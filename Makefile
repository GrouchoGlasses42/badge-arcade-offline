.DEFAULT_GOAL := help
.PHONY: help install build release verify verify-release test lint
PYTHON ?= .venv/bin/python

help:
	@echo 'make install  Create a virtual environment and install test tools'
	@echo 'make build    Build the code patch without game data (Python + clang)'
	@echo 'make vanilla  Build the Vanilla IPS only (alias: build)'
	@echo 'make expanded Build Expanded from BASE_ARCHIVE, ARCHIVE, SCHEDULE, ALLBADGE, optional BOOT9'
	@echo 'make custom-weekly Build Custom Weekly from the Expanded inputs and WEEK'
	@echo 'make release  Rebuild the versioned public release and checksums'
	@echo 'make verify   Verify and patch your decompressed executable'
	@echo 'make test     Run tests. Private input tests skip if files are absent'
	@echo 'make lint     Check source, tests and release tools'
	@echo 'make check-assets Audit the checkout for private game material'

install:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements-dev.txt

GAME_VERSION ?= 1.3.1
HOME_MENU ?= 0
HOME_FLAG = $(if $(filter 1,$(HOME_MENU)),--home-menu,)
ARCHIVE ?= ../nba-private/inputs/pc.sarc
BASE_ARCHIVE ?= ../nba-private/inputs/base-pc.sarc
SCHEDULE ?= ../nba-private/inputs/Schedule.xml
OUT ?= ../nba-private/nba-$(if $(filter 1,$(HOME_MENU)),home-menu,game-only)-all-catchers-luma.zip
WEEK ?= ../nba-private/inputs/week.enc
ALLBADGE ?= ../nba-private/inputs/allbadge_v131.dat.boss
BOOT9 ?=
WEEK_OUT ?= ../nba-private/nba-custom-weekly-luma.zip

build:
	$(PYTHON) src/badge_patch.py --game-version "$(GAME_VERSION)" $(HOME_FLAG) --package build/nba-code-only.zip

release:
	$(PYTHON) tools/release.py

verify:
	$(PYTHON) src/badge_patch.py --code "$(BADGE_CODE)" --output ../nba-private/verified

.PHONY: complete vanilla expanded custom-weekly
vanilla: build
expanded: complete
complete:
	$(PYTHON) tools/build_complete.py --archive "$(ARCHIVE)" --base-archive "$(BASE_ARCHIVE)" --schedule "$(SCHEDULE)" --allbadge "$(ALLBADGE)" $(if $(BOOT9),--boot9 "$(BOOT9)",) --output "$(OUT)" $(HOME_FLAG)

custom-weekly:
	$(PYTHON) tools/build_spotpass.py --update-archive "$(ARCHIVE)" --base-archive "$(BASE_ARCHIVE)" --schedule "$(SCHEDULE)" --week "$(WEEK)" --allbadge "$(ALLBADGE)" $(if $(BOOT9),--boot9 "$(BOOT9)",) --output "$(WEEK_OUT)" $(HOME_FLAG)

verify-release:
	$(PYTHON) tools/verify_release.py

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check src tests tools

.PHONY: check-assets
check-assets:
	$(PYTHON) tools/check_assets.py
