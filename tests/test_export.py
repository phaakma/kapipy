import pytest
import httpx
from unittest.mock import patch, MagicMock
from datetime import datetime

from kapipy.export import validate_export_params, request_export
from kapipy.custom_errors import ExportError


@pytest.fixture
def sample_api_args():
    return dict(
        api_url="https://example.com/api/",
        api_key="TEST_KEY",
        id="123",
        data_type="layer",
        kind="shp",
        export_format="zip",
    )


@pytest.fixture
def sample_geometry():
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [175.0, -37.0],
                [176.0, -37.0],
                [176.0, -38.0],
                [175.0, -38.0],
                [175.0, -37.0],
            ]
        ],
    }


# ------------------------------------------------------------------------------
# validate_export_params
# ------------------------------------------------------------------------------

@patch("kapipy.export.httpx.post")
def test_validate_export_params_success(mock_post, sample_api_args, sample_geometry):
    """Should return True when validation is successful."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"items": [{"is_valid": True}]}
    mock_resp.raise_for_status.return_value = None
    mock_post.return_value = mock_resp

    result = validate_export_params(
        **sample_api_args,
        crs="EPSG:4326",
        filter_geometry=sample_geometry
    )

    assert result is True
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert kwargs["json"]["extent"] == sample_geometry
    assert kwargs["headers"]["Authorization"].startswith("key ")


@patch("kapipy.export.httpx.post")
def test_validate_export_params_invalid(mock_post, sample_api_args):
    """Should raise ValueError when validation response marks an item invalid."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"items": [{"is_valid": False, "invalid_reasons": ["bad"]}]}
    mock_resp.raise_for_status.return_value = None
    mock_post.return_value = mock_resp

    with pytest.raises(ValueError, match="An error occurred"):
        validate_export_params(**sample_api_args)


@patch("kapipy.export.httpx.post")
def test_validate_export_params_json_parse_error(mock_post, sample_api_args):
    """Should raise ValueError if response JSON parsing fails."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("not valid json")
    mock_resp.raise_for_status.return_value = None
    mock_post.return_value = mock_resp

    with pytest.raises(ValueError, match="Error parsing JSON"):
        validate_export_params(**sample_api_args)


@patch("kapipy.export.httpx.post")
def test_validate_export_params_http_status_error_4xx(mock_post, sample_api_args):
    """Should raise ValueError when a 4xx HTTP error occurs."""
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad request"
    err = httpx.HTTPStatusError("Bad request", request=None, response=mock_resp)
    mock_post.side_effect = err

    with pytest.raises(ValueError, match="Bad request"):
        validate_export_params(**sample_api_args)


@patch("kapipy.export.httpx.post")
def test_validate_export_params_http_status_error_5xx(mock_post, sample_api_args):
    """Should propagate 5xx HTTP errors."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    err = httpx.HTTPStatusError("Server error", request=None, response=mock_resp)
    mock_post.side_effect = err

    with pytest.raises(httpx.HTTPStatusError):
        validate_export_params(**sample_api_args)


def test_validate_export_params_invalid_data_type(sample_api_args):
    """Should raise ValueError when data_type is unsupported."""
    sample_api_args["data_type"] = "raster"
    with pytest.raises(ValueError, match="Unsupported or not implemented data type"):
        validate_export_params(**sample_api_args)


# ------------------------------------------------------------------------------
# request_export
# ------------------------------------------------------------------------------

@patch("kapipy.export.httpx.post")
def test_request_export_success(mock_post, sample_api_args):
    """Should return a well-formed dict when export request succeeds."""
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"id": 999, "state": "processing"}
    mock_resp.raise_for_status.return_value = None
    mock_post.return_value = mock_resp

    result = request_export(**sample_api_args, crs="EPSG:4326")

    assert isinstance(result, dict)
    assert result["request_method"] == "POST"
    assert result["response"]["id"] == 999
    assert "request_time" in result
    assert isinstance(result["request_time"], datetime)
    mock_post.assert_called_once()


@patch("kapipy.export.httpx.post")
def test_request_export_json_parse_error(mock_post, sample_api_args):
    """Should raise ExportError if response JSON parsing fails."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("invalid json")
    mock_resp.raise_for_status.return_value = None
    mock_post.return_value = mock_resp

    with pytest.raises(ExportError, match="Error parsing JSON"):
        request_export(**sample_api_args)


@patch("kapipy.export.httpx.post")
def test_request_export_http_error(mock_post, sample_api_args):
    """Should raise ExportError on HTTPStatusError."""
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    err = httpx.HTTPStatusError("Server error", request=None, response=mock_resp)
    mock_post.side_effect = err

    with pytest.raises(ExportError, match="Failed export request"):
        request_export(**sample_api_args)


def test_request_export_invalid_data_type(sample_api_args):
    """Should raise ValueError when data_type is unsupported."""
    sample_api_args["data_type"] = "raster"
    with pytest.raises(ValueError, match="Unsupported or not implemented data type"):
        request_export(**sample_api_args)
