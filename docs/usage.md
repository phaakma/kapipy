# Usage Guide

This guide walks you through the main ways to use the `kapipy` package to query and download data from the LINZ Data Service via Koordinates.

## Installation Notes  
Kapipy is designed to use either GeoPandas or the ArcGIS API for Python, returning and reading data as either a GeoDataFrame or a Spatially Enabled DataFrame respectively.  Neither package is defined as a requirement of kapipy, as users may choose to use one over the other and may not want the other automatically installed.  

This means you need to manually install one of either **geopandas** or **arcgis** into your Python environment.

### ArcGIS  
 If you are an ArcGIS user, cloning the default conda environment from ArcGIS Pro or ArcGIS Server should be sufficient, and you just need to install kapipy. If you choose to start with a blank environment and do not intend to install arcpy, you may need to install the following:  
- pyproj  
- shapely  
- pyshp  

### Jupyter Notebooks  
If you are starting with a clean Python environment and want to use Jupyter Notebooks (e.g. inside Visual Studio Code), then manually install these packages:  
- ipykernel  
- ptyprocess  
- comm  

## Connecting to the various open data portals  

LINZ, Stats NZ and LRIS have built in names for convenience. Alternatively, pass in the base URL.  

```python
from kapipy.gis import GISK

linz = GISK(name="linz", api_key="your-linz-api-key")
statsnz = GISK(name='statsnz', api_key="your-stats-api-key")
lris = GISK(name='lris', api_key="your-lris-api-key")
```

Passing in a base url:  
```python
from kapipy.gis import GIS

linz = GISK(url="https://data.linz.govt.nz/", api_key="your-linz-api-key")
```

## Get a reference to an item  
The gis object has a property called **content** which is a ContentManager. This allows you to get a reference to an item using it's id.  

```python
from kapipy.gis import GISK

#create gis object
linz = GISK(name="linz", api_key="your-linz-api-key")

#get item object
rail_station_layer_id = "50318" #rail station 175 points
itm = linz.content.get(rail_station_layer_id)

print(itm)
```

## WFS queries  
Items with WFS endpoints can be queried using the **query** and, if the item supports changesets, **changeset** methods of the item .

For spatial items, it is recommended to specify a desired spatial reference via the **out_sr** parameter.  

### Query  
Get all data  
```python  
data = itm.query(out_sr=2193)
```

Get first 5 records.  

```python
data = itm.query(count=5, out_sr=2193)
```

Data is returned as a WFSResponse object. This has four attributes that can be used to access the data:  
- **.json**: this provides the raw json response returned from the WFS service.  
- **.df**: this provides a Pandas DataFrame of the data.  
- **.gdf**: if geopandas is installed, this will return a GeoDataFrame of the data.  
- **.sdf**: if arcgis is installed, this will return a Spatially Enabled DataFrame of the data.  

The attribute types of the dataframes are set according to the item's field list.  

```python
print(data.item.data.fields)
print(data.sdf.dtypes())
print(data.sdf.head())
```

Only fetch specified attribute fields. Remember to include the geometry field if you want that in the tabular data.  
```python
data = itm.query(
    out_fields=['id', 'geodetic_code', itm.data.geometry_field],
    out_sr = 2193)
print(f"Total records returned {itm.title}: {data.df.shape[0]}")
data.df.head()
```

### Changeset    

Also returned as a WFSResponse object with the same logic as the **query** method.  
The datetime parameters should be provided in ISO 8601 format.  

The **from_time** parameter is the time from which the changeset data will be generated.  
The **to_time** parameter is optional, and is the time up to which the changeset data will be generated. If this parameter is not provided then it defaults to now.  

```python
data = itm.changeset(from_time="2024-01-01T00:00:00Z", out_sr=2193)
print((f"Total records returned {itm.title}: {data.gdf.shape[0]}"))
```

### Query with a spatial filter  
The **filter_geometry** argument can be passed in as a gdf, sdf or geojson.  

It is recommended to only have one polygon geometry in the dataframe, and avoid complex geometries with lots of vertices. If there is more than one record in the dataframe, the records will be unioned into one geometry.  

The following example will only return features that intersect the **filter_geometry** object.  
```python
data = itm.changeset(
    from_time="2024-01-01T00:00:00Z", 
    out_sr=2193,
    filter_geometry=matamata_gdf
    )
print(f"Total records returned {itm.title}: {data.sdf.shape[0]}")
data.sdf.head()
```

## Export data    
Exporting data creates an asynchronous task on the data portal server that returns a job id. It is possible to create and manage individual downloads, or treat them collectively.  

Again, it is recommended to always specify the **out_sr**.  

### Export formats  
You can check the available export formats by using the **data.export_formats** property of an item.  

```python
print(itm.data.export_formats)
```  

### Single item export  

The item **export** method initiates the creation of the job on the server and a **JobResult** object is returned. Accessing the **status** property triggers a check with the server to get the latest **status** of the job.  
The **status** returned is a **JobStatus** object that has **state** and **progress** properties.  

```python
job = itm.export("geodatabase", out_sr=2193)
print(job.status)
```
Download the job data once it is ready. If this method is called before the job **state** is **'complete'**, it will poll the status of the job until it is ready and then downloads it.  
Calling the download method of a JobResult object gives you the flexibility of specifying a specific folder for that download.  
```python
job.download(folder=r"c:/temp")
```

### Generate an export using a spatial filter    

The **filter_geometry** argument can be passed in as a gdf, sdf or geojson.  

It is recommended to only have one polygon geometry in the dataframe, and avoid complex geometries with lots of vertices. If there is more than one record in the dataframe, the records will be unioned into one geometry.  

The following example will only return features that intersect the **filter_geometry** object.  

```python
# gdf
matamata_gdf = gpd.read_file("../examples/matamata_piako.shp")
# sdf
matamata_sdf = pd.DataFrame.spatial.from_featureclass("../examples/matamata_piako.shp")

job = itm.export("geodatabase", out_sr=2193, filter_geometry=matamata_sdf,)
```

### Export and download multiple items  

Whenever the **export** method of an item is called, the **JobResult** object is added to a list belonging to the ContentManager called **jobs**. 

The ContentManager has a download method as well. Calling this method and passing in a folder will download to that folder any jobs in the content manager's job list that are not already downloaded.  

```python
itm1.export("geodatabase", out_sr=2193, extent=matamata_sdf,)
itm2.export("geodatabase", out_sr=2193, extent=matamata_sdf,)

linz.content.download(folder=r"c:/temp")
```

The ContentManager also has an **output_folder** property. You can set this and it will be used as the default if no folder is provided.  
```python
linz.content.download_folder = r"c:/temp"

itm1.export("geodatabase", out_sr=2193, extent=matamata_sdf,)
itm2.export("geodatabase", out_sr=2193, extent=matamata_sdf,)

linz.content.download()
```

Alternatively, you can pass the content manager's **download** method a list of specific jobs and only those jobs will be downloaded.  
```python
job_1 = itm1.export("geodatabase", out_sr=2193, extent=matamata_sdf,)
job_2 = itm2.export("geodatabase", out_sr=2193, extent=matamata_sdf,)
job_3 = itm3.export("geodatabase", out_sr=2193, extent=matamata_sdf,)
job_4 = itm4.export("geodatabase", out_sr=2193, extent=matamata_sdf,)
job_5 = itm5.export("geodatabase", out_sr=2193, extent=matamata_sdf,)

# only jobs 1, 3 and 5 will be downloaded
linz.content.download([job_1, job_3, job_5])
```

Once a job is downloaded, it's "downloaded" attribute will be set to True, and any future calls to the ContentManager's **download** method will not download it.  
Use the 'force_all' parameter to force a download of all jobs in the list, regardless of their download status.  

```python
linz.content.download(force_all=True)
```

## Audit Manager  

The Audit Manager is optional. If enabled, it:  
- Records details of every query and export in a sqlite database.  
- Saves a copy of every query response as a file.  

```python
from kapipy.gis import GISK

# create gis object
linz = GISK(name="linz", api_key="your-linz-api-key")

# enable audit logging
linz.audit.enable_auditing(folder=r"c:/temp/audit")

# get item object
rail_station_layer_id = "50318" #rail station 175 points
itm = linz.content.get(rail_station_layer_id)

# Any query will now automatically populate a record in the audit database
data = itm.query()
```  

A copy of each response is saved as a json file. You can optionally disable this by passing in retain_data=False when enabling the audit manager.  

```python
linz.audit.enable_auditing(folder=r"c:/temp/audit", retain_data=False)
```  

The .export() method does not record the total_features count. This is because the data is returned as a zip file in any one of several formats, and to compute the counts would require the overhead of unzipping, handling reading in any format then computing the actual counts. Doing this, for example, on the NZ Parcels layer with ~2.7 million records is non-trivial and therefore not undertaken.  

The most recent record for a given id can be retrieved.  

```python
# returns record of the most recent query recorded.  
latest = linz.audit.get_latest_request_for_item(rail_station_layer_id)
```  