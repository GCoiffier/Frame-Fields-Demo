SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

VENV := $(shell echo $${VIRTUAL_ENV-.venv})
PY3 := $(shell command -v python3 2>/dev/null)
PYTHON := $(VENV)/bin/python
INSTALL_STAMP := $(VENV)/.install.stamp

.PHONY: run clean

$(PYTHON):
	@if [ -z $(PY3) ]; then echo "Python 3 could not be found."; exit 2; fi
	echo $(PY3) -m venv $(VENV)
	$(PY3) -m venv $(VENV)

$(INSTALL_STAMP): $(PYTHON) requirements.txt
	$(PYTHON) -m pip install -r requirements.txt
	touch $(INSTALL_STAMP)
run: $(INSTALL_STAMP)
	$(PYTHON) run.py data/fandisk.off
clean:
	@rm -rf $(BUILDDIR)
	rm -rf $(VENV) .pytest_cache .coverage
	find . -type f -name *.pyc -delete
	find . -type d -name __pycache__ -delete

