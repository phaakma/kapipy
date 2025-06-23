# How this came about    

In New Zealand, where I am based, we are extremely lucky to have a wide range of open geospatial data available to us. One main source of this data is LINZ who provide an [open data website](https://data.linz.govt.nz/) with a wide range of data, including, for example, the cadastral datasets. Their website has a great UI for exploring and exporting data, as well as instructions for loading web services directly into desktop applications.  

I work a lot with local councils and other organisations wanting to use data from LINZ within ETL processes using python. Over the years, I have seen (and written!) various implementations of python scripts that query the LINZ data API's and download data. Usually these are some variation of sending requests to the WFS endpoint. A common use case is to download changeset data to keep local data up to date. The local data is then mashed up with internal datasets, such as rating information, to create various derived outputs.  

My role as a GIS Advisor is primarily within the ArcGIS eco-system, and as such I work a lot with the **ArcGIS API for Python**. This is a comprehensive python package provided by Esri to interact with the ArcGIS data portals: **ArcGIS Online** and **ArcGIS Enterprise**.  

I wrote and re-wrote several LINZ export helper scripts, and eventually I realised that I wanted to provide a familiar experience for extracting data from LINZ, with similarities to how the ArcGIS API for Python package allows to browse ArcGIS portal content.  

The general approach is:  
- Get a reference to a portal.  
- Get a reference to a content item from that portal.  
- Perform actions on that content.  

To me, this feels like a natural way to interact with a data portal. Kapipy wraps the Koordinates export API to provide the data as a zip file download, and the WFS API to return either a geopandas GeoDataFrame or an ArcGIS Spatially Enabled DataFrame. This makes it useful to all users, but extra convenient for ArcGIS users who may already be using sdf inside scripts. In fact, I find myself using kapipy within Jupyter and ArcGIS Notebooks as I can now bring in and display data layers from both LINZ and ArcGIS portals using a similar approach.   

As a bonus for me, this was the first time I had attempted building a python package and publishing to PyPi. Constructing a package like this is a great way to learn, as it forces you to think about software architecture. Already I have re-organised the modules and components several times!

For example, after the AI overlords helped me implement a JobResult class, I initially kept a jobs list attribute with the item class and added the job object to that list. I thought that would enable the user to retrospectively review and redownload prior jobs. But then I changed my mind. How often would a user create multiple download jobs for the same item within the same run of a script? There seemed little utility for the job list. Then it occurred to me that keeping a more global jobs list with the ContentManager might be more useful. If the ContentManager controlled the exports and kept a list of them, I could envisage a workflow where a script generated export requests for several items, then one call to the ContentManager **download** method could download them all to a folder in one go.  

Your use cases may differ. Feel free to contribute ideas, feedback and code via the [GitHub repo](https://github.com/phaakma/kapipy/issues).  



```
*|********
*|*/******
*|/**|\***
*|\**|*\**
*|*\*|*/**
*****|/***
*****|****
*****|****
```
