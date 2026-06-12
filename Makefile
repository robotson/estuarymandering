.PHONY: all setup data map map-all clean

# renders use the project venv when it exists, system python otherwise
# (deferred = so this re-evaluates at recipe time, AFTER `make setup` runs)
PY = $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)

all: setup data map map-all

setup:
	@if command -v uv >/dev/null 2>&1; then \
		uv venv && uv pip install -r requirements.txt; \
	else \
		python3 -m venv .venv && .venv/bin/pip install -r requirements.txt; \
	fi

data:
	bash bootstrap.sh

map:
	$(PY) scripts/render_map.py

map-all:
	$(PY) scripts/render_map_all_territories.py

clean:
	rm -f outputs/*.png outputs/*.pdf
