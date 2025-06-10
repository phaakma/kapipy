# Frequently Asked Questions  

## Is this a comprehensive python wrapper for the Koordinates API?  
No. The focus here is primarily on extracting data easily, and it is unlikely to ever move beyond data exploration and export. The project is young, and even within the that narrow scope there is more can be done. At the time of writing, only Vector and Table datasets are implemented, as it felt like those are the core datasets that might require regular downloading.

## How do I get an API key?  
LINZ, Stats NZ and LRIS all have sign up pages. They should be a common Koordinates login, but you need to generate separate API keys from each site separately.  

## How do I report bugs or provide feedback?  
The recommended way is via the [GitHub issues page](https://github.com/phaakma/kapipy/issues).  .  

## Will it work with other Koordinates data portals?  
Probably? Maybe? Not sure. Try it and provide feedback if it doesn't! The focus during development is purely on LINZ, Stats NZ and LRIS, so those are the only ones that have been tested.  

## Can I download the entire NZ Primary Parcels layer using the query method?  
Never tried. And you probably shouldn't either.   
For context, the NZ Primary Parcels layer is approx 2.7M polygons. The query method uses the WFS endpoint, and would have to page hundreds of thousands of requests to download the data. That seems to be just asking for a network or connection error of some sort to cut you off halfway through.  
Use the **export** method to generate and download large datasets, and then use the **changeset** method to retrieve changes and then apply those.  
