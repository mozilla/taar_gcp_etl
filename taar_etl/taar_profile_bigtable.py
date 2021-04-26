import click


def gcs_avro_uri(gcs_bucket, iso_date):
    # Export of BigQuery into Avro uses GCS_AVRO_URI as the template for
    # filenames.
    return f"""gs://{gcs_bucket}/taar-profile.{iso_date}.avro.*"""


# Construct a BigQuery client object.
class ProfileDataExtraction:
    def __init__(
            self,
            date,
            gcp_project,
            bigquery_dataset_id,
            bigquery_table_id,
            gcs_bucket,
            bigtable_instance_id,
            bigtable_table_id,
            sample_rate,
            subnetwork,
    ):
        from datetime import datetime

        # The GCP project that houses the BigTable database of TAAR user profiles
        self.GCP_PROJECT = gcp_project

        # The BigQuery needs to export a complete table to Avro.
        # The dataset and table IDs specify a table to hold data that will
        # be exported into avro files held in GCS
        self.BIGQUERY_DATASET_ID = bigquery_dataset_id
        self.BIGQUERY_TABLE_ID = bigquery_table_id

        # The GCS bucket that will hold Avro files for export from BigQuery
        # and import into BigTable
        self.GCS_BUCKET = gcs_bucket

        # Timestamp to tag the Avro files in GCS
        self.ISODATE_NODASH = date
        self.ISODATE_DASH = datetime.strptime(date, "%Y%m%d").strftime(
            "%Y-%m-%d"
        )

        self.GCP_PROJECT = gcp_project

        # Avro files are imported into Cloud BigTable.  Instance and Table ID
        # for the Cloud BigTable instance.
        self.BIGTABLE_INSTANCE_ID = bigtable_instance_id
        self.BIGTABLE_TABLE_ID = bigtable_table_id

        self.SAMPLE_RATE = sample_rate

        self.SUBNETWORK = subnetwork

    def run_query(self, sql):
        from google.cloud import bigquery

        client = bigquery.Client()
        job_config = bigquery.QueryJobConfig(use_query_cache=True)
        query_job = client.query(
            sql, job_config=job_config
        )  # Make an API request.

        rows = []
        for row in query_job:
            rows.append(row)
        return rows

    def insert_sql(self):
        return f"""
        CREATE OR REPLACE TABLE
            `{self.GCP_PROJECT}`.{self.BIGQUERY_DATASET_ID}.{self.BIGQUERY_TABLE_ID}
        as (
            select
                client_id,
                city as geo_city,
                SAFE_CAST(subsession_hours_sum * 3600 as int64) as subsession_length,
                locale,
                os,
                active_addons,
                places_bookmarks_count_mean as bookmark_count,
                scalar_parent_browser_engagement_tab_open_event_count_sum as tab_open_count,
                scalar_parent_browser_engagement_total_uri_count_sum as total_uri,
                scalar_parent_browser_engagement_unique_domains_count_mean as unique_tlds
            from
                `moz-fx-data-shared-prod`.telemetry.clients_last_seen
            where
                array_length(active_addons) > 0
                and RAND() < {self.SAMPLE_RATE}
                and submission_date = '{self.ISODATE_DASH}'
        )
        """

    def extract(self):
        self.run_query(self.insert_sql())

    def wipe_bigquery_tmp_table(self):
        from google.cloud import bigquery

        client = bigquery.Client()
        table_id = f"""{self.GCP_PROJECT}.{self.BIGQUERY_DATASET_ID}.{self.BIGQUERY_TABLE_ID}"""
        # If the table does not exist, delete_table raises
        # google.api_core.exceptions.NotFound unless not_found_ok is True.
        print(f"Deleting {table_id}")

        # Make an API request to delete table as DROP TABLE is not
        # suported by BigQuery
        client.delete_table(table_id, not_found_ok=True)
        print("Deleted table '{}'.".format(table_id))

    def dump_avro(self):
        from google.cloud import bigquery

        client = bigquery.Client()
        job_config = bigquery.job.ExtractJobConfig(
            destination_format=bigquery.job.DestinationFormat.AVRO
        )

        dataset_ref = client.dataset(
            self.BIGQUERY_DATASET_ID, project=self.GCP_PROJECT
        )
        table_ref = dataset_ref.table(self.BIGQUERY_TABLE_ID)

        extract_job = client.extract_table(
            table_ref,
            gcs_avro_uri(self.GCS_BUCKET, self.ISODATE_NODASH),
            # Location must match that of the source table.
            location="US",
            job_config=job_config,
        )  # API request
        extract_job.result()  # Waits for job to complete.

    def create_table_in_bigtable(self):
        from google.cloud import bigtable
        from google.cloud.bigtable import column_family
        from google.cloud.bigtable import row_filters
        from datetime import timedelta

        print(
            "Checking if we need to create the {} table.".format(
                self.BIGQUERY_TABLE_ID
            )
        )
        client = bigtable.Client(project=self.GCP_PROJECT, admin=True)
        instance = client.instance(self.BIGTABLE_INSTANCE_ID)
        table = instance.table(self.BIGTABLE_TABLE_ID)

        print("Creating column family `profile`")

        # Define the GC policy to retain only the most recent version
        max_age_rule = column_family.MaxAgeGCRule(timedelta(days=90))
        max_versions_rule = column_family.MaxVersionsGCRule(1)
        gc_rule = column_family.GCRuleUnion(
            rules=[max_age_rule, max_versions_rule]
        )

        # Note that this ties out to the configuration in
        # taar.profile_fetcher::BigTableProfileController
        column_family_id = "profile"
        column_families = {column_family_id: gc_rule}
        if not table.exists():
            table.create(column_families=column_families)
            print(f"Created {column_family_id}")

    def load_bigtable(self, max_num_workers=1, dataflow_service_account=None):
        import apache_beam as beam
        from apache_beam.io.gcp.bigtableio import WriteToBigTable

        self.create_table_in_bigtable()

        options = get_dataflow_options(
            max_num_workers,
            self.GCP_PROJECT,
            f"""taar-profile-load-{self.ISODATE_NODASH}""",
            self.GCS_BUCKET,
            self.SUBNETWORK,
            dataflow_service_account
        )
        with beam.Pipeline(options=options) as p:
            p | "Read" >> beam.io.ReadFromAvro(
                gcs_avro_uri(self.GCS_BUCKET, self.ISODATE_NODASH),
                use_fastavro=True,
            ) | "Create BigTable Rows" >> beam.Map(
                create_bigtable_rows
            ) | "Write Records to Cloud BigTable" >> WriteToBigTable(
                project_id=self.GCP_PROJECT,
                instance_id=self.BIGTABLE_INSTANCE_ID,
                table_id=self.BIGTABLE_TABLE_ID,
            )
        print("Export to BigTable is complete")

    def delete_opt_out(self, days, max_num_workers=1, dataflow_service_account=None):
        import apache_beam as beam
        from apache_beam.io.gcp.bigtableio import WriteToBigTable

        sql = f"""
        select distinct client_id
        from `moz-fx-data-shared-prod.telemetry.deletion_request`
        where date(submission_timestamp) >= DATE_SUB(DATE '{self.ISODATE_DASH}', INTERVAL {days} DAY)
              and date(submission_timestamp) <= '{self.ISODATE_DASH}'
        """

        options = get_dataflow_options(
            max_num_workers,
            self.GCP_PROJECT,
            f"""taar-profile-delete-{self.ISODATE_NODASH}""",
            self.GCS_BUCKET,
            self.SUBNETWORK,
            dataflow_service_account
        )

        with beam.Pipeline(options=options) as p:
            p | "Read from BigQuery" >> beam.io.ReadFromBigQuery(
                query=sql,
                use_standard_sql=True
            ) | "Collect rows" >> beam.Map(
                delete_bigtable_rows
            ) | "Delete in Cloud BigTable" >> WriteToBigTable(
                project_id=self.GCP_PROJECT,
                instance_id=self.BIGTABLE_INSTANCE_ID,
                table_id=self.BIGTABLE_TABLE_ID,
            )


# Cloud Dataflow functions below
def explode_active_addons(jdata):
    import hashlib

    obj = {}
    for k in [
        "geo_city",
        "locale",
        "os",
    ]:
        obj[k] = jdata[k] or ""

    for k in [
        "bookmark_count",
        "tab_open_count",
        "total_uri",
        "unique_tlds",
    ]:
        obj[k] = int(jdata[k] or 0)

    obj["subsession_length"] = int(jdata["subsession_length"] or 0)
    obj["client_id"] = hashlib.sha256(
        jdata["client_id"].encode("utf8")
    ).hexdigest()

    # Now fix the addons

    obj["addon_addon_id"] = []
    obj["addon_blocklisted"] = []
    obj["addon_name"] = []
    obj["addon_user_disabled"] = []
    obj["addon_app_disabled"] = []
    obj["addon_version"] = []
    obj["addon_scope"] = []
    obj["addon_type"] = []
    obj["addon_foreign_install"] = []
    obj["addon_has_binary_components"] = []
    obj["addon_install_day"] = []
    obj["addon_update_day"] = []
    obj["addon_signed_state"] = []
    obj["addon_is_system"] = []
    obj["addon_is_web_extension"] = []
    obj["addon_multiprocess_compatible"] = []

    for rec in jdata["active_addons"]:
        obj["addon_addon_id"].append(rec["addon_id"])
        obj["addon_blocklisted"].append(rec["blocklisted"] or False)
        obj["addon_name"].append(rec["name"] or "")
        obj["addon_user_disabled"].append(rec["user_disabled"] or False)
        obj["addon_app_disabled"].append(rec["app_disabled"] or False)
        obj["addon_version"].append(rec["version"] or "")
        obj["addon_scope"].append(int(rec["scope"] or 0))
        obj["addon_type"].append(rec["type"] or "")
        obj["addon_foreign_install"].append(rec["foreign_install"] or False)
        obj["addon_has_binary_components"].append(
            rec["has_binary_components"] or False
        )
        obj["addon_install_day"].append(int(rec["install_day"] or 0))
        obj["addon_update_day"].append(int(rec["update_day"] or 0))
        obj["addon_signed_state"].append(int(rec["signed_state"] or 0))
        obj["addon_is_system"].append(rec["is_system"] or False)
        obj["addon_is_web_extension"].append(rec["is_web_extension"] or False)
        obj["addon_multiprocess_compatible"].append(
            rec["multiprocess_compatible"] or False
        )

    return obj


def create_bigtable_rows(jdata):
    import datetime
    import json
    import zlib
    import hashlib
    from google.cloud.bigtable import row

    column_family_id = "profile"

    jdata["client_id"] = hashlib.sha256(
        jdata["client_id"].encode("utf8")
    ).hexdigest()

    row_key = jdata["client_id"]
    column = "payload".encode()

    # Coerce float columns to int
    for k in [
        "bookmark_count",
        "tab_open_count",
        "total_uri",
        "unique_tlds",
    ]:
        jdata[k] = int(jdata[k] or 0)
    jdata["subsession_length"] = int(jdata["subsession_length"] or 0)

    direct_row = row.DirectRow(row_key=row_key)
    direct_row.set_cell(
        column_family_id,
        column,
        zlib.compress(json.dumps(jdata).encode("utf8")),
        timestamp=datetime.datetime.utcnow(),
    )

    return direct_row


def delete_bigtable_rows(element):
    from google.cloud.bigtable import row
    import hashlib

    row_key = hashlib.sha256(element['client_id'].encode("utf8")).hexdigest()
    direct_row = row.DirectRow(row_key=row_key)
    direct_row.delete()
    return direct_row


def get_dataflow_options(
        max_num_workers, gcp_project, job_name, gcs_bucket, subnetwork,
        service_account
):
    from apache_beam.options.pipeline_options import (
        GoogleCloudOptions,
        PipelineOptions,
        StandardOptions,
        WorkerOptions,
    )

    options = PipelineOptions()

    # For Cloud execution, specify DataflowRunner and set the Cloud Platform
    # project, job name, staging file location, temp file location, and region.
    options.view_as(StandardOptions).runner = "DataflowRunner"

    # Coerece the options to a WorkerOptions type to fix the scaling
    # and max workers
    options.view_as(WorkerOptions).max_num_workers = max_num_workers

    # Note that autoscaling *must* be set to a non-default value or
    # the cluster will never scale up
    options.view_as(WorkerOptions).autoscaling_algorithm = "THROUGHPUT_BASED"
    if subnetwork:
        options.view_as(WorkerOptions).subnetwork = subnetwork

    # Coerece the options to a GoogleCloudOptions type and set up
    # GCP specific options
    options.view_as(GoogleCloudOptions).project = gcp_project
    options.view_as(GoogleCloudOptions).job_name = job_name
    options.view_as(GoogleCloudOptions).temp_location = f"gs://{gcs_bucket}/tmp"
    options.view_as(GoogleCloudOptions).region = "us-west1"
    if service_account:
        options.view_as(GoogleCloudOptions).service_account_email = service_account

    return options


@click.command()
@click.option(
    "--iso-date",
    required=True,
    help="Date as YYYYMMDD. Used to specify timestamps for avro files in GCS.",
)
@click.option(
    "--gcp-project", type=str, required=True, help="GCP Project to run in",
)
@click.option(
    "--bigquery-dataset-id",
    help="The BigQuery dataset ID that the user profile data will be held in prior to Avro export.",
    default="taar_tmp",
)
@click.option(
    "--bigquery-table-id",
    help="The BigQuery table ID that the user profile data will be held in prior to Avro export.",
    default="taar_tmp_profile",
)
@click.option(
    "--avro-gcs-bucket",
    help="Google Cloud Storage bucket to hold Avro output files",
    required=True,
)
@click.option(
    "--bigtable-instance-id", help="BigTable Instance ID", required=True,
)
@click.option(
    "--bigtable-table-id", help="BigTable Table ID", default="taar_profile",
)
@click.option(
    "--dataflow-workers",
    type=int,
    default=20,
    help="Number of dataflow workers to use for stages which use dataflow "
         "(export to BigTable and profiles deletion).",
)
@click.option(
    "--dataflow-service-account",
    help="Specifies a user-managed controller service account, using the format "
         "my-service-account-name@<project-id>.iam.gserviceaccount.com. "
         "For more information, see the Controller service account section of the "
         "Cloud Dataflow security and permissions page. "
         "If not set, workers use your project's Compute Engine service account as the controller service account."
)
@click.option(
    "--sample-rate",
    help="Sampling rate (0 to 1.0) of clients to pull from clients_last_seen",
    default=0.0001,
)
@click.option(
    "--subnetwork",
    help="GCE subnetwork for launching workers. Default is up to the "
    "Dataflow service. Expected format is "
    "regions/REGION/subnetworks/SUBNETWORK or the fully qualified "
    "subnetwork name. For more information, see "
    "https://cloud.google.com/compute/docs/vpc/"
)
@click.option(
    "--fill-bq",
    "stage",
    help="Populate a bigquery table to prepare for Avro export on GCS",
    flag_value="fill-bq",
    required=True,
    default=True,
)
@click.option(
    "--bq-to-gcs",
    "stage",
    help="Export BigQuery table to Avro files on GCS",
    flag_value="bq-to-gcs",
    required=True,
)
@click.option(
    "--gcs-to-bigtable",
    "stage",
    help="Import Avro files into BigTable",
    flag_value="gcs-to-bigtable",
    required=True,
)
@click.option(
    "--wipe-bigquery-tmp-table",
    "stage",
    help="Remove temporary table from BigQuery",
    flag_value="wipe-bigquery-tmp-table",
    required=True,
)
@click.option(
    "--bigtable-delete-opt-out",
    "stage",
    help="Delete data from Bigtable for users that sent telemetry deletion requests in the last N days.",
    flag_value="bigtable-delete-opt-out",
    required=True,
)
@click.option(
    "--delete-opt-out-days",
    help="The number of days to analyze telemetry deletion requests for.",
    default=28,
)
def main(
        iso_date,
        gcp_project,
        bigquery_dataset_id,
        bigquery_table_id,
        avro_gcs_bucket,
        bigtable_instance_id,
        bigtable_table_id,
        dataflow_workers,
        dataflow_service_account,
        sample_rate,
        subnetwork,
        stage,
        delete_opt_out_days
):
    print(
        f"""
===
Running job with :
    SAMPLE RATE             : {sample_rate}
    DATAFLOW_WORKERS        : {dataflow_workers}
    DATAFLOW_SERVICE_ACCOUNT: {dataflow_service_account}
    GCP_PROJECT             : {gcp_project}
    GCS_BUCKET              : {avro_gcs_bucket}
    BIGQUERY_DATASET_ID     : {bigquery_dataset_id}
    BIGQUERY_TABLE_ID       : {bigquery_table_id}
    BIGTABLE_INSTANCE_ID    : {bigtable_instance_id}
    BIGTABLE_TABLE_ID       : {bigtable_table_id}
    ISODATE_NODASH          : {iso_date}
    SUBNETWORK              : {subnetwork}
    STAGE                   : {stage}
    DELETE_OPT_OUT_DAYS      : {delete_opt_out_days}
===
"""
    )
    extractor = ProfileDataExtraction(
        iso_date,
        gcp_project,
        bigquery_dataset_id,
        bigquery_table_id,
        avro_gcs_bucket,
        bigtable_instance_id,
        bigtable_table_id,
        sample_rate,
        subnetwork,
    )

    if stage == "fill-bq":
        print("Starting BigQuery export")
        extractor.extract()
        print("BQ export complete")
    elif stage == "bq-to-gcs":
        print("Avro export starting")
        extractor.dump_avro()
        print("Avro dump completed")
    elif stage == "gcs-to-bigtable":
        print("BigTable import starting")
        extractor.load_bigtable(dataflow_workers, dataflow_service_account)
        print("BigTable import completed")
    elif stage == "wipe-bigquery-tmp-table":
        print("Clearing temporary BigQuery table: ")
        extractor.wipe_bigquery_tmp_table()
        print("BigTable clearing completed")
    elif stage == "bigtable-delete-opt-out":
        print("Deleting opt-out users from Bigtable")
        extractor.delete_opt_out(delete_opt_out_days, dataflow_workers, dataflow_service_account)
        print("BigTable opt-out users deletion completed")


if __name__ == "__main__":
    main()
