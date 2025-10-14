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

def convert_title_to_fc(text):
    # Replace any non-alphanumeric characters with underscore
    # This seems to be the Koordinates method for setting the feature class names
    return re.sub(r'[^0-9A-Za-z]', '_', text)


def convert_title_to_fgb(text):
    # Remove parentheses and commas completely
    cleaned = re.sub(r"[(),]", "", text)
    
    # Convert scale "1:50k" to "150k" by removing colon
    cleaned = re.sub(r"(\d):(\d+k)", r"\1\2", cleaned)
    
    # Replace any remaining non-alphanumeric characters (including spaces) with dash
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "-", cleaned)
    
    # Remove leading/trailing dashes and lowercase
    return f"{cleaned.strip('-').lower()}.gdb"


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

def delete_fgb(target_db: str):
    if os.path.exists(target_db):
        logger.info(f"Deleting existing fgb: {target_db}")
        shutil.rmtree(target_db)

def unzip_fgb(file_path: str, folder: str):
    with zipfile.ZipFile(file_path, "r") as zip_ref:
        gdb_files = [f for f in zip_ref.namelist() if ".gdb/" in f]
        for file in gdb_files:
            zip_ref.extract(file, folder)

def copy_feature_class(source_fgb, source_fc, target_db, target_fc): 

    # disable writing gp tool to feature class metadata
    if arcpy.GetLogMetadata():
        arcpy.SetLogMetadata(False)

    src = os.path.join(source_fgb, source_fc)
    tgt = os.path.join(target_db, target_fc)
    logger.info(f"Source feature class: {src}")
    logger.info(f"Target feature class: {tgt}")

    logger.info(arcpy.Exists(src))
    logger.info(arcpy.Exists(tgt))

    if not arcpy.Exists(src):
        raise ValueError(f"Source feature class does not exist")

    if not arcpy.Exists(tgt):
        desc = arcpy.Describe(src)
        geometry_type = desc.shapeType
        spatial_ref = desc.spatialReference
        arcpy.management.CreateFeatureclass(
            target_db, 
            target_fc, 
            geometry_type=geometry_type,
            template=src,
            spatial_reference=spatial_ref
            ) 
    if not arcpy.Describe(tgt).editorTrackingEnabled:
        #editor tracking is optional but useful for future troubleshooting 
        arcpy.management.EnableEditorTracking(
            in_dataset=tgt,
            creator_field="created_user",
            creation_date_field="created_date",
            last_editor_field="last_edited_user",
            last_edit_date_field="last_edited_date",
            add_fields="ADD_FIELDS",
            record_dates_in="UTC"
        )
        logger.info(f"Editor tracking enabled on: {tgt}")
    

    arcpy.management.TruncateTable(tgt)
    # This append copies fields that match and ignores those that don't
    arcpy.management.Append(src, tgt, schema_type="NO_TEST")



def target_db_exists(target_db):
    # ensure target geodatabase exists.
    # If it's a file geodatabase and doesn't exist, create it.
    # If it's an enterprise geodatabase and doesn't exist, throw an error.

    logger.debug(f"Checking existence of: {target_db}")
    if arcpy.Exists(target_db):
        return True
    elif target_db.split('.').pop().lower() == "gdb":
        t = Path(target_db)
        out_folder_path = str(t.parent)
        out_name = t.stem
        t.parent.mkdir(parents=True, exist_ok=True)
        arcpy.management.CreateFileGDB(out_folder_path, out_name)
        logger.info(f"Target file geodatabase created.")
        return True
    elif target_db.split('.').pop().lower() == "sde":
        logger.error(f'Target enterprise geodatabase does not exist: {target_db}')
    else:
        logger.error(f'Invalid target geodatabase: {target_db}')
    return False 


def process_exports(layers: dict, gisk, folder: str, crop_sdf):

    for layer in layers:
        # If the target doesn't exist, no point in processing this layer any further.
        target_db = layer.get("target_db")
        if not target_db_exists(target_db):
            logger.error(f"Skipping layer {layer.get('id')}")
            continue

        itm = gisk.content.get(layer.get("id"))
        logger.info(f"Processing layer: {itm.id=}, {itm.title=}")
        layer["source_fc"] = convert_title_to_fc(itm.title)
        layer["temp_fgb"] = convert_title_to_fgb(itm.title)
        out_sr = layer.get("out_sr", 2193)
        logger.info(f"Temp gdb: {layer.get('temp_fgb')}")
        logger.info(f"Feature class: {layer.get('source_fc')}")
        delete_fgb(layer.get("temp_fgb"))
        #This initiates the export request from LINZ
        itm.export(export_format="geodatabase", out_sr=out_sr, bbox_geometry=crop_sdf)

    # poll and download all items
    gisk.content.download(poll_interval=30)

    for job in gisk.content.jobs:
        logger.info(f'Unzipping temp file geodatabases')
        unzip_fgb(file_path=job.download_file_path, folder=folder)
        os.remove(job.download_file_path)

    # copy everything to final target database  
    for layer in layers:
        logger.info(f'Copying data to target database')
        temp_fgb = os.path.join(folder, layer.get("temp_fgb"))               
        target_db = layer.get("target_db")
        source_fc = layer.get("source_fc")
        target_fc = layer.get("target_fc")
        copy_feature_class(temp_fgb, source_fc, target_db, target_fc)        


def configure_layers(config, section):
    defaults = config["defaults"]
    layers = []
    for item in config.get(section, []):
        # Inherit defaults and override with item-specific values
        layer = {**defaults, **item}
        layers.append(layer)
    return layers

def main(args):    
    
    script_dir = Path(__file__).parent.resolve()
    config_path = script_dir / args.file

    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    audit_folder = config.get("audit_folder")
    global logger # global so we can use it all through the script
    logger = configure_logging(audit_folder)
    linz_layers = configure_layers(config, "linz_layers") 
    statsnz_layers = configure_layers(config, "statsnz_layers") 

    logger.info(linz_layers)
    logger.info(statsnz_layers)   

    # Connect to StatsNZ
    # assumes api key previously stored using keyring
    statsnz_api_key = keyring.get_password("statsnz", "kapipy_example")
    statsnz = GISK(name="statsnz", api_key=statsnz_api_key)
    statsnz.audit.enable_auditing(folder=audit_folder)
    statsnz.content.download_folder = audit_folder

    regional_councils = statsnz.content.get("120946")
    waikato_region = regional_councils.query(cql_filter="REGC2025_V1_00_NAME='Waikato Region'")
    logger.info(f'Waikato Region: {len(waikato_region.sdf)}')

    process_exports(layers=statsnz_layers, gisk=statsnz, folder=audit_folder, crop_sdf=waikato_region.sdf)    

    # Connect to LINZ
    # assumes api key previously stored using keyring
    linz_api_key = keyring.get_password("linz", "kapipy_example")
    linz = GISK(name="linz", api_key=linz_api_key)
    linz.audit.enable_auditing(folder=audit_folder)
    linz.content.download_folder = audit_folder
    process_exports(layers=linz_layers, gisk=linz, folder=audit_folder, crop_sdf=waikato_region.sdf)    

    logger.info(f"Finished processing all layers")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog="LINZ Download",
        description="Python script to download LINZ datasets to ArcGIS feature classes.",
    )
    parser.add_argument(
        "-f",
        "--file",
        help="Name of config file.",
        required=True
    )

    args = parser.parse_args()
    main(args)
