TAARlite and TAAR ETL jobs for GCP
==================================


This repo contains scripts which are used in ETL jobs for the TAAR and
TAARlite services.

TODO document each major module here:

  taar_amodump.py 
  taar_amowhitelist.py
  taar_lite_guidguid.py
  taar_update_whitelist.py
  taar_utils.py
  taar_utils.pyc


S3 Buckets
==========

This is a list of buckets that we are writing to in S3

Bucket                          Path
======================          =================================
telemetry-parquet               telemetry-ml/addon_recommender/
telemetry-parquet               taar/ensemble/
telemetry-parquet               taar/lite/
telemetry-private-analysis-2    taar/locale/
telemetry-parquet               taar/similarity/
srg-team-bucket                 *
