.PHONY: all run check package clean
PYTHON := $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
all:
	$(PYTHON) tools/build.py
run: all
	./run.sh --no-build
check: all
	$(PYTHON) tools/check.py
	$(PYTHON) tools/check_native.py
package:
	./buildweather
clean:
	rm -rf build dist/sdcard
