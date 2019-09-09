.PHONY: build up tests flake8 ci tests-with-cov

all:
	docker build -t mozilla/taar_amodump .

shell:
	docker run --rm -it mozilla/taar_amodump:latest /bin/bash

run:
	docker run -t -e MOZETL_COMMAND="taar_amodump --date=20190802" mozilla/taar_amodump:latest 
