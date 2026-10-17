.DEFAULT_GOAL := help
.PHONY: help install build release verify verify-release test lint
PYTHON ?= .venv/bin/python

help:
	@echo 'make install  Create a virtual environment and install test tools'
	@echo 'make build    Build the code patch without game data (Python + clang)'
	@echo 'make release  Rebuild the versioned public release and checksums'
	@echo 'make verify   Verify and patch your decompressed executable'
	@echo 'make test     Run tests; native tests skip when private inputs are absent'
	@echo 'make lint     Check source, tests and release tools'

install:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements-dev.txt

GAME_VERSION ?= 1.3.1
ARCHIVE ?= inputs/pc.sarc
BASE_ARCHIVE ?= inputs/base-pc.sarc
SCHEDULE ?= inputs/Schedule.xml
OUT ?= build/nba-game-only-all-catchers-luma.zip

build:
	$(PYTHON) src/badge_patch.py --game-version "$(GAME_VERSION)" --package build/nba-code-only.zip

release:
	$(PYTHON) tools/release.py

verify:
	$(PYTHON) src/badge_patch.py --code "$(BADGE_CODE)" --output build/verified

.PHONY: complete
complete:
	$(PYTHON) tools/build_complete.py --archive "$(ARCHIVE)" --base-archive "$(BASE_ARCHIVE)" --schedule "$(SCHEDULE)" --output "$(OUT)"

verify-release:
	$(PYTHON) tools/verify_release.py

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check src tests tools
