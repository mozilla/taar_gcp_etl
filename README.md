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

S3 locations
============

Top level bucket: 

    S3_PARQUET_BUCKET=telemetry-parquet

New GCS storage locations:
==========================

Top level bucket: 

    GCS_BUCKET=moz-fx-data-derived-datasets-parquet


Jobs
====

taar_etl.taar_amodump 

    This job extracts the complete AMO listing and emits a JSON blob.
    Depends On:
        https://addons.mozilla.org/api/v3/addons/search/

    Output file: 
        Path: s3://telemetry-parquet/telemetry-ml/addon_recommender/extended_addons_database.json

taar_etl.taar_amowhitelist 

    This job filters the AMO whitelist from taar_amodump into 3 filtered lists.

    Depends On:
        taar_etl.taar_amodump 

    Output file:
        Path: s3://telemetry-parquet/telemetry-ml/addon_recommender/whitelist_addons_database.json
        Path: s3://telemetry-parquet/telemetry-ml/addon_recommender/featured_addons_database.json
        Path: s3://telemetry-parquet/telemetry-ml/addon_recommender/featured_whitelist_addons.json

taar_etl.taar_update_whitelist

    This job extracts the editorial approved addons from AMO

    Depends On:
        https://addons.mozilla.org/api/v3/addons/search/

    Output file:
        Path: s3://telemetry-parquet/telemetry-ml/addon_recommender/only_guids_top_200.json


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


Task Sensors
------------

wait_for_main_summary_export
wait_for_clients_daily_export

PySpark Jobs
------------

taar_similarity
    Depends On:
        gcs: gs://moz-fx-data-derived-datasets-parquet/main_summary/v4

    Output file: 
        S3_PARQUET_BUCKET=telemetry-parquet
        Path: taar/similarity/donors.json
        Path: taar/similarity/lr_curves.json

taar_locale
    Depends On:
        gcs: gs://moz-fx-data-derived-datasets-parquet/clients_daily/v6
        Path: s3://telemetry-parquet/telemetry-ml/addon_recommender/only_guids_top_200.json

    Output file: 
        S3_BUCKET: telemetry-private-analysis-2
        Path: taar/locale/top10_dict.json


taar_lite
    Compute addon coinstallation rates for TAARlite
    
    Depends On:
            s3a://telemetry-parquet/clients_daily/v6/submission_date_s3={dateformat}

    Output file: 
        S3_BUCKET: telemetry-parquet
        Path: taar/lite/guid_coinstallation.json


Google Cloud Platform jobs
--------------------------

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
