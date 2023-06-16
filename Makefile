help: ## Show this help
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-21s\033[0m %s\n", $$1, $$2}'


# Host development scripts (docker-compose)

build: ## Build the development environment with docker-compose
	docker-compose build

develop: ## Start the development server with docker
	docker-compose run --service-ports -- dev

develop_remote: ## Start the development server with docker
	docker-compose run --service-ports -- dev_remote

shell: ## Get a shell inside a new development container
	docker-compose run --service-ports -- dev bash

down: ## Delete docker-compose containers and volumes
	docker-compose down --remove-orphans --volumes

dc-lint: ## Using docker-compose, ensures the code is properlly formatted
	docker-compose run --service-ports -- dev make lint


# App

start-dev: ## Start a development server	
	uvicorn app.main:app \
		--host 0.0.0.0 \
		--port 8080 \
		--lifespan=on \
		--use-colors \
		--loop uvloop \
		--http httptools \
		--reload

generate-sample:  ## Generate voice samples
	docker-compose run --rm dev python3 app/scripts/generate_sample.py $(ARGS)


# Codestyle scripts

lint: ## Ensures the code is properlly formatted
	pycodestyle app
	isort --settings-path=./setup.cfg --check-only app

format:  ## format the code accordig to the configuration
	autopep8 -ir app
	isort --settings-path=./setup.cfg app


# Pipenv scripts - dependency management

lock: ## Refresh pipfile.lock
	pipenv lock

requirements: ## Refresh requirements.txt from pipfile.lock
	pipenv requirements > requirements.txt

requirements_dev: ## Refresh requirements-dev.txt from pipfile.lock
	pipenv requirements --dev > requirements-dev.txt

check: ## Scan dependencies for security vulnerabilities
	pipenv check

update: ## Update dependencies in pipfile and refresh pipfile.lock
	pipenv update

update_dev: ## Update all dependencies in pipfile and refresh pipfile.lock
	pipenv update --dev


# Testing scripts

test: ## Run project tests locally
	docker-compose run --rm dev pytest -vv

test_dev-remote:  ## Run project tests, saving to S3 bucket, and using remote db
	docker-compose run --rm dev_remote pytest -vv
