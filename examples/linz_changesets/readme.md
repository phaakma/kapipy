# kapipy changesets example  

This is an example for setting up a basic workflow to download some LINZ data locally and keep it updated via the changesets. The example script takes command line parameters and requires set up of a configuration file. This script assumes use of ArcGIS where the target database is either a file or enterprise geodatabase.     

The changesets.py file has command line arguments:
- **--file** / **-f**  a required parameter of a configuration yaml file.  
- **--export** / **-e** or **--changeset** / **-c**  whether to generate a full export or query the changesets.  

## Configuration file  

YAML is a form of JSON, often used for configuration files. The layout is structured and easy to follow, and can include comments. A small helper function in the script combines the defaults section into each layer section.  

It is assumed that the config file is in the same directory as the changesets.py file.  

An example configuration yaml file for the changesets.py looks like the following.

```yaml
audit_folder: d:/audit/tcdc

defaults:  
  crop_layer_id: 3036
  crop_feature_id: 10870
  out_sr: 2193
  target_db: D:/data/LINZ/linz_tcdc.gdb

layers:
  - id: 50772
    target_fc: NZ_Primary_Parcels

  - id: 51681
    target_fc: NZ_Place_Names__NZGB_
    out_sr: 4326 #for some reason LINZ API doesn't want to export this as 2193
```  

The **audit_folder** is a root folder for the logs and a temporary location for downloaded data.  
The **defaults** are applied to each layer, but can be over-ridden at the layer level if desired.  
The **layers** is a list, requiring the layer id and the name of the target featureclass.  
The **target_db** is either a file geodatabase or sde connection file for an enterprise geodatabase. The target feature classes for each layer will end up in this database.  

The crop feature is a convenience thing from the LINZ API, where the ids in this example correspond to the district boundary for Thames-Coromandel District Council. Alternatively, in the script you could load in a polygon boundary from a local file and use that instead.   

## Keyring  

This script assumes that you have stored an API key using the Python keyring library. You would need to manually run the following Python command prior, using your API key.  

```python
keyring.set_password("kapipy", "linz", "YOUR-API-KEY")
```  

Otherwise, substitute your own method for storing and loading the API key.  

## Command line examples  

Run the following to export, download, unzip file geodatabases with the data and copy the data into your target.  

- If the target is a file geodatabase and it does not exist, it will be created.  
- If the target is an enterprise geodatabase and it does not exist, an error will be raised.  
- If the target feature classes do not exist, they will be created by the **--export** option.  
- If the target is an enterprise geodatabase, ensure the credentials for the connection are the appropriate ones to create the feature classes. Otherwise, create the feature classes manually, and ensure the credentials have permissions to delete and add features.  
- The script will enable editor tracking on the target feature classes if it is not already enabled.
- On subsequent runs of **--export**, the target feature classes will be truncated and new data fully appended again.  
- Subsequent runs of **--changeset** will apply the changes only.  
- The yaml file is assumed to be in the same directory as *changesets.py*.  
- Update the path to the desired python.exe and to *changesets.py* as specific to your environment.  

```bash
path/to/python.exe path/to/changesets.py --export --file config_tcdc.yaml
```

Subsequently, run the following to fetch changesets.  

```bash
path/to/python.exe path/to/changesets.py --changeset --file config_tcdc.yaml
```

## Scheduling  

Typically, you would run the full export manually, and then schedule the changeset to run after that.  
Alternatively, you could also schedule the full export, perhaps just on a longer interval. E.g. changesets once a week, and full every 3 months.  

There is an included PowerShell script that can be used to set up Windows Task Scheduler tasks: **run-changesets.ps1**. 

- In the **run-changesets.ps1** file, update the python path if necessary to point to the appropriate python environment.  
- Create a new task.  
- For the action, set the command to ```powershell.exe```  
- Use the following arguments, substituting the appropriate paths and parameters:  
```-ExecutionPolicy Bypass -File "D:\data\kapipy_downloads\run-changesets.ps1" -f config_filename.yaml -c```  
- Set the **start in** directory to be the directory where the **changesets.py** script is.  

