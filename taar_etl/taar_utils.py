# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib
import hashlib
import json
import logging
import os.path
import shutil
import tempfile

import boto3
from botocore.exceptions import ClientError
from google.cloud import storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AMO_DUMP_BUCKET = "telemetry-parquet"
AMO_DUMP_KEY = "telemetry-ml/addon_recommender/addons_database.json"

AMO_WHITELIST_KEY = (
    "telemetry-ml/addon_recommender/whitelist_addons_database.json"
)
AMO_CURATED_WHITELIST_KEY = (
    "telemetry-ml/addon_recommender/only_guids_top_200.json"
)


@contextlib.contextmanager
def selfdestructing_path(dirname):
    yield dirname
    shutil.rmtree(dirname)


def store_json_to_gcs(bucket, prefix, filename, json_obj, iso_date_str):
    """Saves the JSON data to a local file and then uploads it to GCS.

    Two copies of the file will get uploaded: one with as "<base_filename>.json"
    and the other as "<base_filename><YYYYMMDD>.json" for backup purposes.

    :param bucket: The GCS bucket name.
    :param prefix: The GCS prefix.
    :param filename: A string with the base name of the file to use for saving
        locally and uploading to GCS
    :param json_data: A string with the JSON content to write.
    :param date: A date string in the "YYYYMMDD" format.
    """
    byte_data = json.dumps(json_obj).encode("utf8")
    client = storage.Client()
    bucket = client.get_bucket(bucket)
    simple_fname = f"{prefix}/{filename}.json"
    blob = bucket.blob(simple_fname)
    print(f"Wrote out {simple_fname}")
    blob.upload_from_string(byte_data)
    long_fname = f"{prefix}/{filename}.{iso_date_str}.json"
    blob = bucket.blob(long_fname)
    print(f"Wrote out {long_fname}")
    blob.upload_from_string(byte_data)


def load_amo_external_whitelist():
    """ Download and parse the AMO add-on whitelist.

    :raises RuntimeError: the AMO whitelist file cannot be downloaded or contains
                          no valid add-ons.
    """
    final_whitelist = []
    amo_dump = {}
    try:
        # Load the most current AMO dump JSON resource.
        s3 = boto3.client("s3")
        s3_contents = s3.get_object(
            Bucket=AMO_DUMP_BUCKET, Key=AMO_WHITELIST_KEY
        )
        amo_dump = json.loads(s3_contents["Body"].read().decode("utf-8"))
    except ClientError:
        logger.exception(
            "Failed to download from S3",
            extra={"bucket": AMO_DUMP_BUCKET, "key": AMO_DUMP_KEY},
        )

    # If the load fails, we will have an empty whitelist, this may be problematic.
    for key, value in list(amo_dump.items()):
        addon_files = value.get("current_version", {}).get("files", {})
        # If any of the addon files are web_extensions compatible, it can be recommended.
        if any([f.get("is_webextension", False) for f in addon_files]):
            final_whitelist.append(value["guid"])

    if len(final_whitelist) == 0:
        raise RuntimeError("Empty AMO whitelist detected")

    return final_whitelist


def load_amo_curated_whitelist():
    """
    Return the curated whitelist of addon GUIDs
    """
    whitelist = read_from_s3(
        "only_guids_top_200.json",
        "telemetry-ml/addon_recommender/",
        "telemetry-parquet",
    )
    return list(whitelist)


def hash_telemetry_id(telemetry_id):
    """
        This hashing function is a reference implementation based on :
            https://phabricator.services.mozilla.com/D8311

    """
    return hashlib.sha256(telemetry_id.encode("utf8")).hexdigest()
