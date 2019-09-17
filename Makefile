.PHONY: help prepare-dev test lint run doc
SHELL = /bin/bash
.DEFAULT_GOAL := test

VENV_NAME?=venv
VENV_ACTIVATE=. $(VENV_NAME)/bin/activate
PYTHON=${VENV_NAME}/bin/python3

.DEFAULT: help
help:
	@echo "make prepare-dev"
	@echo "       prepare development environment, use only once"
	@echo "make test"
	@echo "       run tests"
	@echo "make coverage"
	@echo "       creates a html coverage report"
	@echo "make docker-build"
	@echo "       builds a docker image"

.PHONY: prepare-dev
prepare-dev:
	python3 -m pip install virtualenv

.PHONY: init
init:
	deactivate || echo "no virtualenv"
	virtualenv venv
	source ./venv/bin/activate
	${PYTHON} setup.py test

.PHONY: test
test: init
	venv/bin/python3 setup.py validate

.PHONY: coverage
coverage: init
	$(VENV_NAME)/bin/coverage html -i flyte/**/** && open htmlcov/index.html

.PHONY: run-example
run-example: init
	FLYTE_API=http://localhost:8080 python3 -m example.app env/

.PHONY: docker-build
docker-build: init
	docker build -t python-flyte-example .

.PHONY: docker-run
docker-run: docker-build
	 docker run -d --name flyte-python-example --rm -e FLYTE_API=http://flyte:8080 --link flyte:flyte python-flyte-example