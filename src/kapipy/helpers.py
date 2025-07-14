from .gis import has_arcgis, has_arcpy
import os
import logging

logger = logging.getLogger(__name__)

def apply_changes(changes_sdf, target_fc, id_field):

    if not has_arcgis:
        raise ImportError("The arcgis package is required.")
    if not has_arcpy:
        raise ImportError("The arcpy package is required.")

    import arcpy

    if changes_sdf.empty:
        logger.info(f"No changes were returned.")
        return

    if not arcpy.Exists(target_fc):
        logger.error(f"Target feature class does not exist. {target_fc}")
        return

    target_desc = arcpy.da.Describe(target_fc)

    inserts = changes_sdf[changes_sdf["__change__"] == "INSERT"].copy()
    updates = changes_sdf[changes_sdf["__change__"] == "UPDATE"].copy()
    deletes = changes_sdf[changes_sdf["__change__"] == "DELETE"].copy()

    if not inserts.empty:
        logger.info(f"Processing {len(inserts)} inserts.")
        inserts_fc = inserts.spatial.to_featureclass(os.path.join("memory", "inserts"))
        arcpy.management.Append(
            inputs=inserts_fc,
            target=target_fc,
            schema_type="NO_TEST",
        )
        arcpy.management.Delete(inserts_fc)

    if not updates.empty:
        logger.info(f"Processing {len(updates)} updates")
        #processUpdates(updates, target_fc, id_field)

        source_fc = updates.spatial.to_featureclass(os.path.join("memory", "updates"))

        source_desc = arcpy.da.Describe(source_fc)        

        source_fields = [field.name.lower() for field in source_desc.get("fields")]
        target_fields = [field.name.lower() for field in target_desc.get("fields")]

        # Exclude the GlobalID, OID and editor tracking fields
        exclude_fields = [
            source_desc.get("globalIDFieldName").lower(),
            source_desc.get("OIDFieldName").lower(),
            source_desc.get("createdAtFieldName").lower(),
            source_desc.get("creatorFieldName").lower(),
            source_desc.get("editedAtFieldName").lower(),
            source_desc.get("editorFieldName").lower(),
            target_desc.get("globalIDFieldName").lower(),
            target_desc.get("OIDFieldName").lower(),
            target_desc.get("createdAtFieldName").lower(),
            target_desc.get("creatorFieldName").lower(),
            target_desc.get("editedAtFieldName").lower(),
            target_desc.get("editorFieldName").lower(),
        ]
        
        source_fields = [f for f in source_fields if f.lower() not in exclude_fields]
        target_fields = [f for f in target_fields if f.lower() not in exclude_fields]

        # Identify date and text fields
        date_fields = [
            f.name.lower() for f in target_desc.get("fields") if f.type == "Date"
        ]
        text_fields = [
            f.name.lower() for f in target_desc.get("fields") if f.type == "String"
        ]

        # Store rows to be updated in a dictionary keyed by the record id
        updates_dict = {}
        with arcpy.da.SearchCursor(in_table=source_fc, field_names=source_fields) as cursor:
            for row in cursor:
                record_id = row[source_fields.index(id_field)]
                updates_dict[record_id] = row
        del cursor

        # Use a single UpdateCursor to apply updates in bulk
        with arcpy.da.UpdateCursor(
            in_table=target_fc, field_names=target_fields
        ) as updateCursor:
            for r in updateCursor:
                record_id = r[target_fields.index(id_field)]
                if record_id in updates_dict:                    
                    row = updates_dict[record_id]
                    for field in target_fields:
                        val = row[source_fields.index(field)]
                        if field in date_fields:
                            dt = datetime.strptime(val, "%Y-%m-%dT%H:%M:%SZ")
                            r[target_fields.index(field)] = dt
                        else:
                            r[target_fields.index(field)] = val
                    updateCursor.updateRow(r)
        del updateCursor
        arcpy.management.Delete(source_fc)

    if not deletes.empty:
        logger.info(f"Processing {len(deletes)} deletes")
        delete_ids_string = ",".join(str(i) for i in deletes[id_field])
        where_clause = f"id in ({delete_ids_string})"        
        target_layer = arcpy.management.MakeFeatureLayer(
            target_fc, "target_layer", where_clause=where_clause
        )

        arcpy.management.DeleteRows(target_layer)
        arcpy.Delete_management(target_layer)

    logger.info("Finished applying changes.")
