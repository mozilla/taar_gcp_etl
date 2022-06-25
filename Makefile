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


test_amodump:
	docker run \
		-v ~/.config:/app/.config \
		-v ~/.gcp_creds:/app/creds \
		-e GOOGLE_APPLICATION_CREDENTIALS=/app/creds/cfr-personalization-experiment-a068661e8a05.json \
		-e GCLOUD_PROJECT=cfr-personalization-experiment   \
		-it app:build \
		-m taar_etl.taar_amodump \
		--date=20220620

test_amowhitelist:
	docker run \
		-v ~/.config:/app/.config \
		-v ~/.gcp_creds:/app/creds \
		-e GOOGLE_APPLICATION_CREDENTIALS=/app/creds/cfr-personalization-experiment-a068661e8a05.json \
		-e GCLOUD_PROJECT=cfr-personalization-experiment   \
		-it app:build \
		-m taar_etl.taar_amowhitelist

test_update_whitelist:
	docker run \
		-v ~/.config:/app/.config \
		-v ~/.gcp_creds:/app/creds \
		-e GOOGLE_APPLICATION_CREDENTIALS=/app/creds/cfr-personalization-experiment-a068661e8a05.json \
		-e GCLOUD_PROJECT=cfr-personalization-experiment   \
		-it app:build \
		-m taar_etl.taar_update_whitelist \
		--date=20220620

test_delete:
	docker run \
		-v ~/.config:/app/.config \
		-e GCLOUD_PROJECT=moz-fx-data-taar-nonprod-48b6  \
		-it app:build \
		-m taar_etl.taar_profile_bigtable \
		--iso-date=20210426 \
		--gcp-project=moz-fx-data-taar-nonprod-48b6 \
		--bigtable-table-id=taar_profile \
		--bigtable-instance-id=taar-stage-202006 \
		--delete-opt-out-days 28 \
		--avro-gcs-bucket moz-fx-data-taar-nonprod-48b6-stage-etl \
		--subnetwork regions/us-west1/subnetworks/gke-taar-nonprod-v1 \
		--dataflow-workers=2 \
		--dataflow-service-account taar-stage-dataflow@moz-fx-data-taar-nonprod-48b6.iam.gserviceaccount.com \
		--sample-rate=1.0 \
		--bigtable-delete-opt-out