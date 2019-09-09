.PHONY: build up tests flake8 ci tests-with-cov

all:
	docker build -t mozilla/taar_amodump .

shell:
	docker run --rm -it mozilla/taar_amodump:latest /bin/bash

run:
	docker run -t --rm -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} -e AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION} -e PROC_DATE=${PROC_DATE} mozilla/taar_amodump:latest 
