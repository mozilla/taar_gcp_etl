.PHONY: build up tests flake8 ci tests-with-cov

all:
	# PySpark only knows eggs, not wheels
	docker-compose build 

shell:
	docker-compose run taar_amodump bash 
