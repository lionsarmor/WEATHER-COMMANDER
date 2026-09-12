.PHONY: all run check package clean
PYTHON := $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
all:
	$(PYTHON) tools/build.py
run: all
	./run.sh --no-build
check: all
	$(PYTHON) tools/check.py
	$(PYTHON) tools/test_weather.py
	$(PYTHON) tools/test_cities.py
package:
	./buildweather
clean:
	rm -rf build dist/sdcard
