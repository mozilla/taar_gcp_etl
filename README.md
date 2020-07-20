[![CircleCI](https://circleci.com/gh/mozilla/taar_gcp_etl.svg?style=svg)](https://circleci.com/gh/mozilla/taar_gcp_etl)

TAARlite and TAAR ETL jobs for GCP
==================================


This repo contains scripts which are used in ETL jobs for the TAAR and
TAARlite services.


-----

Put all your code into your own repository and package it up as a
container.  This makes it much easier to deploy your code into both
GKEPodOperators which run containerized code within a Kubernetes Pod,
as well as giving you the ability to deploy code into a dataproc
cluster using a git checkout.


## New GCS storage locations

Top level bucket: 

    GCS_BUCKET=moz-fx-data-derived-datasets-parquet


## Jobs

taar_etl.taar_amodump 

    This job extracts the complete AMO listing and emits a JSON blob.
    Depends On:
        https://addons.mozilla.org/api/v3/addons/search/

    Output file: 
        Path: gs://taar_models/addon_recommender/extended_addons_database.json

taar_etl.taar_amowhitelist 

    This job filters the AMO whitelist from taar_amodump into 3 filtered lists.

    Depends On:
        taar_etl.taar_amodump 

    Output file:
        Path: gs://taar_models/addon_recommender/whitelist_addons_database.json
        Path: gs://taar_models/addon_recommender/featured_addons_database.json
        Path: gs://taar_models/addon_recommender/featured_whitelist_addons.json

taar_etl.taar_update_whitelist

    This job extracts the editorial approved addons from AMO

    Depends On:
        https://addons.mozilla.org/api/v3/addons/search/

    Output file:
        Path: gs://taar_models/addon_recommender/only_guids_top_200.json


taar_etl.taar_profile_bigtable


    This task is responsible for extracting data from BigQuery from
    the telemetry table: `clients_last_seen`
    and exports temporary files in Avro format to a bucket in Google
    to Cloud Storage.

    Avro files are then loaded into Cloud BigTable.

    Each record is keyed on a SHA256 hash of the telemetry client-id.

    While this job runs - several intermediate data files are created.
    Any intermediate files are destroyed at the end of the job
    execution.

    The only artifact of this job is records residing in BigTable
    as defined by the `--bigtable-instance-id` and `--bigtable-table-id`
    options to the job.


## PySpark Jobs

taar_similarity
    Output file: 
        Path: gs://taar_models/similarity/donors.json
        Path: gs://taar_models/similarity/lr_curves.json

taar_locale
    Output file: 
        Path: gs://taar_models/locale/top10_dict.json


taar_lite
    Compute addon coinstallation rates for TAARlite
    
    Output file: 
        Path: gs://taar_models/taar/lite/guid_coinstallation.json


## Google Cloud Platform jobs

taar_etl.taar_profile_bigtable
    This job extracts user profile data from `clients_last_seen` to
    build a user profile table in Bigtable. This job is split into 3
    parts:

    1. Filling a BigQuery table with all pertinent data so that we
       can export to Avro on Google Cloud Storage.  The fill is
       completed using a `CREATE OR REPLACE TABLE` operation in
       BigQuery.

    2. Exporting the newly populated BigQuery table into Google Cloud
       Storage in Apache Avro format.

    3. Import of Avro files from Google Cloud Storage into 
       Cloud BigTable.

    When this set of tasks is scheduled in Airflow, it is expected
    that the Google Cloud Storage bucket will be cleared at the start of
    the DAG, and cleared again at the end of DAG to prevent unnecessary
    storage.


## Uploading images to gcr.io

Travis will automatically build a docker image and push the image into
gcr.io for production using the latest tag.

You can use images from the gcr.io image repository using a path like:

```
gcr.io/moz-fx-data-airflow-prod-88e0/taar_gcp_etl:<latest_tag>
```



## Running a job from within a container

Sample command for the impatient:

```
	docker run \
		-v ~/.gcp_creds:/app/creds  \     # directory where you service_account json file resides 
		-v ~/.config:/app/.config \
		-e GOOGLE_APPLICATION_CREDENTIALS=/app/creds/<YOUR_SERVICE_ACCOUNT_JSON_FILE_HERE.json> \
		-e GCLOUD_PROJECT=<YOUR_TEST_GCP_PROJECT_HERE> \
		-it app:build \
		-m taar_etl.taar_profile_bigtable \
		--iso-date=<YESTERDAY_ISODATE_NO_DASHES> \
		--gcp-project=<YOUR_TEST_GCP_PROJECT_HERE> \
		--avro-gcs-bucket=<YOUR_GCS_BUCKET_FOR_AVRO_HERE> \
		--bigquery-dataset-id=<BIG_QUERY_DATASET_ID_HERE> \
		--bigquery-table-id=<BIG_QUERY_TABLE_ID_HERE> \
		--bigtable-instance-id=<BIG_TABLE_INSTANCE_ID> \
		--wipe-bigquery-tmp-table
```

The container defines an entry point which pre-configures the conda
enviromet and starts up the python interpreter.  You need to pass in
arguments to run your module as a task.

Note that to test on your local machine - you need to volume mount two
locations to get your credentials to load, and you will need to mount
your google authentication tokens by mounting `.config` and you will
also need to volume mount your GCP service account JSON file.  You
will also need to specify your GCP_PROJECT.
