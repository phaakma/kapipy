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

def test_crs_creation():
    """Test CRS dataclass creation and attribute access."""
    crs = from_dict(data_class=CRS, data=LAYER_JSON.get("data").get("crs"))
    assert crs.id == "EPSG:4167"
    assert crs.srid == 4167


def test_field_def_creation():
    """Test FieldDef dataclass creation and attribute access."""
    data = LAYER_JSON.get("data").get("fields")[0]

    obj = from_dict(data_class=FieldDef, data=data)
    assert obj.name == "id"
    assert obj.type == "integer"


def test_export_format_creation():
    """Test ExportFormat dataclass creation and attribute access."""
    data = LAYER_JSON.get("data").get("export_formats")[0]

    obj = from_dict(data_class=ExportFormat, data=data)
    assert obj.name == "Shapefile"
    assert obj.mimetype == "application/x-zipped-shp"


def test_vector_item_data_creation():
    """Test VectorItemData dataclass creation and attribute access."""

    data = LAYER_JSON.get("data")

    obj = from_dict(data_class=VectorItemData, data=data)
    assert isinstance(obj.crs, CRS)
    assert obj.crs.id == "EPSG:4167"
    assert obj.geometry_type == "point"
    assert isinstance(obj.extent, dict)

