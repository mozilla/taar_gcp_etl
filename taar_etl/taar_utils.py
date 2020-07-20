# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import bz2
import contextlib
import hashlib
import io
import json
import logging
import os.path
import shutil
import tempfile
from google.cloud import storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AMO_DUMP_BUCKET = "taar_models"

AMO_WHITELIST_PREFIX = "addon_recommender"
AMO_WHITELIST_FNAME = "whitelist_addons_database.json"
AMO_CURATED_WHITELIST_FNAME = "only_guids_top_200.json"


@contextlib.contextmanager
def selfdestructing_path(dirname):
    yield dirname
    shutil.rmtree(dirname)


def store_json_to_gcs(
    bucket, prefix, filename, json_obj, iso_date_str, compress=True
):
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

    byte_data = bz2.compress(byte_data)
    logger.info(f"Compressed data is {len(byte_data)} bytes")

    client = storage.Client()
    bucket = client.get_bucket(bucket)
    simple_fname = f"{prefix}/{filename}.bz2"
    blob = bucket.blob(simple_fname)
    blob.chunk_size = 5 * 1024 * 1024  # Set 5 MB blob size
    print(f"Wrote out {simple_fname}")
    blob.upload_from_string(byte_data)
    long_fname = f"{prefix}/{filename}.{iso_date_str}.bz2"
    blob = bucket.blob(long_fname)
    blob.chunk_size = 5 * 1024 * 1024  # Set 5 MB blob size
    print(f"Wrote out {long_fname}")
    blob.upload_from_string(byte_data)


def read_from_gcs(fname, prefix, bucket):
    with io.BytesIO() as tmpfile:
        client = storage.Client()
        bucket = client.get_bucket(bucket)
        simple_fname = f"{prefix}/{fname}.bz2"
        blob = bucket.blob(simple_fname)
        blob.download_to_file(tmpfile)
        tmpfile.seek(0)
        payload = tmpfile.read()
        payload = bz2.decompress(payload)
        return json.loads(payload.decode("utf8"))


def load_amo_external_whitelist():
    """ Download and parse the AMO add-on whitelist.

    :raises RuntimeError: the AMO whitelist file cannot be downloaded or contains
                          no valid add-ons.
    """
    final_whitelist = []
    amo_dump = read_from_gcs(AMO_WHITELIST_FNAME, AMO_WHITELIST_PREFIX, AMO_DUMP_BUCKET)

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
    whitelist = read_from_gcs(
        "only_guids_top_200.json", "addon_recommender", "taar_models",
    )
    return list(whitelist)


def hash_telemetry_id(telemetry_id):
    """
        This hashing function is a reference implementation based on :
            https://phabricator.services.mozilla.com/D8311

    """
    return hashlib.sha256(telemetry_id.encode("utf8")).hexdigest()
