# Network segmentation and egress policy

Financial Manager networking is default-deny at two layers: Docker network membership controls
service reachability, and `financial_manager.network_policy.NetworkPolicy` controls every
external HTTPS destination by exact hostname. Both layers are source controlled.

## Enforced topology

- `research-agent` has only the internal `fm_agent` network and no external route.
- `market-data-gateway` and `news-gateway` bridge `fm_agent` to the separate
  `fm_market_egress` network. They do not join the broker networks.
- `approval-service` is the only service joining the agent network to the internal
  `fm_broker_control` network. It is not an egress proxy.
- `broker-gateway` joins `fm_broker_control` and the isolated `fm_broker_egress` network.
- No AI/LLM or research-agent container shares `fm_broker_egress` or a network with an external
  broker endpoint.
- `alert-router` is isolated from the agent and broker services and may reach only the regional
  Amazon SNS endpoint `sns.us-west-2.amazonaws.com` over HTTPS.

The platform-profile service entries use the hardened baseline image only to validate topology;
later service epics replace their entrypoints without changing network boundaries.

## Egress and DNS

`config/network-policy.json` is the authoritative application-layer allowlist. It initially
contains no external hosts, so M1 is safe before market-data, news, and brokerage providers are
selected. Provider onboarding must add exact DNS names by reviewed PR and add connection tests.
Wildcards, HTTP, embedded credentials, non-443 ports, and IP literals fail closed. Resolved DNS
and proxy connection outcomes must be emitted through the structured audit/telemetry path.

Market/news destinations may be added only to their respective gateway. Broker destinations may
be added only to `broker-gateway`. Agents never receive external egress entries. Policy changes
must identify the provider, owner, purpose, environment, and verification evidence in the PR.
The alert-router SNS entry supports operational notification only and cannot be reused for market,
news, brokerage, or agent traffic.

## Verification

`tests/test_network_policy.py` proves prohibited service paths, direct agent egress, broker-path
isolation, invalid destination rejection, policy audit records, and Compose network membership.
