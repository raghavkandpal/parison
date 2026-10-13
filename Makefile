PYTHON ?= python
TEST ?=

.PHONY: context test check build

context:
	@git status --short --branch
	@printf 'latest-tag: '; git tag --sort=-version:refname | sed -n '1p'
	@sed -n '/^- Version:/p; /^- Theme:/p; /^- Next gate:/p' docs/CURRENT.md

test:
	PYTHONPATH=src $(PYTHON) -m unittest $(if $(TEST),$(TEST),discover -s tests) -q

check: test
	git diff --check

build:
	$(PYTHON) -m build
