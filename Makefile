.PHONY: all setup data map clean

all: setup data map

setup:
	python3 -m pip install -r requirements.txt

data:
	bash bootstrap.sh

map:
	python3 scripts/render_map.py

clean:
	rm -f outputs/*.png outputs/*.pdf
