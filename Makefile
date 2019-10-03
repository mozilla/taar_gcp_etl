.PHONY: build up tests flake8 ci tests-with-cov

all:
	docker build -t app:build .

shell:
	docker run --rm -it mozilla/taar_amodump:latest /bin/bash

run_taar_amodump:
	docker run -t --rm -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} -e PROC_DATE=${PROC_DATE} app:build -m taar_etl.taar_amodump --date 20190801

run_taar_amowhitelist:
	docker run -t --rm -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} app:build -m taar_etl.taar_amowhitelist

run_taar_update_whitelist:
	docker run -t --rm -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} app:build -m taar_etl.taar_update_whitelist --date 20190801
