"""
An example showing downloading data from LINZ.
The layers to download are loaded from a configuration yaml file.
Command line parameters define the config file and whether to
do a full export or query for a changeset.
This script assumes a LINZ crop layer is to be used.
Author: Paul Haakma
Date: August 2025
"""

from kapipy.gis import GISK
from kapipy.helpers import apply_changes
import os
import shutil
import logging
from logging.handlers import RotatingFileHandler
import zipfile
from pathlib import Path
import argparse
import yaml
import keyring
import arcpy

def configure_logging(data_folder):
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
        format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        handlers=[console_handler, rotatingFileHandler],
    )
    logger = logging.getLogger(__name__)
    return logger


def buildErrorMessage(e):
    errorMessage = ""
    # Build and show the error message
    # If many arguments
    if (e.args):
        for i in range(len(e.args)):
            if (i == 0):
                errorMessage = str(e.args[i]).encode('utf-8').decode('utf-8')
            else:
                errorMessage = errorMessage + " " + \
                    str(e.args[i]).encode('utf-8').decode('utf-8')
    # Else just one argument
    else:
        errorMessage = str(e)
    return errorMessage.strip().replace("\n", " ").replace("\r", "").replace("'", "")[:1000]

def delete_fgb(target_fgb: str):
    if os.path.exists(target_fgb):
        logger.info(f"Deleting existing fgb: {target_fgb}")
        shutil.rmtree(target_fgb)

def unzip_fgb(file_path: str, data_folder: str):
    with zipfile.ZipFile(file_path, "r") as zip_ref:
        gdb_files = [f for f in zip_ref.namelist() if ".gdb/" in f]
        for file in gdb_files:
            zip_ref.extract(file, data_folder)

def process_exports(layers: dict, gisk, data_folder: str):
    fgb_list = []    
    for layer in layers:
        crop_feature_url = None 
        crop_feature_sdf = None                     
        crop_layer_id = layer.get("crop_layer_id")
        crop_feature_id = layer.get("crop_feature_id")
        if crop_layer_id is not None and crop_feature_id is not None:
            crop_feature_item = gisk.content.crop_layers.get(crop_layer_id).get(crop_feature_id)
            crop_feature = crop_feature_item.get()
            crop_feature_url = crop_feature_item.url
            crop_feature_sdf = crop_feature.sdf

        itm = gisk.content.get(layer.get("id"))
        logger.info(f"Processing layer: {itm.id=}, {itm.title=}")
        id_field = itm.data.primary_key_fields[0]
        target_fgb = os.path.join(data_folder, layer.get("fgb"))
        fgb_list.append(target_fgb)
        target_fc = os.path.join(target_fgb, layer.get("featureclass"))
        out_sr = layer.get("out_sr", 2193)

        delete_fgb(target_fgb)
        #This initiates the export request from LINZ
        itm.export(export_format="geodatabase", out_sr=out_sr, extent=crop_feature_url)

    # poll and download all items
    gisk.content.download(poll_interval=30)
    for job in gisk.content.jobs:
        unzip_fgb(file_path=job.download_file_path, data_folder=data_folder)
        os.remove(job.download_file_path)

    for target_fgb in fgb_list:
        #editor tracking is optional but useful for future troubleshooting
        enable_editor_tracking(target_fgb)


def process_changesets(layers: dict, gisk, data_folder: str):
    for layer in layers:
        try:
            crop_feature_url = None 
            crop_feature_sdf = None                     
            crop_layer_id = layer.get("crop_layer_id")
            crop_feature_id = layer.get("crop_feature_id")
            if crop_layer_id is not None and crop_feature_id is not None:
                crop_feature_item = gisk.content.crop_layers.get(crop_layer_id).get(crop_feature_id)
                crop_feature = crop_feature_item.get()
                crop_feature_url = crop_feature_item.url
                crop_feature_sdf = crop_feature.sdf

            itm = gisk.content.get(layer.get("id"))
            logger.info(f"Processing layer: {itm.id=}, {itm.title=}")
            id_field = itm.data.primary_key_fields[0]
            target_fgb = os.path.join(data_folder, layer.get("fgb"))
            target_fc = os.path.join(target_fgb, layer.get("featureclass"))
            out_sr = layer.get("out_sr", 2193)

            changes_sdf = get_changeset(itm, crop_feature_sdf, out_sr=out_sr, gisk=gisk)
            if changes_sdf is None:
                raise Exception(f"A problem occured fetching changes.")
            apply_changes(changes_sdf, target_fc, id_field=id_field)

        except Exception as e:
            err = buildErrorMessage(e)
            logger.error(err, exc_info=True)

def enable_editor_tracking(fgb):
    arcpy.env.workspace = fgb
    for fc in arcpy.ListFeatureClasses():        
        arcpy.management.EnableEditorTracking(
            in_dataset=fc,
            creator_field="created_user",
            creation_date_field="created_date",
            last_editor_field="last_edited_user",
            last_edit_date_field="last_edited_date",
            add_fields="ADD_FIELDS",
            record_dates_in="UTC"
        )
        logger.info(f"Editor tracking enabled on: {fc}")

def get_changeset(itm, crop_sdf, out_sr, gisk):
    last_download_record = gisk.audit.get_latest_request_for_item(
        itm.id, request_type=None
    )
    
    if not last_download_record or last_download_record.get("request_time") is None:
        logger.warning(f"No previous request exists in audit database. Please run a full export first to seed the data.")
        return None
    else:
        last_request_time = last_download_record.get("request_time")
        logger.info(f"{last_request_time=}")

    changeset_data = itm.changeset(
        from_time=last_request_time, out_sr=out_sr, bbox_geometry=crop_sdf
    )

    crop_sdf.spatial.project(spatial_reference=out_sr)
    number_of_changes = len(changeset_data.sdf)
    logger.info(f"Returning changes: {number_of_changes}")

    if number_of_changes > 0:
        # The select method is used to return just the features that intersect the crop feature
        return changeset_data.sdf.spatial.select(crop_sdf)
    return changeset_data.sdf

def configure_layers(config):
    defaults = config["defaults"]
    layers = []
    for item in config["layers"]:
        # Inherit defaults and override with item-specific values
        layer = {**defaults, **item}
        layers.append(layer)
    return layers

def main(args):
    
    script_dir = Path(__file__).parent.resolve()
    config_path = script_dir / args.file

    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    data_folder = config["data_folder"]
    global logger # global so we can use it all through the script
    logger = configure_logging(data_folder)
    layers = configure_layers(config) 

    # Connect to LINZ
    # assumes api key previously stored using keyring
    linz_api_key = keyring.get_password("kapipy", "linz")
    linz = GISK(name="linz", api_key=linz_api_key)
    linz.audit.enable_auditing(folder=data_folder)
    linz.content.download_folder = data_folder

    if args.export:
        process_exports(layers=layers, gisk=linz, data_folder=data_folder)
    elif args.changeset:
        process_changesets(layers=layers, gisk=linz, data_folder=data_folder)
    
    logger.info(f"Finished processing all layers")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog="LINZ Download",
        description="Python script to download LINZ datasets to ArcGIS feature class and keep updated using changesets.",
    )
    parser.add_argument(
        "-f",
        "--file",
        help="Name of config file.",
        required=True
    )
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "-e",
        "--export",
        action="store_true",
        help="Flag to export and download a new file geodatabase",
    )
    action_group.add_argument(
        "-c",
        "--changeset",
        action="store_true",
        help="Flag indicating to download the layer changeset.",
    )

    args = parser.parse_args()
    main(args)
