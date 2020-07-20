.PHONY: build up tests flake8 ci tests-with-cov

TAG_BASE=gcr.io/${GCP_PROJECT_ID}/taar_gcp_etl
TAG_REV=$(shell git tag|tail -n 1)

all: build

build:
	docker build -t app:build .

setup_conda:
	# Install all dependencies and setup repo in dev mode
	conda env create -f environment.yml
	python setup.py develop

shell:
	docker run --rm -it mozilla/taar_amodump:latest /bin/bash

tag_gcr_io:
	docker tag app:build ${TAG_BASE}:${TAG_REV}

push_gcr_io:
	docker push ${TAG_BASE}:${TAG_REV}
