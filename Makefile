.PHONY: clean clean-build clean-pyc lint test coverage dist install develop publish venv

help:
	@echo "venv - create a virtual environment with uv"
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "lint - check style with flake8"
	@echo "test - run tests quickly with the default Python"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "dist - package"
	@echo "install - install the package to the active Python's site-packages"
	@echo "develop - install the package in development mode"
	@echo "publish - publish the package to PyPI"

venv:
	uv venv
	@echo "Virtual environment created. Activate it with:"
	@echo "source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate"

clean: clean-build clean-pyc

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc:
	find . -name '*.pyc' -delete
	find . -name '*.pyo' -delete
	find . -name '*~' -delete
	find . -name '__pycache__' -delete

lint:
	uv run flake8 tests

test:
	uv run pytest

coverage:
	uv run pytest --cov tests/

dist: clean
	uv run python -m build
	uv run twine check dist/*

install: clean
	uv install .

develop: clean
	uv install -e ".[dev]"

publish: clean dist
	uv run twine upload dist/*
