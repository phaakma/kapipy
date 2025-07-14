# Example scripts  

## Keep a copy of NZ Primary Parcels for your district up to date  
A common workflow for NZ district councils is to download a copy of the NZ Primary Parcels for their district, and then keep it up to date with changesets.  
The approach here is split into two parts:
- A manual step to download the initial data and prepare it as the target for the next step.  
- An step that downloads and applies changesets, intended to be scheduled and run automatically.  

### Download data for district  

```python
from kapipy.gis import GISK  
import zipfile
import pandas as pd
from arcgis.features import GeoAccessor, GeoSeriesAccessor

# Connect to LINZ   
linz = GISK(name="linz", api_key=api_key)

# Load in extent shape file  
district_extent = r"c:/data/matamata_piako.shp"
district_extent_sdf = pd.DataFrame.spatial.from_featureclass(district_extent)

# Download the primary parcels data  
nz_primary_parcels_layer_id = "50772"  
itm = linz.content.get(nz_primary_parcels_layer_id)
job = itm.export(
    export_format="geodatabase",
    out_sr=2193,
    extent=district_extent_sdf,
    )
result = job.download(folder=r"c:/data/linz")

with zipfile.ZipFile(result.file_path, 'r') as zip_ref:
    zip_ref.extractall()
```

todo: in above example, how to delete features that don't intersect the extent? 
how to get the name of the feature class?
Can we use result.filename as the feature class name? 

todo: example of how to download and apply changeset.  

```python
#todo.....
```