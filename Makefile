PYTHON ?= python

.PHONY: test check build

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -q

check: test
	git diff --check

build:
	$(PYTHON) -m build
