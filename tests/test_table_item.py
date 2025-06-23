import pytest
from kapipy.table_item import TableItem
from kapipy.data_classes import FieldDef, Service

from dacite import from_dict, Config

# the API sometimes uses type as a property which is not ideal
safe_keys = {"type_": "type"}
field_config = Config(strict=False, convert_key=lambda k: safe_keys.get(k, k))

from sample_api_data import TABLE_JSON

@pytest.fixture
def sample_table_item_data():
    return from_dict(
        data_class=TableItem, data=TABLE_JSON, config=field_config
    )


def test_initialization_valid(sample_table_item_data):
    item = sample_table_item_data
    assert item.id == 113761
    assert item.title == "Suburb Locality - Population"
    assert len(item.data.fields) == 3
    assert item.data.feature_count == 3190


def test_initialization_missing_required():
    data = {
        "title": "Missing ID",
        "fields": [],
        "services": [],
        "tags": [],
        "description": "",
    }
    from dacite.core import MissingValueError
    with pytest.raises(MissingValueError):
        item = from_dict(
                data_class=TableItem, data=data, config=field_config
            )


def test_properties_and_attributes(sample_table_item_data):    
    assert isinstance(sample_table_item_data.data.fields, list)
    assert isinstance(sample_table_item_data.id, int)
    assert isinstance(sample_table_item_data.type_, str)
    
