"""
This ETL job computes the number of installations for all addons.
"""

import logging

import click
from google.cloud import bigquery

from taar_etl.taar_utils import store_json_to_gcs

OUTPUT_BUCKET = "taar_models"
OUTPUT_PREFIX = "taar/lite"
OUTPUT_FILENAME = "guid_install_ranking.json"


def extract_telemetry(iso_today):
    telemetry_client = bigquery.Client()
    res = telemetry_client.query(f'''  
      SELECT
          addon_id as addon_guid,
          count(client_id) as install_count
      FROM
          `moz-fx-data-shared-prod`.telemetry.addons
      WHERE submission_date = DATE('{iso_today}')
      GROUP BY addon_id
      ''')

    return {row[0]: row[1] for row in res.result()}


@click.command()
@click.option("--date", required=True)
@click.option("--bucket", default=OUTPUT_BUCKET)
@click.option("--prefix", default=OUTPUT_PREFIX)
def main(date, bucket, prefix):
    logging.info("Processing GUID install rankings")

    result_data = extract_telemetry(date)
    store_json_to_gcs(bucket, prefix, OUTPUT_FILENAME, result_data, date)


if __name__ == "__main__":
    main()
