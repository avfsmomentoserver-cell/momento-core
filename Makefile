# Momento local development. Debian 12, apt + venv + SQLite only.
#
# No Docker, no cloud account, no paid service. Run `make help` for targets.
#
# `make verify` runs exactly what CI runs, so a green local run means a green
# pipeline. Heavier targets (research, audit) stay local to protect the free
# tier's 400 minutes/month.

SHELL := /bin/bash
.DEFAULT_GOAL := help

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
RUFF := $(VENV)/bin/ruff
PYTEST := $(VENV)/bin/pytest

# Override any of these: make research CSV=other.csv PERMUTATIONS=500
CSV ?= clean_data.csv
PERMUTATIONS ?= 200
COV_MIN ?= 40

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s \033[0m %s\n", $$1, $$2}'

.PHONY: apt
apt: ## Print the required Debian packages (does not install)
	@echo "sudo apt install -y python3 python3-venv python3-pip git make"

$(VENV)/bin/activate: requirements-dev.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	@touch $(VENV)/bin/activate

.PHONY: venv
venv: $(VENV)/bin/activate ## Create the venv and install dev deps

.PHONY: audit-deps
audit-deps: venv ## Install numpy/pandas/scipy for the audit tool
	$(PIP) install -r requirements-audit.txt

.PHONY: lint
lint: venv ## Lint and format-check (same as CI)
	$(RUFF) check backend
	$(RUFF) format --check backend

.PHONY: fmt
fmt: venv ## Apply formatting and safe fixes
	$(RUFF) format backend
	$(RUFF) check --fix backend

.PHONY: test
test: venv ## Run the assertable test suite (same as CI)
	$(PYTEST)

.PHONY: cov
cov: venv ## Run tests with a coverage gate
	$(PYTEST) --cov --cov-report=term-missing --cov-fail-under=$(COV_MIN)

.PHONY: research
research: venv ## Run the research suite against $(CSV)
	@test -f "$(CSV)" || { echo "missing $(CSV) - set CSV=<path>"; exit 1; }
	cd backend && ../$(PY) -m research.runner "../$(CSV)" \
		--permutations $(PERMUTATIONS) \
		--json ../research-report.json

.PHONY: audit
audit: audit-deps ## Run the eagle-eye data audit against $(CSV)
	@test -f "$(CSV)" || { echo "missing $(CSV) - set CSV=<path>"; exit 1; }
	@test -f tools/eagle_eye_audit.py || { echo "tools/eagle_eye_audit.py not committed yet"; exit 1; }
	$(PY) tools/eagle_eye_audit.py "$(CSV)" --json audit-report.json

.PHONY: verify
verify: lint test ## Everything CI checks, in one command

.PHONY: clean
clean: ## Remove venv, caches and generated reports
	rm -rf $(VENV) .pytest_cache .ruff_cache .coverage coverage.xml
	rm -f research-report.json audit-report.json
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
