import pytest
from kapipy.vector_item import VectorItem
from kapipy.data_classes import FieldDef, Service

from dacite import from_dict, Config

# the API sometimes uses type as a property which is not ideal
safe_keys = {"type_": "type"}
field_config = Config(strict=False, convert_key=lambda k: safe_keys.get(k, k))

from sample_api_data import LAYER_JSON


@pytest.fixture
def sample_vectoritem_data():
    return from_dict(
        data_class=VectorItem, data=LAYER_JSON, config=field_config
    )


def test_initialization_valid(sample_vectoritem_data):
    item = sample_vectoritem_data
    assert item.id == 50787
    assert item.title == "NZ Geodetic Marks"
    assert item.data.crs.srid == 4167
    assert len(item.data.fields) == 13
    assert item.data.geometry_field == "shape"
    assert item.data.geometry_type == "point"
    assert item.data.feature_count == 132966


def test_initialization_missing_required():
    data = {
        "title": "Missing ID",
        "geometry": {"type": "Point", "coordinates": [0, 0]},
        "fields": [],
        "services": [],
        "crs": "EPSG:4326",
        "tags": [],
        "description": "",
    }
    from dacite.core import MissingValueError
    with pytest.raises(MissingValueError):
        item = from_dict(
                data_class=VectorItem, data=data, config=field_config
            )


def test_properties_and_attributes(sample_vectoritem_data):    
    assert isinstance(sample_vectoritem_data.data.fields, list)
    assert isinstance(sample_vectoritem_data.id, int)
    assert isinstance(sample_vectoritem_data.type_, str)
    assert sample_vectoritem_data.description == "This dataset provides information about the position, position accuracy, mark name, mark type, condition and unique four letter code for geodetic marks in terms of a New Zealand's official geodetic datum.\n\nThe dataset only contains marks that are within the New Zealand mainland and offshore islands. These positions have been generated using geodetic observations such as precise differential GPS or electronic distance and theodolite angles measurements. The positions are either 2D or 3D depending of the availability of this measurement data.\n\nThe source data is from Toitū Te Whenua Land Information New Zealand's (LINZ) Landonline system where it is used by Land Surveyors. This dataset is updated daily to reflect changes made in the Landonline.\n\n\nAccuracy\n============\nGeodetic marks with a coordinate order of 5 or less have been positioned in terms of NZGD2000. Lower order marks (order 6 and greater) are derived from cadastral surveys, lower accuracy measurement techniques or inaccurate historical datum transformations, and may be significantly less accurate.\n\nThe accuracy of NZGD2000 coordinates is described by a series of 'orders' classifications. Positions in terms of NZGD2000 are described by three-dimensional coordinates (latitude, longitude, ellipsoidal height). The accuracy of a survey mark is indicated by its Order. Orders are classifications based on the quality of the coordinate in relation to the datum and in relation to other surrounding marks. For more information [see](https://www.linz.govt.nz/guidance/geodetic-system/coordinate-systems-used-new-zealand/coordinate-and-height-accuracy/coordinate-orders)\n\nNote that the accuracy applies at the time the mark was last surveyed. Refer to the web geodetic database for historical information about mark coordinates.\n\nNote also that the existence of a mark in this dataset does not imply that there is currently a physical mark in the ground - the dataset includes destroyed or lost historical marks. The geodetic database provides more information on the mark status, valid at last time it was visited by LINZ or a maintenance contractor."


def test_method_functionality_to_geojson(sample_vectoritem_data):
    if hasattr(sample_vectoritem_data, "to_geojson"):
        geojson = sample_vectoritem_data.to_geojson()
        assert isinstance(geojson, dict)
        assert geojson["type"] == "Feature"
        assert geojson["geometry"]["type"] == "Point"
