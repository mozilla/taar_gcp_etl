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
        S3_PARQUET_BUCKET
        Path: telemetry-ml/addon_recommender/extended_addons_database.json

taar_etl.taar_amowhitelist 

    This job filters the AMO whitelist from taar_amodump into 3 filtered lists.

    Depends On:
        taar_etl.taar_amodump 

    Output file:
        S3_PARQUET_BUCKET

        Path: telemetry-ml/addon_recommender/whitelist_addons_database.json
        Path: telemetry-ml/addon_recommender/featured_addons_database.json
        Path: telemetry-ml/addon_recommender/featured_whitelist_addons.json

taar_etl.taar_update_whitelist

    This job extracts the editorial approved addons from AMO
    Depends On:
        https://addons.mozilla.org/api/v3/addons/search/

    Output file:
        S3_PARQUET_BUCKET

        Path: telemetry-ml/addon_recommender/only_guids_top_200.json


Task Sensors
------------

wait_for_main_summary_export
wait_for_clients_daily_export

PySpark Jobs
------------

taar_dynamo_job
    Depends On:
        gcs: gs://moz-fx-data-derived-datasets-parquet/main_summary/v4
        TODO: we need to upgrade to v6 as the similarity job has been
              updated

    Output file: 
        AWS DynamoDB: us-west-2/taar_addon_data_20180206

taar_similarity
    Depends On:
        gcs: gs://moz-fx-data-derived-datasets-parquet/main_summary/v4

    Output file: 
        S3_PARQUET_BUCKET
        Path: taar/similarity/donors.json
        Path: taar/similarity/lr_curves.json

taar_locale
    Depends On:
        gcs: gs://moz-fx-data-derived-datasets-parquet/clients_daily/v6

        S3_PARQUET_BUCKET
        Path: telemetry-ml/addon_recommender/only_guids_top_200.json

    Output file: 
        S3_BUCKET: telemetry-private-analysis-2
        Path: taar/locale/top10_dict.json


taar_collaborative_recommender

    Computes addons using a collaborative filter.

    Depends On:
        clients_daily over apache hive tables

        S3_BUCKET: telemetry-ml/addon_recommender/only_guids_top_200.json

    Output files:
        s3://telemetry-ml/addon_recommender/addon_mapping.json
        s3://telemetry-ml/addon_recommender/item_matrix.json
        s3://telemetry-ml/addon_recommender/{rundate}/addon_mapping.json
        s3://telemetry-ml/addon_recommender/{rundate}/item_matrix.json


taar_lite
    Compute addon coinstallation rates for TAARlite
    
    Depends On:
            s3a://telemetry-parquet/clients_daily/v6/submission_date_s3={dateformat}

    Output file: 
        S3_BUCKET: telemetry-parquet
        Path: taar/lite/guid_coinstallation.json
