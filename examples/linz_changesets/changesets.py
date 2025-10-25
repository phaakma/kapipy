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

from utils.feature_class_utils import (
    delete_fgb,
    unzip_fgb,
    copy_feature_class,
    ensure_target_db_exists,
    enable_editor_tracking,
)
from utils.timing_utils import timer 

CROP_FEATURE_CACHE = {}


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


def process_changesets(layers: dict, gisk, temp_folder: str, from_time: str = "AUDIT_MANAGER"):
    """Process each layer defined in the layers configuration.
    Args:
        layers (dict): The layers configuration.
        gisk (GISK): An authenticated GISK instance.
        temp_folder (str): Path to a temporary folder for processing.
        from_time (str, optional): The from_time parameter for changeset queries. Defaults to "AUDIT_MANAGER".

    Raises:
        Exception: If there is a problem fetching changes.
    """
    for layer in layers:
        try:
            crop_feature_sdf = None
            crop_layer_id = layer.get("crop_layer_id")
            crop_feature_id = layer.get("crop_feature_id")
            if crop_layer_id is not None and crop_feature_id is not None:
                crop_uid = f"{crop_layer_id}_{crop_feature_id}"
                if crop_uid in CROP_FEATURE_CACHE:
                    crop_feature_sdf = CROP_FEATURE_CACHE[crop_uid]
                else:
                    crop_feature_item = gisk.content.crop_layers.get(crop_layer_id).get(
                        crop_feature_id
                    )
                    crop_feature = crop_feature_item.get()
                    crop_feature_sdf = crop_feature.sdf
                    CROP_FEATURE_CACHE[crop_uid] = crop_feature_sdf

            itm = gisk.content.get(layer.get("id"))
            logger.info(f"Processing layer: {itm.id=}, {itm.title=}")
            id_field = itm.data.primary_key_fields[0]
            target_db = os.path.join(temp_folder, layer.get("target_db"))
            target_fc = os.path.join(target_db, layer.get("target_fc"))
            out_sr = layer.get("out_sr", 2193)

            changeset_data = itm.query(
                from_time = from_time,
                out_sr=out_sr,
                bbox_geometry=crop_feature_sdf,
            )
            number_of_records = len(changeset_data.sdf)
            logger.info(f"{number_of_records=}")

            if number_of_records > 0:
                logger.info(f"Preparing to apply changes to {target_fc}")
                changes_sdf = changeset_data.sdf
                if crop_feature_sdf is not None:
                    # The select method is used to return just the features that intersect the crop feature
                    # bbox_geometry is used instead of filter_geometry because we cannot be sure that 
                    # the polygon has less than 1000 vertices (a limitation of the LINZ WFS API).
                    crop_feature_sdf.spatial.project(spatial_reference=out_sr)
                    changes_sdf = changeset_data.sdf.spatial.select(crop_feature_sdf)

                if changes_sdf is None:
                    raise Exception(f"A problem occurred fetching changes.")
                
                ensure_target_db_exists(target_db)
                if changeset_data.is_changeset:
                    logger.info(f"Applying changeset with {len(changes_sdf)=}")
                    apply_changes(changes_sdf, target_fc, id_field=id_field)
                else:
                    logger.info(f"Full export with {len(changes_sdf)=}")
                    changes_sdf.spatial.to_featureclass(location=target_fc)
                    enable_editor_tracking(target_fc)
            else:
                logger.info(f"No changes to apply for layer: {itm.id=}, {itm.title=}")

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
    authentication_config = config.get("authentication", {})
    linz_api_key = keyring.get_password(authentication_config.get("section"), authentication_config.get("username"))
    linz = GISK(name="linz", api_key=linz_api_key)
    linz.audit.enable_auditing(folder=audit_folder)

    if args.changeset:
        from_time = "AUDIT_MANAGER"
    elif args.all:
        from_time = None #force a full download of all data

    with timer():
        process_changesets(layers=layers, gisk=linz, temp_folder=audit_folder, from_time=from_time)

    logger.info(f"Finished processing all layers")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog="LINZ Download",
        description="Python script to download LINZ datasets to ArcGIS feature class and keep updated using changesets.",
    )
    parser.add_argument("-f", "--file", help="Name of config file.", required=True)
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "-c",
        "--changeset",
        action="store_true",
        help="Flag indicating to download the layer changeset.",
    )
    action_group.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Flag indicating to download ALL layer data.",
    )

    args = parser.parse_args()
    main(args)
