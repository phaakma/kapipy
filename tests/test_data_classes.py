from datetime import datetime
import pytest
from dacite import from_dict, Config
from kapipy.data_classes import (
    CRS,
    FieldDef,
    ExportFormat,
    VectorItemData,
    Service,
    Version,
    ItemData,
    Geotag,
)
from sample_api_data import LAYER_JSON

# the API sometimes uses type as a property which is not ideal
safe_keys = {"type_": "type"}
field_config = Config(strict=False, convert_key=lambda k: safe_keys.get(k, k))


def test_crs_creation():
    """Test CRS dataclass creation and attribute access."""
    crs = from_dict(data_class=CRS, data=LAYER_JSON.get("data").get("crs"))
    assert crs.id == "EPSG:4167"
    assert crs.srid == 4167


def test_field_def_creation():
    """Test FieldDef dataclass creation and attribute access."""
    data = LAYER_JSON.get("data").get("fields")[0]

    obj = from_dict(data_class=FieldDef, data=data, config=field_config)
    assert obj.name == "id"
    assert obj.type_ == "integer"


def test_export_format_creation():
    """Test ExportFormat dataclass creation and attribute access."""
    data = LAYER_JSON.get("data").get("export_formats")[0]

    obj = from_dict(data_class=ExportFormat, data=data)
    assert obj.name == "Shapefile"
    assert obj.mimetype == "application/x-zipped-shp"


def test_vector_item_data_creation():
    """Test VectorItemData dataclass creation and attribute access."""

    data = LAYER_JSON.get("data")

    obj = from_dict(data_class=VectorItemData, data=data, config=field_config)
    assert isinstance(obj.crs, CRS)
    assert obj.crs.id == "EPSG:4167"
    assert obj.geometry_type == "point"
    assert isinstance(obj.extent, dict)

