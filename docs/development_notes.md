# Development Notes  

These are just general notes for the author to help remember design choices, rabbit holes and how they panned out, etc.  

## Installation  
When I run ```uv sync``` and ```uv pip install -e .``` on a new cloned copy, if I have a python environment activated already in my terminal it seems to do odd things sometimes. VS Code sometimes activates automatically depending on settings. And sometimes those settings vary between PowerShell and the standard Command Prompt. So I find it best to ensure I open a separate Command Prompt window with nothing activated, run those initial commands there, and then open up VS Code and any terminal windows. 

If installing from the whl file using UV, remember to add the package name.
```bash
uv pip install kapipy@path/to/packagefile.whl
```

If using the code directly rather than installing from PyPi (once it is uploaded to there), run the following to install the package locally in editable mode.
```bash
pip install -e .
```

## ArcGIS  
Recommend using the existing conda manager that comes installed with ArcGIS Pro or ArcGIS Server.  
If using arcgis module but not arcpy installed, need to install:
- pyproj
- shapely  
- pyshp
  
Optionally pip install dotenv if wanting to use that.  
If creating a blank conda environment (rather than cloning the default), and
wanting to use Jupyter notebooks, install:
- ipykernel
- ptyprocess
- comm

When converting geojson to sdf, I first tried using FeatureSet.from_geojson(geojson) but I
found that it assumes that the geojson is in wgs84 (which is the strict definition of geojson).
But in our case sometimes we often get the geojson returned already in NZTM/2193. So the from_geojson
ended up with incorrect spatial data. 
So I write a function that manually converts the geojson to an ArcGIS FeatureSet by passing in
the json, fields and wkid. Then I can convert that FeatureSet to an sdf.  

## Development using Jupyter Notebooks  
I got the following tips from Cookie Cutter Data Science.  
[Cookie Cutter Data Science](https://cookiecutter-data-science.drivendata.org/)  

Make the project a python package and install it locally. I was using UV, so I ran this command:
```
uv pip install -e .  
```  
Then, in my notebook, I included this cell first:  
```jupyter
%load_ext autoreload
%autoreload 2
```  
This allowed me to load my local python package like this:  
```jupyter  
from k_data_helpers import KServer  
```  
And it would hot reload any changes I made while developing.

## Koordinates API  

### Export API  
The export api doesn't appear to have an option for applying a cql_filter or any similar filter. Only extent. The extent appears to have to be a geojson geometry object. Note that this is just the geometry part, not the properties or collection. And it would have to be in WGS84. I might look at ways to handle passing in geometry objects of different types, such as from a geopandas geometry, and behind the scenes just handling that and converting to the corrrect format.  

Also, the export API treats the extent as a crop, and so features will be clipped. This may not be desired in all situations, e.g. clipping Property Parcels is not usually a good thing as someone may inadvertantly think that that is the actually parcel geometry, not realising it was clipped. The question is: how to handle this? Just warn the user in documentation and leave it up to them? Apply a buffer and do some post-processing? I'm inclined to do less, let the system supply as it is designed, and educate the user. This does imply the end user needs to do a little bit extra work but I would rather the user explicitly get the output and the module logic not get in the way.  

It does appear to allow generating an export of multiple items at once. E.g. you could request several layers in one zipped file geodatabase. Currently, this wrapper only supports one at a time, because I didn't realise at the time you could do multiple, so this would be a good enhancement for the future. The current approach is based off starting with an item and downloading that. So a multi item download would need to be initiated by a higher order class, perhaps the ContentManager?  

Need to think about how a user would most likely pass in the parameters for a multi download without constructing the whole list verbosely, but allowing them to do that if they wish.  

## Notes on design choices  

### OWSLib  
I investigated using the OWSLib python package to download the WFS data, but discovered that it doesn't support the CQL filter keyword option that the LINZ GeoServer provides. OGC filters were still an option, but seem very complex to construct and I believe most users would prefer to use the simpler CQL which is more similar to SQL. So I moved back to using a basic request to the WFS endpoint. The OWSLib package would provide more scope for expansion, but since the intent of this helper library is primarily focused on Koordinates and LINZ in particular, we can afford to be a little more opinionated on our approach, such as not having to support all the WFS versions.  
I'm not sure if the LINZ WFS endpoint is strictly equivalent with all other Koordinates WFS endpoints. So the implementation at the moment is coded to work with LINZ and might not work in other places.  


## Prompts  

Can you review the docstrings for all classes, methods and functions. Make sure they are accurate and reflect the correct Parameters and Return values. Ensure the syntax is correct, use the word Parameters instead of Args, and ensure the formatting is consistent for use with MkDocs and the Google format. Only provide docstrings that actually need to change. Provide each docstring in a separate section so I can copy and paste it. There is no need to provide the original for comparison. Provide an update for __str__ and __repr__ if necessary. Check that the type hints are accurate.

## Tests  
Tests are written using pytest.

To run all tests with logging. Leave off the log parameter if not wanting logging.  
```bash
uv run -m pytest --log-cli-level=INFO
```  

To run a specific test, replace the relevant file name and test function.  
```bash
uv run -m pytest tests/test_simple.py::test_validate_layer_export_params --log-cli-level=INFO
```  

There is currently very limited test coverage. Any live tests require a "LINZ_API_KEY" entry to exist in a .env file in the root project folder.  

To manually test the current build in a conda ArcGIS environment, need to manually install the current build into that environment.  
- Open the ArcGIS python command prompt.  
- Activate the desired environment.  
- Change directory into the local kapipy development folder.  
- If necessary, uninstall any existing install of kapipy.  
- Run the following pip command.  

```bash
pip install -e .
```  

## Build: Guidelines and Processes  

- Do all development work on the develop branch.  
- Push all commits to Github on develop.  
- When ready to create a release:
- - Increment the version in pyproject.toml and __version__.py  
- - Create a pull request in Github across to the main branch.
- - Create a release in main.  
- This will trigger Github action which will build and publish to PyPi.  

Pushing commits to develop branch in Github should trigger Github action to run pytest tests.  

Uv commands to manually build and publish.  
```bash
uv build --no-sources

# testpypi
uv publish --index testpypi

# or PyPi
uv publish --index pypi
```  

## Documentation  
Documentation uses MkDocs to generate and publish documentation website using Github Pages.  

Locally, run ```uv mkdocs build```  then ```uv mkdocs gh-deploy --clean```  

This could probably be set up as a Github action. If the gh-deploy was run from a Github workflow, need to figure out a way to use secrets.GITHUB_TOKEN. Or does it need authentication at all? Maybe it just works from there?    

## Enhancements  

Should there be a max days for the changesets? Or would that be up to the user to enforce? I'm leaning towards that being up to the user.  

Is there a way to obtain from the API ahead of time what the file geodatabase and feature class names will be?  






