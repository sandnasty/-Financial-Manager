PYTHON ?= python3

.DEFAULT_GOAL := help

.PHONY: help check-toolchain build test lint format format-check validate doctor container-test clean

help: ## Show the supported command interface
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

check-toolchain: ## Fail unless the pinned runtime is active
	@$(PYTHON) tools/check_toolchain.py

build: check-toolchain ## Create the deterministic representative-service artifact
	@$(PYTHON) tools/build.py

test: check-toolchain ## Run all unit and build-contract tests
	@$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

lint: check-toolchain ## Run source and repository policy checks
	@$(PYTHON) tools/lint.py

format: check-toolchain ## Normalize source-controlled text files in place
	@$(PYTHON) tools/format.py

format-check: check-toolchain ## Check formatting without changing files
	@$(PYTHON) tools/format.py --check

validate: check-toolchain lint format-check test build ## Run the authoritative local/CI validation path
	@echo "PASS: build, tests, lint, formatting, lock, and reproducibility checks succeeded"

doctor: ## Diagnose the supported Windows + WSL2/Docker development environment
	@sh tools/doctor.sh

container-test: ## Run the hardened-container integration test (requires Docker Desktop)
	@sh tests/security/test_container_baseline.sh

clean: ## Remove generated outputs
	@$(PYTHON) -c "import shutil; shutil.rmtree('dist', ignore_errors=True)"
