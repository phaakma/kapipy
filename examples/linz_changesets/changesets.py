"""
An example showing downloading data from LINZ.
The layers to download are loaded from a configuration yaml file.
Command line parameters define the config file and whether to
do a full export or query for a changeset.
This script assumes a LINZ crop layer is to be used.
Author: Paul Haakma
Date: October 2025
"""

from kapipy.gis import GISK
from kapipy.helpers import apply_changes
import os
import psutil
import shutil
import logging
from logging.handlers import RotatingFileHandler
import zipfile
from pathlib import Path
import argparse
import yaml
import keyring
import re
import arcpy


def configure_logging(audit_folder):
    log_folder = os.path.join(audit_folder, "logs")
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


def delete_fgb(target_db: str):
    if os.path.exists(target_db):
        logger.info(f"Deleting existing fgb: {target_db}")
        shutil.rmtree(target_db)


def unzip_fgb(file_path: str, audit_folder: str):
    with zipfile.ZipFile(file_path, "r") as zip_ref:
        gdb_files = [f for f in zip_ref.namelist() if ".gdb/" in f]
        for file in gdb_files:
            zip_ref.extract(file, audit_folder)


def copy_feature_class(source_fgb, source_fc, target_db, target_fc):
    """
    Copy a feature class, ensuring editor tracking is enabled.
    Create the target feature class if it doesn't exist, with the
    same schema and spatial reference.
    Enable editor tracking if necessary.
    Truncate and append all the data.
    """

    # disable writing gp tool to feature class metadata
    if arcpy.GetLogMetadata():
        arcpy.SetLogMetadata(False)

    src = os.path.join(source_fgb, source_fc)
    tgt = os.path.join(target_db, target_fc)
    if not arcpy.Exists(tgt):
        desc = arcpy.Describe(src)
        geometry_type = desc.shapeType
        spatial_ref = desc.spatialReference
        arcpy.management.CreateFeatureclass(
            target_db,
            target_fc,
            geometry_type=geometry_type,
            template=src,
            spatial_reference=spatial_ref,
        )
    if not arcpy.Describe(tgt).editorTrackingEnabled:
        # editor tracking is optional but useful for future troubleshooting
        arcpy.management.EnableEditorTracking(
            in_dataset=tgt,
            creator_field="created_user",
            creation_date_field="created_date",
            last_editor_field="last_edited_user",
            last_edit_date_field="last_edited_date",
            add_fields="ADD_FIELDS",
            record_dates_in="UTC",
        )
        logger.info(f"Editor tracking enabled on: {tgt}")

    arcpy.management.TruncateTable(tgt)
    # This append copies fields that match and ignores those that don't
    arcpy.management.Append(src, tgt, schema_type="NO_TEST")


def target_db_exists(target_db):
    """Ensure target geodatabase exists.

    If it's a file geodatabase and doesn't exist, create it.
    If it's an enterprise geodatabase and doesn't exist, throw an error.
    """

    logger.debug(f"Checking existence of: {target_db}")
    if arcpy.Exists(target_db):
        return True
    elif target_db.split(".").pop().lower() == "gdb":
        t = Path(target_db)
        out_folder_path = str(t.parent)
        out_name = t.stem
        t.parent.mkdir(parents=True, exist_ok=True)
        arcpy.management.CreateFileGDB(out_folder_path, out_name)
        logger.info(f"Target file geodatabase created.")
        return True
    elif target_db.split(".").pop().lower() == "sde":
        logger.error(f"Target enterprise geodatabase does not exist: {target_db}")
    else:
        logger.error(f"Invalid target geodatabase: {target_db}")
    return False


def process_exports(layers: dict, gisk, audit_folder: str):

    for layer in layers:
        # If the target doesn't exist, no point in processing this layer any further.
        target_db = os.path.join(audit_folder, layer.get("target_db"))
        if not target_db_exists(target_db):
            logger.error(f"Skipping layer {layer.get('id')}")
            continue

        crop_feature_url = None
        crop_layer_id = layer.get("crop_layer_id")
        crop_feature_id = layer.get("crop_feature_id")
        if crop_layer_id is not None and crop_feature_id is not None:
            crop_feature_item = gisk.content.crop_layers.get(crop_layer_id).get(
                crop_feature_id
            )
            crop_feature_url = crop_feature_item.url

        itm = gisk.content.get(layer.get("id"))
        logger.info(f"Processing layer: {itm.id=}, {itm.title=}")
        layer["source_fc"] = itm.feature_class_name
        layer["temp_fgb"] = itm.fgb_name
        out_sr = layer.get("out_sr", 2193)
        logger.info(layer.get("temp_fgb"))
        delete_fgb(layer.get("temp_fgb"))
        # This initiates the export request from LINZ
        itm.export(export_format="geodatabase", out_sr=out_sr, extent=crop_feature_url)

    # poll and download all items
    gisk.content.download(poll_interval=30)

    for job in gisk.content.jobs:
        logger.info(f"Unzipping temp file geodatabases")
        unzip_fgb(file_path=job.download_file_path, audit_folder=audit_folder)
        os.remove(job.download_file_path)

    # copy everything to final target database
    for layer in layers:
        logger.info(f"Copying data to target database")
        temp_fgb = os.path.join(audit_folder, layer.get("temp_fgb"))
        target_db = os.path.join(audit_folder, layer.get("target_db"))
        source_fc = layer.get("source_fc")
        target_fc = layer.get("target_fc")
        copy_feature_class(temp_fgb, source_fc, target_db, target_fc)


def process_changesets(layers: dict, gisk, audit_folder: str):
    for layer in layers:
        try:
            crop_feature_sdf = None
            crop_layer_id = layer.get("crop_layer_id")
            crop_feature_id = layer.get("crop_feature_id")
            if crop_layer_id is not None and crop_feature_id is not None:
                crop_feature_item = gisk.content.crop_layers.get(crop_layer_id).get(
                    crop_feature_id
                )
                crop_feature = crop_feature_item.get()
                crop_feature_sdf = crop_feature.sdf

            itm = gisk.content.get(layer.get("id"))
            logger.info(f"Processing layer: {itm.id=}, {itm.title=}")
            id_field = itm.data.primary_key_fields[0]
            target_db = os.path.join(audit_folder, layer.get("target_db"))
            target_fc = os.path.join(target_db, layer.get("target_fc"))
            out_sr = layer.get("out_sr", 2193)

            changeset_data = itm.query(
                from_time = "AUDIT_MANAGER",
                out_sr=out_sr,
                bbox_geometry=crop_feature_sdf
            )
            number_of_changes = len(changeset_data.sdf)
            logger.info(f"{number_of_changes=}")

            changes_sdf = changeset_data.sdf

            if number_of_changes > 0 and crop_feature_sdf is not None:
                # The select method is used to return just the features that intersect the crop feature
                crop_feature_sdf.spatial.project(spatial_reference=out_sr)
                changes_sdf = changeset_data.sdf.spatial.select(crop_feature_sdf)

            if changes_sdf is None:
                raise Exception(f"A problem occurred fetching changes.")
            apply_changes(changes_sdf, target_fc, id_field=id_field)

        except Exception as e:
            logger.error(str(e), exc_info=True)

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

    audit_folder = config["audit_folder"]
    global logger  # global so we can use it all through the script
    logger = configure_logging(audit_folder)
    layers = configure_layers(config)

    # Connect to LINZ
    # assumes api key previously stored using keyring
    linz_api_key = keyring.get_password(config.get("keyring").get("section"), config.get("keyring").get("username"))
    linz = GISK(name="linz", api_key=linz_api_key)
    linz.audit.enable_auditing(folder=audit_folder)
    linz.content.download_folder = audit_folder

    if args.export:
        process_exports(layers=layers, gisk=linz, audit_folder=audit_folder)
    elif args.changeset:
        process_changesets(layers=layers, gisk=linz, audit_folder=audit_folder)

    logger.info(f"Finished processing all layers")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog="LINZ Download",
        description="Python script to download LINZ datasets to ArcGIS feature class and keep updated using changesets.",
    )
    parser.add_argument("-f", "--file", help="Name of config file.", required=True)
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
