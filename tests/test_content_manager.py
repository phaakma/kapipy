import pytest
from unittest.mock import patch
from kapipy.gis import GISK
from kapipy.content_manager import ContentManager
from kapipy.data_classes import BaseItem

from sample_api_data import SEARCH_LAYER_JSON, LAYER_JSON

@pytest.fixture
def content_manager():
    # Replace with actual initialization as needed
    return ContentManager(None, None)

@patch("kapipy.content_manager.ContentManager._get_item_details")
@patch("kapipy.content_manager.ContentManager._search_by_id")
def test_get_item(mock_search_by_id, mock_get_item_details, content_manager):
    """
    Test that ContentManager.get returns the correct item when both _search_by_id and
    _get_item_details methods are patched to return sample API responses.
    Ensures that both API calls are mocked and no real network requests are made.
    """
    mock_search_by_id.return_value = SEARCH_LAYER_JSON
    mock_get_item_details.return_value = LAYER_JSON

    # Retrieve the item
    item = content_manager.get(50787)

    assert item.id == 50787
    assert item.title == "NZ Geodetic Marks"

def test_download_jobs(content_manager):

    assert isinstance(content_manager.jobs, list)
