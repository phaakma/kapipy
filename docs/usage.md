# Usage Guide

This guide walks you through the main ways to use the `kapipy` package to query and download data from the LINZ Data Service via Koordinates.

## Installation Notes  
Kapipy is designed to use either GeoPandas or the ArcGIS API for Python, returning and reading data as either a GeoDataFrame or a Spatially Enabled DataFrame respectively.  Neither package is defined as a requirement of kapipy, as users may choose to use one over the other and may not want the other automatically installed.  

This means you need to manually instally one of either **geopandas** or **arcgis** into your Python environment.

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

```python
from kapipy.gis import GIS

linz = GIS(name="linz", api_key="your-linz-api-key")
statsnz = GIS(name='statsnz', api_key="your-stats-api-key")
lris = GIS(name='lris', api_key="your-lris-api-key")
```

## Get a reference to an item  


```python
from kapipy.gis import GIS

#create gis object
linz = GIS(name="linz", api_key="your-linz-api-key")

#get item object
rail_station_layer_id = "50318" #rail station 175 points
itm = linz.content.get(rail_station_layer_id)

print(itm)
```

## Query an item using WFS endpoint  

Get all data  
```python  
data = itm.query()
```

Get first 5 records.  

```python
data = itm.query(count=5)
```

Data is returned as either a geopandas GeoDataFrame or an ArcGIS Spatially Enabled DataFrame, typed by the fields provided by the API.  
```python
print(data.dtypes())
print(data.head())
```

## Get a changeset using WFS endpoint  

Also returned as a DataFrame.
```python
changeset = itm.get_changeset(from_time="2024-01-01T00:00:00Z", wkid=2193)
print((f"Total records returned {itm.title}: {changeset.shape[0]}"))
```

## Generate an export  

It is recommended to always specify the wkid.  

```python
job = itm.export("geodatabase", wkid=2193)
print(job.status)
```
Download the job data once it is ready. If this method is called before the job is complete, it will keep polling the status of the job until it is ready and then downloads it.  
```python
job.download(folder=r"c:/temp")
```

## Generate an export with extent geometry  

The *extent* argument can be passed in as a GeoDataFrame or a Spatially Enabled DataFrame.  

```python
waikato_polygon = gpd.read_file('../examples/waikato.json')
matamata_gdf = gpd.read_file("../examples/matamata_piako.shp")

job = itm.export("geodatabase", wkid=2193, extent=waikato_polygon,)
print(job.status)
```
