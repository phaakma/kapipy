# Kapipy changesets example  

This is an example for setting up a basic workflow to download some LINZ data locally and keep it updated via the changesets. The example script takes command line parameters and requires set up of a configuration file. This script assumes use of ArcGIS where the target database is either a file or enterprise geodatabase.     

The changesets.py file has command line arguments:
- **--file** / **-f**  a required parameter of a configuration yaml file.  
- **--all** / **-a** or **--changeset** / **-c**  whether to query all data or query for changesets.  

## Configuration file  

YAML is a form of JSON, often used for configuration files. The layout is structured and easy to follow, and can include comments. A small helper function in the script combines the defaults section into each layer section.  

It is assumed that the config file is in the same directory as the changesets.py file.  

An example configuration yaml file for the changesets.py looks like the following.

```yaml
audit_folder: c:/temp/audit/tcdc

authentication:
  section: linz 
  username: kapipy_example

defaults:  
  crop_layer_id: 3036
  crop_feature_id: 10870
  out_sr: 2193
  target_db: C:/temp/data/LINZ/linz_tcdc.gdb

layers:
  - id: 50772
    target_fc: NZ_Primary_Parcels

  - id: 51681
    target_fc: NZ_Place_Names__NZGB_
    out_sr: 4326 #for some reason LINZ API doesn't want to export this as 2193
```  

The **audit_folder** is a root folder for the logs and the AuditManager sqlite database.  
The **defaults** are applied to each layer, but can be over-ridden at the layer level if desired.  
The **layers** is a list, requiring the layer id and the name of the target featureclass along with any overrides.  
The **target_db** is either a file geodatabase or sde connection file for an enterprise geodatabase. The target feature classes for each layer will end up in this database.  
See below regarding **authentication**.  

The crop feature is a convenience thing from the LINZ API, where the ids in this example correspond to the district boundary for Thames-Coromandel District Council. Alternatively, in the script you could load in a polygon boundary from a local file and use that instead.   

## Authentication and Keyring  

This script assumes that you have stored an API key using the Python keyring library. You would need to manually run the following Python command prior. Use your own details and API key.  

```python
keyring.set_password("linz", "kapipy_example", "YOUR-API-KEY")
```  

Otherwise, substitute your own method for storing and loading the API key.  

## Command line examples  

The **--changeset** command line option tells the query method to check the AuditManager database for the last time each layer was queried. If never, then all records will be retrieved. Otherwise, the last query date will be used to retrieve just changes since then.  

The **--all** command line option can be used to force the query method to pull down all records. This is useful if you suspect drift in your dataset and want a full reset.  

Run the following to query and copy the data into your target.  

- If the target is a file geodatabase and it does not exist, it will be created.  
- If the target is an enterprise geodatabase and it does not exist, an error will be raised.  
- If the target feature classes do not exist, they will be created.  
- If the target is an enterprise geodatabase, ensure the credentials for the connection are the appropriate ones to create the feature classes. Otherwise, create the feature classes manually, and ensure the credentials have permissions to delete and add features.  
- If all records are downloaded, the target feature class is over-written.  
- The script will enable editor tracking on the target feature classes if it is not already enabled.
- Subsequent runs of **--changeset** will apply the changes only.  
- The yaml file is assumed to be in the same directory as *changesets.py*.  
- Update the path to the desired python.exe and to *changesets.py* as specific to your environment.  

```bash
path/to/python.exe path/to/changesets.py --changeset --file config_tcdc.yaml
```

Or, to force retrieving all records, run the following.  

```bash
path/to/python.exe path/to/changesets.py --all --file config_tcdc.yaml
```

## Scheduling  

Typically, you would schedule the command using the **--changeset** option. It will seed the target with all records initially, and then fetch changesets thereafter. You could then run **--all** manually as required.  

Alternatively, you could also schedule the query for all features, perhaps just on a longer interval. E.g. changesets once a week, and all records every 3 months.  

There is an included PowerShell script that can be used to set up Windows Task Scheduler tasks: **run-changesets.ps1**. 

- In the **run-changesets.ps1** file, update the python path if necessary to point to the appropriate python environment.  
- Create a new task.  
- For the action, set the command to ```powershell.exe```  
- Use the following arguments, substituting the appropriate paths and parameters:  
```-ExecutionPolicy Bypass -File "C:\kapipy\run-changesets.ps1" -f config_filename.yaml -c```  
- Set the **start in** directory to be the directory where the **changesets.py** script is.  

