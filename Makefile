SHELL := /bin/bash
.DEFAULT_GOAL := help

VENV := .venv
PYTHON_MIN := 3.13
ACTIVATE := source $(VENV)/bin/activate

# Detect Python provider: uv > pyenv > system
PYTHON_BIN := $(shell \
	if command -v uv >/dev/null 2>&1; then \
		echo uv; \
	elif command -v pyenv >/dev/null 2>&1 && pyenv versions --bare 2>/dev/null | grep -q '^3\.'; then \
		echo pyenv; \
	elif command -v python3 >/dev/null 2>&1; then \
		echo system; \
	else \
		echo none; \
	fi)

# Use uv pip when available (uv venvs don't include pip by default)
ifeq ($(PYTHON_BIN),uv)
  PIP_INSTALL := uv pip install --python $(VENV)/bin/python3
else
  PIP_INSTALL := $(ACTIVATE) && pip install
endif

.PHONY: help setup hooks lint check deploy clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: $(VENV)/bin/ansible ## Create venv and install Ansible + Galaxy collections

$(VENV)/bin/ansible: $(VENV)/bin/activate requirements.yml
	$(PIP_INSTALL) ansible ansible-lint yamllint pre-commit
	$(ACTIVATE) && ansible-galaxy collection install -r requirements.yml
	@touch $@

$(VENV)/bin/activate:
ifeq ($(PYTHON_BIN),uv)
	@echo "==> Using uv to create venv"
	uv venv $(VENV) --python $(PYTHON_MIN)
else ifeq ($(PYTHON_BIN),pyenv)
	@echo "==> Using pyenv Python to create venv"
	$(eval PYENV_PY := $(shell pyenv versions --bare | grep '^3\.' | sort -V | tail -1))
	$(HOME)/.pyenv/versions/$(PYENV_PY)/bin/python -m venv $(VENV)
else ifeq ($(PYTHON_BIN),system)
	@echo "==> Using system python3 to create venv"
	@python3 -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)" || \
		{ echo "Error: Python >= $(PYTHON_MIN) required"; exit 1; }
	python3 -m venv $(VENV)
else
	$(error No suitable Python found. Install uv, pyenv, or python3 >= $(PYTHON_MIN))
endif

hooks: $(VENV)/bin/ansible ## Install pre-commit hooks into .git/hooks
	$(ACTIVATE) && pre-commit install

lint: $(VENV)/bin/ansible ## Run ansible-lint and yamllint
	$(ACTIVATE) && yamllint -c .yamllint.yml .
	$(ACTIVATE) && ansible-lint playbooks/ roles/

check: $(VENV)/bin/ansible ## Dry-run site.yml (check mode)
	$(ACTIVATE) && ansible-playbook playbooks/site.yml --check --diff

deploy: $(VENV)/bin/ansible ## Full deploy via site.yml
	$(ACTIVATE) && ansible-playbook playbooks/site.yml

clean: ## Remove virtual environment
	rm -rf $(VENV)
