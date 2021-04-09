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


test_delete:
	docker run \
		-v ~/.gcp_creds:/app/creds \
		-e GOOGLE_APPLICATION_CREDENTIALS=/app/creds/$(GCP_CREDS_NAME) \
		-e GCLOUD_PROJECT=cfr-personalization-experiment \
		-it app:build \
		-m taar_etl.taar_profile_bigtable \
		--iso-date=20210406 \
		--gcp-project=cfr-personalization-experiment \
		--bigtable-table-id=test_table \
		--bigtable-instance-id=taar-profile \
		--delete-opt-out-days 28 \
		--avro-gcs-bucket taar_profile_dump \
		--sample-rate=1.0 \
		--bigtable-delete-opt-out