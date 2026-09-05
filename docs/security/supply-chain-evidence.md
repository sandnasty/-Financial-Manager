# Supply-chain evidence: SBOM, signatures, and provenance

## Release evidence model

Every releasable Financial Manager container is identified by its immutable GHCR digest. The publication workflow creates three independent evidence classes for that exact digest:

1. **CycloneDX SBOM** generated from the published digest.
2. **Keyless Cosign signature** bound to the digest.
3. **Signed attestations** for the CycloneDX SBOM and SLSA-style build provenance.

The evidence is also retained as GitHub Actions artifacts with the corresponding publication run so an operator can retrieve the SBOM/provenance for a selected deployed version.

## Signing identity and key protection

Financial Manager uses Sigstore/Cosign keyless signing from the controlled `Immutable Container Artifact` GitHub Actions workflow.

- The publication job alone receives `id-token: write` so it can obtain a short-lived GitHub OIDC token.
- No long-lived signing private key is created, stored in the repository, placed on a developer workstation, or stored as a GitHub secret.
- Verification requires the certificate identity for `.github/workflows/artifact-publish.yml@refs/heads/main` and the GitHub Actions issuer `https://token.actions.githubusercontent.com`.
- Cosign is installed through the integrity-checking `sigstore/cosign-installer` action and is explicitly pinned to patched Cosign v3.1.3.

This design follows the existing MS-76 rule to prefer short-lived/federated credentials instead of static signing material.

## SBOM

Trivy generates `supply-chain-evidence/sbom.cdx.json` in CycloneDX JSON format by scanning the exact digest-qualified GHCR image after publication. The file is retained with `artifact-metadata.json` and is also signed as a Cosign `cyclonedx` attestation attached to the image digest.

## Build provenance

`tools/supply_chain_evidence.py` creates `supply-chain-evidence/provenance.json`. It records:

- repository;
- full Git commit SHA;
- project version;
- publication workflow and workflow ref;
- GitHub Actions run ID and attempt;
- builder/run URL;
- runner OS and architecture;
- exact OCI image name and SHA-256 digest.

The generator validates that the provenance source and artifact digest match the release metadata before the predicate is attested. The provenance is signed as a Cosign `slsaprovenance` attestation bound to the same image digest.

## Promotion verification

Before vulnerability scanning or DEV deployment, `Controlled Artifact Promotion`:

1. downloads the publication metadata, SBOM, and provenance associated with the selected publication run;
2. verifies that local provenance source SHA/repository/digest matches the immutable publication metadata;
3. verifies the digest exists in GHCR;
4. verifies the Cosign image signature against the expected main-branch publication workflow identity;
5. verifies the signed CycloneDX attestation;
6. verifies the signed SLSA-style provenance attestation;
7. only then executes the MS-64 exact-digest vulnerability gate.

A missing signature, missing attestation, unexpected signer identity, or provenance/digest mismatch stops the `resolve-artifact` job. DEV, TEST, and PROD cannot run because they depend on that job.

## Negative verification

Publication includes a controlled negative demonstration using a replaced all-zero digest. The job requires Cosign verification of that replaced reference to fail. A unit test also proves the provenance validator rejects a digest that differs from the recorded release digest.

## Evidence retrieval

For a deployed version:

1. Read the DEV/TEST/PROD deployment record to obtain the `source_run_id` and immutable digest.
2. Open the corresponding `Immutable Container Artifact` run.
3. Download `immutable-container-metadata-<run-id>-<attempt>`.
4. The artifact contains:
   - `artifact-metadata.json`
   - `supply-chain-evidence/sbom.cdx.json`
   - `supply-chain-evidence/provenance.json`
   - signature/attestation verification output generated during publication.
5. The OCI signature and attestations can also be verified directly against the digest with Cosign using the expected workflow identity and GitHub OIDC issuer.

Evidence is retained for 90 days in the current baseline. Long-term retention remains subject to the operational retention policy work in E03-08.
