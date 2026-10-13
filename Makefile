PYTHON ?= python
TEST ?=

.PHONY: context test check build

context:
	@git status --short --branch
	@printf 'latest-tag: '; git describe --tags --abbrev=0 2>/dev/null || printf 'none\n'
	@sed -n '/^- Version:/p; /^- Theme:/p; /^- Next gate:/p' docs/CURRENT.md

test:
	PYTHONPATH=src $(PYTHON) -m unittest $(if $(TEST),$(TEST),discover -s tests) -q

check: test
	git diff --check

build:
	$(PYTHON) -m build
