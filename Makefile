export PATH := /snap/bin:$(PATH)
# TARGETS
build:
	charmcraft build
	rm slurmdbd.charm
	pip3 install -r tmp-requirements.txt --target=build/venv
	./zip_build_dir.py
clean:
	rm -rf build
	rm slurmdbd.charm
