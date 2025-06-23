import os
import pytest

import logging

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception as e:
    print(e)


from kapipy.wfs_utils import download_wfs_data
from kapipy.export import validate_export_params

logger = logging.getLogger(__name__)

rail_station_layer_id = "50318"  # rail station 175 points
fences_layer_id = "50268"  # NZ Fence Centrelines
geodetic_marks_layer_id = "50787"  # NZ Geodetic Marks 132,966 point features
nz_walking_biking_tracks_layer_id = "52100"  # NZ Walking and Biking Tracks 29,187 polyline features
suburb_locality_table_id = "113761"  # Suburb Locality - Population 3190 records

DEFAULT_API_VERSION = "v1.x"

def test_download_linz_wfs_data_live(id: str = rail_station_layer_id):
    # Load environment variables from .env file    
    api_key = os.getenv("LINZ_API_KEY")
    assert api_key, "LINZ_API_KEY must be set in your .env file"

    url = "https://data.linz.govt.nz/services/wfs"
    srsName = "EPSG:2193"
    typeNames = f"layer-{rail_station_layer_id}"
    query_result = download_wfs_data(
        url=url, typeNames=typeNames, api_key=api_key, srsName=srsName
    ) 
    assert isinstance(query_result, dict), "Result should be a dictionary"
    response = query_result.get("response")
    features = response.get("features")
    assert isinstance(features, list)
    logger.info(f"Number of features downloaded: {len(response)}")
    # log all response properties except features
    logger.debug("Result properties::::::::::::::::::")
    for key, value in response.items():
        if key != "features":
            logger.debug(f"{key}: {value}")
    assert len(features) > 0, "Should return at least one feature"

def test_validate_layer_export_params(layer_id:str = rail_station_layer_id, api_version=DEFAULT_API_VERSION):
    api_key = os.getenv("LINZ_API_KEY")
    assert api_key, "LINZ_API_KEY must be set in your .env file"
    api_url = f"https://data.linz.govt.nz/services/api/{DEFAULT_API_VERSION}/"
    crs = "EPSG:2193"
    export_format = "applicaton/x-ogc-filegdb"
    data_type = "layer" 
    kind = "vector"  
    
    result = validate_export_params(
        api_url=api_url, api_key=api_key, id=layer_id, data_type=data_type, kind=kind, export_format=export_format, crs=crs
    ) 
    assert isinstance(result, bool), "Result should be a boolean"
    assert result == True, "Download should be valid"