import os
import shutil
import logging
import zipfile
from pathlib import Path
import arcpy

logger = logging.getLogger(__name__)

def delete_fgb(target_db: str):
    if os.path.exists(target_db):
        logger.info(f"Deleting existing fgb: {target_db}")
        shutil.rmtree(target_db)

def backup_feature_class(target_db: str, source_fc: str, backup_fc: str):
    """Rename a feature class.

    NOTE: This will delete any pre-existing feature class with
    the target name. This is destructive and irreversible!
    """

    source_fc_path = os.path.join(target_db, source_fc)
    backup_fc_path = os.path.join(target_db, backup_fc)
    arcpy.env.overwriteOutput = True
    if arcpy.Exists(source_fc_path):
        arcpy.conversion.ExportFeatures(source_fc_path, backup_fc_path)
        logger.info(f'Backed up {source_fc_path} to {backup_fc_path}')
    else:
        logger.info(f'Did not exist so not backed up: {source_fc_path}')

def unzip_fgb(file_path: str, folder: str):
    with zipfile.ZipFile(file_path, "r") as zip_ref:
        gdb_files = [f for f in zip_ref.namelist() if ".gdb/" in f]
        for file in gdb_files:
            zip_ref.extract(file, folder)

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

    if not arcpy.Exists(src):
        logger.error(f"Source feature class does not exist: {src}")
        return

    tgt = os.path.join(target_db, target_fc)
    if not arcpy.Exists(tgt):    
        desc = arcpy.Describe(src)

        logger.info(f"{desc.dataType=}")

        if desc.dataType == "FeatureClass":
            geometry_type = desc.shapeType
            spatial_ref = desc.spatialReference
            arcpy.management.CreateFeatureclass(
                target_db,
                target_fc,
                geometry_type=geometry_type,
                template=src,
                spatial_reference=spatial_ref,
            )
        elif desc.dataType == "Table":
            arcpy.management.CreateTable(
                target_db,
                target_fc,
                template=src,
            )
    enable_editor_tracking(tgt)
    arcpy.management.TruncateTable(tgt)
    # This append copies fields that match and ignores those that don't
    arcpy.management.Append(src, fc, schema_type="NO_TEST")

def enable_editor_tracking(fc):
    """Enable editor tracking on a feature class or table."""
    if not arcpy.Describe(fc).editorTrackingEnabled:
        # editor tracking is optional but useful for future troubleshooting
        arcpy.management.EnableEditorTracking(
            in_dataset=fc,
            creator_field="created_user",
            creation_date_field="created_date",
            last_editor_field="last_edited_user",
            last_edit_date_field="last_edited_date",
            add_fields="ADD_FIELDS",
            record_dates_in="UTC",
        )
        logger.info(f"Editor tracking enabled on: {fc}")



def ensure_target_db_exists(target_db):
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