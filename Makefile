PYTHON ?= python3
HOST ?= codex
TARGET ?= .

.PHONY: check test governance verify install-dry-run install

check:
	$(PYTHON) docs/tools/conformance.py --all

test: check

governance:
	PYTHONDONTWRITEBYTECODE=1 ./project/governance-check.sh --actor agent

verify: check governance
	git diff --check

install-dry-run: check
	$(PYTHON) docs/tools/install.py --host "$(HOST)" --target "$(TARGET)"

install: check
	@test "$(CONFIRM_APPLY)" = "1" || { \
		echo "Refusing writes; rerun with CONFIRM_APPLY=1 after reviewing install-dry-run" >&2; \
		exit 2; \
	}
	$(PYTHON) docs/tools/install.py --host "$(HOST)" --target "$(TARGET)" --apply
