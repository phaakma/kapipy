# Usage Guide

This guide walks you through the main ways to use the `kapipy` package to query and download data from the LINZ Data Service via Koordinates.

## Connecting to the LINZ Data Service

```python
from kapipy.gis import GIS
linz = GIS(name="linz", api_key="your-api-key")
```

## Get a reference to an item  

For this snippet to work, create a .env file in the project root folder and include a variable called 'LINZ_API_KEY'.  

```python
from dotenv import load_dotenv, find_dotenv
from kapipy.gis import GIS
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)
api_key = os.getenv('LINZ_API_KEY')

#create gis object
linz = GIS(name="linz", api_key="your-api-key")

#get item object
rail_station_layer_id = "50318" #rail station 175 points
itm = linz.content.get(rail_station_layer_id)
#print item title
print(itm.title)
```

## Query an item using WFS endpoint  

Get all data  
```python  
data = itm.query()
```

Get first 5 records. Could be any records as there doesn't appear to be a sort argument, so probably only useful for data exploration.  
```python
data = itm.query(count=5)
```

Data is returned as a geopandas GeoDataFrame, typed by the fields provided by the API.  
```python
print(data.dtypes())
print(data.head())
```

## Get a changeset using WFS endpoint  

Also returned as a GeoDataFrame.
```python
changeset = itm.get_changeset(from_time="2024-01-01T00:00:00Z")
print((f"Total records returned {itm.title}: {changeset.shape[0]}"))
```

## Generate an export  

```python
job = itm.export("geodatabase", crs="EPSG:2193",)
print(job.status)
```
Download the job data once it is ready. If this method is called before the job is complete, it will keep polling the status of the job until it is ready and then downloads it.  
```python
job.download(folder=r"c:/temp")
```

## Generate an export with extent geometry  

```python
waikato_polygon = {
        "coordinates": [
          [
            [
              174.30400216373914,
              -36.87399457472202
            ],
            [
              174.30400216373914,
              -38.83764306196984
            ],
            [
              176.83017911725346,
              -38.83764306196984
            ],
            [
              176.83017911725346,
              -36.87399457472202
            ],
            [
              174.30400216373914,
              -36.87399457472202
            ]
          ]
        ],
        "type": "Polygon"
      }

job = itm.export("geodatabase", crs="EPSG:2193", extent=waikato_polygon,)
print(job.status)
```

## Tests  

To run all tests:  

To run all tests with logging. Leave off the log parameter if not wanting logging.  
```bash
uv run -m pytest --log-cli-level=INFO
```  

To run a specific test, replace the relevant file name and test function.  
```bash
uv run -m pytest tests/test_simple.py::test_validate_layer_export_params --log-cli-level=INFO
```  