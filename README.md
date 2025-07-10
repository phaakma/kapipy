# kapipy
A python client for accessing and querying datasets from geospatial open data portals such as LINZ, Stats NZ and LRIS.

## Overview  
kapipy is a Python package that provides a python interface to the Koordinates geospatial content management system. It allows users to connect to a data portal, retrieve metadata, and query vector layers and tables. 

Github repository: [https://github.com/phaakma/kapipy](https://github.com/phaakma/kapipy)  

Documentation: [https://phaakma.github.io/kapipy/](https://phaakma.github.io/kapipy/)  

## Installation  

```bash
pip install kapipy
```

## Basic Usage  

* Import kapipy.  
* Create a GISK object, passing in an api key.  
* Get a reference to an item using {gis}.content.get({layer_id})
* Perform actions on the item.  

Basic example:  
```python
from kapipy.gis import GISK
linz = GISK(name="linz", api_key="my-linz-api-key")
rail_station_layer_id = "50318"
itm = linz.content.get(rail_station_layer_id)
data = itm.query()
data.df.head()
```

## Disclaimer  
Kapipy is provided as-is. The author has no affiliation with either Koordinates nor LINZ, Stats NZ or LRIS. As such, the underlying API's and services may change at any time without warning and break these modules.  

This project does not cover the full spectrum of the Koordinates API and probably never will. It focuses currently on basic workflows such as connecting using an api key, getting references to datasets and downloading them.  

Suggestions and bug reports can be made by submitting issues via the GitHub page.  
