from unittest.mock import patch, Mock
import pytest
from kapipy.gis import GISK
from kapipy.custom_errors import ServerError, BadRequest
from kapipy.content_manager import ContentManager
from kapipy.audit_manager import AuditManager

@pytest.fixture
def gisk():
    """Fixture providing a GISK instance with test configuration."""
    return GISK(url="https://data.linz.govt.nz/", api_key="test_key")


@pytest.fixture
def mock_response():
    """Fixture providing a mock response object."""
    mock = Mock()
    mock.status_code = 200
    return mock


def test_gisk_initialization():
    """Test GISK initialization with url provided."""
    gisk = GISK(url="https://data.linz.govt.nz/", api_key="test_key")
    assert gisk.url == "https://data.linz.govt.nz/"
    assert gisk._api_key == "test_key"


def test_gisk_linz_initialization():
    """Test GISK initialization with built in linz details."""
    gisk = GISK(name="linz", api_key="test_key")
    assert gisk.url == "https://data.linz.govt.nz/"
    assert gisk._api_key == "test_key"


def test_build_service_url(gisk):
    """Test building _service_url property."""
    url = gisk._service_url
    assert url == "https://data.linz.govt.nz/services/"


def test_build_api_url(gisk):
    """Test building _api_url property."""
    url = gisk._api_url
    assert url == "https://data.linz.govt.nz/services/api/v1.x/"

def test_build_wfs_url(gisk):
    """Test building _wfs_url property."""
    url = gisk._wfs_url
    assert url == "https://data.linz.govt.nz/services/wfs/"

def test_content_manager(gisk):
    """Test content manager."""
    assert(isinstance(gisk.content, ContentManager))

def test_audit_manager(gisk):
    """Test audit manager."""
    assert(isinstance(gisk.audit, AuditManager))


