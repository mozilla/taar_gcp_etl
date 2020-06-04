.PHONY: build up tests flake8 ci tests-with-cov

TAG_BASE=gcr.io/cfr-personalization-experiment/taar_gcp_etl
TAG_REV=$(shell git tag|tail -n 1)

all:
	docker build -t app:build .

shell:
	docker run --rm -it mozilla/taar_amodump:latest /bin/bash

### The following run_* commands are only used to test that this container executes ETL jobs
### correctly on the local development machine. They are not intended for production.
run_taar_amodump:
	docker run -t --rm -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} -e PROC_DATE=${PROC_DATE} app:build -m taar_etl.taar_amodump --date 20190801

run_taar_amowhitelist:
	docker run -t --rm -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} app:build -m taar_etl.taar_amowhitelist

run_taar_update_whitelist:
	docker run -t --rm -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} app:build -m taar_etl.taar_update_whitelist --date 20190801

bq_to_tmp:
	python -m taar_etl.taar_profile_bigtable --iso-date=20200601 --gcs-to-bigtable --gcp-project=cfr-personalization-experiment --iso-date=20200617 --avro-gcs-bucket=taar_profile_dump --bigtable-instance-id=taar-profile --bigquery-dataset-id=cfr_etl --fill-bq

push_gcr_io:
	docker tag app:build ${TAG_BASE}:${TAG_REV}
	docker push ${TAG_BASE}:${TAG_REV}
