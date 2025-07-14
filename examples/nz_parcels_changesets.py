# An example showing downloading NZ Parcels for the Thames-Coromandel district.
# Then subsequently fetching changesets.

from kapipy.gis import GISK
import arcpy
import os
import shutil
import logging
from logging.handlers import RotatingFileHandler
import zipfile
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
from dateutil.relativedelta import relativedelta

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
console_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        console_handler,
        rotatingFileHandler
    ],
)
logger = logging.getLogger(__name__)


# find .env automagically by walking up directories until it's found
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)
linz_api_key = os.getenv("LINZ_API_KEY")

# Connect to LINZ
linz = GISK(name="linz", api_key=linz_api_key)
linz.audit.enable_auditing(folder=data_folder)

def version():
    import kapipy
    logger.info(kapipy.__version__)


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
    last_download_record = linz.audit.get_latest_request_for_item(itm.id, request_type=None)
    last_request_time = last_download_record['request_time']

    ### For testing....
    # dt = datetime.fromisoformat(last_request_time)
    # from_time = dt - relativedelta(months=3)
    # from_time_str = from_time.isoformat()
    # logger.info(f'{from_time_str=}')

    changeset_data = itm.changeset(
    from_time=last_request_time,
    out_sr=2193,
    filter_geometry=crop_feature
    )

    logger.info(f'Returning changes: {len(changeset_data.sdf)}')

    return changeset_data.sdf

def apply_changes(changes_sdf, target_fc, id_field):
    if changes_sdf.empty:
        logger.info(f'No changes were returned.')
        return

    inserts = changes_sdf[changes_sdf['__change__'] == 'INSERT']
    updates = changes_sdf[changes_sdf['__change__'] == 'UPDATE']
    deletes = changes_sdf[changes_sdf['__change__'] == 'DELETE']

    if not inserts.empty:
        logger.info(f'Processing {len(inserts)} inserts.')

        inserts_fc = inserts.to_featureset()
        arcpy.management.Append(
            inputs=inserts_fc,
            target=target_fc,
            schema_type="NO_TEST",
        )

    if not updates.empty:
        logger.info(f'Processing {len(updates)} updates')
        processUpdates(updates, target_fc, id_field)

    if not deletes.empty:
        logger.info(f'Processing {len(deletes)} deletes')
        delete_ids_string = ",".join(str(i) for i in deletes[id_field])        
        where_clause = f"id in ({delete_ids_string})"
        logger.info(where_clause)
        target_layer = arcpy.management.MakeFeatureLayer(
            target_fc, "target_layer", where_clause=where_clause
        )

        arcpy.management.DeleteRows(target_layer)
        arcpy.Delete_management(target_layer)

    logger.info("Finished applying changes.")


def processUpdates(changes_sdf, target_fc, id_field):
    """ 
    Applies updates from the source to the target.
    The source is a changeset with a __change__ field.
    The target is expected to have the same schema.
    """ 

    source_fc = changes_sdf.spatial.to_featureclass(os.path.join("memory", "updates"))

    source_desc = arcpy.da.Describe(source_fc)
    target_desc = arcpy.da.Describe(target_fc)

    source_fields = [field.name.lower() for field in source_desc.get("fields")]
    target_fields = [field.name.lower() for field in target_desc.get("fields")]

    # Exclude the GlobalID, OID and editor tracking fields
    exclude_fields = [
        source_desc.get("globalIDFieldName"), 
        source_desc.get("OIDFieldName"),
        source_desc.get("createdAtFieldName"),
        source_desc.get("creatorFieldName"),
        source_desc.get("editedAtFieldName"),
        source_desc.get("editorFieldName"),
        target_desc.get("globalIDFieldName"), 
        target_desc.get("OIDFieldName"),
        target_desc.get("createdAtFieldName"),
        target_desc.get("creatorFieldName"),
        target_desc.get("editedAtFieldName"),
        target_desc.get("editorFieldName"),
        ]

    source_fields = [f for f in source_fields if f not in exclude_fields]
    target_fields = [f for f in target_fields if f not in exclude_fields]

    # Identify date and text fields
    date_fields = [f.name.lower() for f in target_desc.get("fields") if f.type == 'Date']
    text_fields = [f.name.lower() for f in target_desc.get("fields") if f.type == 'String']

    # Store rows to be updated in a dictionary keyed by the record id
    updates_dict = {}
    with arcpy.da.SearchCursor(in_table=source_fc, field_names=source_fields) as cursor:
        for row in cursor:            
            record_id = row[source_fields.index(id_field)]            
            updates_dict[record_id] = row
    del cursor 

    # Use a single UpdateCursor to apply updates in bulk
    with arcpy.da.UpdateCursor(in_table=target_fc, field_names=target_fields) as updateCursor:
        for r in updateCursor:
            record_id = r[target_fields.index(id_field)]
            if record_id in updates_dict:
                logger.info(f"FOUND! {record_id}")
                row = updates_dict[record_id]
                for field in target_fields:
                    val = row[source_fields.index(field)]
                    if field in date_fields:
                        dt = datetime.strptime(val, '%Y-%m-%dT%H:%M:%SZ')
                        r[target_fields.index(field)] = dt
                    else:
                        r[target_fields.index(field)] = val
                updateCursor.updateRow(r)
    del updateCursor
    arcpy.management.Delete(source_fc)
    return

def main():

    nz_primary_parcels_layer_id = "50772"
    nz_suburbs_and_localities_layer_id = "113764"    

    # This is the Thames-Coromandel District Council crop feature
    crop_feature = linz.content.crop_layers.get(3036).get(10870)

    target_fgb = os.path.join(data_folder, 'nz-suburbs-and-localities.gdb')
    fc = 'NZ_Suburbs_and_Localities'
    target_fc = os.path.join(target_fgb, fc)

    itm = linz.content.get(nz_suburbs_and_localities_layer_id)
    id_field = itm.data.primary_key_fields[0]

    # This will delete any existing file geodatabase, then export, 
    # download and unzip a new one.
    export(itm, crop_feature.url, target_fgb)

    # This will fetch any changes since the last download.
    # Then apply the changes to the target file geodatabase.
    changes_sdf = get_changeset(itm, crop_feature)

    apply_changes(changes_sdf, target_fc, id_field=id_field)


if __name__ == "__main__":
    main()
