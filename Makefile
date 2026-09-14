PY ?= python3
export PYTHONPATH := src

.PHONY: help test lint collect report all clean

help:
	@grep -E '^[a-z-]+:.*?##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/'

test:  ## run the unit tests
	$(PY) -m pytest -q

lint:  ## ruff, if installed
	@command -v ruff >/dev/null && ruff check src tests || echo "ruff not installed - skipping"

collect:  ## re-measure every reference day (network, ~30 min; run in parallel with -j if you like)
	@for d in 2023-09-06 2023-09-13 2023-09-20 2024-09-04 2024-09-11 2024-09-18 \
	          2025-09-03 2025-09-10 2025-09-17 2026-09-09; do \
		$(PY) -m pr_fanout collect --date $$d --every 2 --top 30 --out data/day-$$d.json; \
	done

report:  ## rebuild docs/ from data/
	$(PY) -m pr_fanout report --inputs 'data/day-*.json' --out docs

all: collect report test  ## full reproduction from scratch

clean:
	rm -rf docs/*.svg docs/summary*.md docs/summary*.json
