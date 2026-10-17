PYTHON ?= python
TEST ?=

.PHONY: context test lint format format-check check build

context:
	@git status --short --branch
	@printf 'latest-tag: '; git tag --sort=-version:refname | sed -n '1p'
	@sed -n '/^- Version:/p; /^- Theme:/p; /^- Next gate:/p' docs/CURRENT.md

test:
	PYTHONPATH=src $(PYTHON) -m unittest $(if $(TEST),$(TEST),discover -s tests) -q

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

format-check:
	$(PYTHON) -m ruff format --check .

check: lint format-check test
	git diff --check

build:
	$(PYTHON) -m build
