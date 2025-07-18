# An example showing downloading NZ Parcels for the Thames-Coromandel district.
# Then subsequently fetching changesets.

from kapipy.gis import GISK
from kapipy.helpers import apply_changes
import os
import shutil
import logging
from logging.handlers import RotatingFileHandler
import zipfile
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
from dateutil.relativedelta import relativedelta
import argparse

data_folder = r"c:/temp/data"
log_folder = os.path.join(data_folder, "logs")
os.makedirs(log_folder, exist_ok=True)
log_file = os.path.join(log_folder, "linz.log")

rotatingFileHandler = RotatingFileHandler(
    log_file,
    mode="a",
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
    delay=True,
)
rotatingFileHandler.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[console_handler, rotatingFileHandler],
)
logger = logging.getLogger(__name__)

# find .env automagically by walking up directories until it's found
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)
linz_api_key = os.getenv("LINZ_API_KEY")

# Connect to LINZ
linz = GISK(name="linz", api_key=linz_api_key)
linz.audit.enable_auditing(folder=data_folder)


def export(itm, crop_feature_url: str, target_fgb: str):

    if os.path.exists(target_fgb):
        logger.info(f"Deleting existing fgb: {target_fgb}")
        shutil.rmtree(target_fgb)

    job = itm.export(export_format="geodatabase", out_sr=2193, extent=crop_feature_url)
    result = job.download(folder=data_folder)

    with zipfile.ZipFile(result.file_path, "r") as zip_ref:
        gdb_files = [f for f in zip_ref.namelist() if ".gdb/" in f]
        for file in gdb_files:
            zip_ref.extract(file, data_folder)
    os.remove(result.file_path)


def get_changeset(itm, crop_feature):
    last_download_record = linz.audit.get_latest_request_for_item(
        itm.id, request_type=None
    )
    last_request_time = last_download_record["request_time"]

    changeset_data = itm.changeset(
        from_time=last_request_time, out_sr=2193, filter_geometry=crop_feature
    )

    logger.info(f"Returning changes: {len(changeset_data.sdf)}")

    return changeset_data.sdf

def main(args):

    # This is the Thames-Coromandel District Council crop feature
    crop_feature = linz.content.crop_layers.get(3036).get(10870)

    layers = [
        {
            "id": "50772",
            "fgb": "nz-primary-parcels.gdb",
            "featureclass": "NZ_Primary_Parcels",
        },
        {
            "id": "113764",
            "fgb": "nz-suburbs-and-localities.gdb",
            "featureclass": "NZ_Suburbs_and_Localities",
        },
    ]

    for layer in layers:
        itm = linz.content.get(layer.get("id"))
        id_field = itm.data.primary_key_fields[0]
        target_fgb = os.path.join(data_folder, layer.get("fgb"))
        target_fc = os.path.join(target_fgb, layer.get("featureclass"))

        # This will delete any existing file geodatabase, then export,
        # download and unzip a new one.
        if args.export:
            export(itm, crop_feature.url, target_fgb)

        # This will fetch any changes since the last download.
        # Then apply the changes to the target file geodatabase.
        elif args.changeset:
            changes_sdf = get_changeset(itm, crop_feature)
            apply_changes(changes_sdf, target_fc, id_field=id_field)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog="LINZ Download",
        description="Python script to download LINZ datasets to ArcGIS feature class and keep updated using changesets.",
    )
    parser.add_argument(
        "-e",
        "--export",
        action="store_true",
        help="Flag to export and download a new file geodatabase",
    )
    parser.add_argument(
        "-c",
        "--changeset",
        action="store_true",
        help="Flag indicating to download the layer changeset.",
    )
    args = parser.parse_args()
    main(args)
