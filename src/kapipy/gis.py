# gis.py
import os
from urllib.parse import urljoin
import logging
import importlib.util
from .custom_errors import ServerError, BadRequest
import httpx
from .session_manager import SessionManager

logger = logging.getLogger(__name__)

PORTAL_DETAILS = {
    "linz": {
        "name": "LINZ",
        "url": "https://data.linz.govt.nz/",
    },
    "statsnz": {"name": "Stats NZ", "url": "https://datafinder.stats.govt.nz/"},
    "lris": {
        "name": "LRIS",
        "url": "https://lris.scinfo.org.nz/",
    },
}
DEFAULT_API_VERSION = "v1.x"
SERVICES_PATH = "services/"
API_PATH = "api/"
WFS_PATH = "wfs/"

has_arcgis = importlib.util.find_spec("arcgis") is not None
has_geopandas = importlib.util.find_spec("geopandas") is not None
has_arcpy = importlib.util.find_spec("arcpy") is not None

logger.debug(f'{has_arcgis=}')
logger.debug(f'{has_geopandas=}')
logger.debug(f'{has_arcpy=}')


class GISK:
    """
    Client for connecting to a Koordinates server.

    Provides methods for authenticating, accessing content, and making HTTP requests to the Koordinates API.
    Used as the main entry point for interacting with Koordinates-hosted data.

    Attributes:
        name (str): The name of the Koordinates portal.  
            If this is provided, the url is ignored.  
        url (str): The base URL of the Koordinates server.
        _api_version (str): The API version to use.
        _content_manager (ContentManager or None): Cached ContentManager instance.
        _api_key (str): The API key for authenticating requests.
    """

    def __init__(
        self,
        name=None,
        url=None,
        api_key=None,
        api_version=DEFAULT_API_VERSION,
    ) -> None:
        """
        Initializes the GISK instance with the base URL, API version, and API key.

        Parameters:
            name (str, optional): The name of the Koordinates portal (e.g., 'linz'). If provided, overrides url.
            url (str, optional): The base URL of the Koordinates server. Used if name is not provided.
            api_key (str): The API key for authenticating with the Koordinates server.
            api_version (str, optional): The API version to use. Defaults to 'v1.x'.

        Raises:
            ValueError: If the portal name is not recognized or if api_key is not provided.
        """

        if name and PORTAL_DETAILS.get(name.lower(), None) is None:
            raise ValueError("Supplied portal name is not included in default list.")
        if name:
            self.name = PORTAL_DETAILS.get(name.lower()).get("name")
            self.url = PORTAL_DETAILS.get(name.lower()).get("url")
        else:
            self.name = "Custom"
            self.url = url
        self.url = (
            self.url if self.url.endswith("/") else f"{self.url}/"
        )  # ensure trailing slash
        self._api_version = api_version
        self._content_manager = None
        self._audit_manager = None
        self._api_key = api_key
        if not self._api_key:
            raise ValueError("API key must be provided.")
        self.session = SessionManager(
            api_key=self._api_key, 
            api_url=self._api_url, 
            service_url=self._service_url,
            wfs_url=self._wfs_url
            )
        logger.debug(f"GISK initialized with URL: {self.url}")
        
    @property
    def _service_url(self) -> str:
        """
        Returns the service URL for the Koordinates server.

        Returns:
            str: The full service URL, ending with a slash.
        """
        url = f"{self.url}{SERVICES_PATH}"
        return url if url.endswith("/") else f"{url}/"

    @property
    def _api_url(self) -> str:
        """
        Returns the API URL for the Koordinates server.

        Returns:
            str: The full API URL, ending with a slash.
        """
        url = f"{self._service_url}{API_PATH}{self._api_version}/"
        return url if url.endswith("/") else f"{url}/"

    @property
    def _wfs_url(self) -> str:
        """
        Returns the WFS URL for the Koordinates server.

        Returns:
            str: The full WFS URL, ending with a slash.
        """

        url = f"{self._service_url}{WFS_PATH}"
        return url if url.endswith("/") else f"{url}/"

    @property
    def content(self) -> "ContentManager":
        """
        Returns the ContentManager instance for this server.

        Returns:
            ContentManager: The content manager associated with this server.
        """

        if self._content_manager is None:
            from .content_manager import ContentManager
            self._content_manager = ContentManager(self.session, self.audit)
        return self._content_manager

    @property
    def audit(self) -> "AuditManager":
        """
        Returns the AuditManager instance for this GISK.

        Returns:
            AuditManager: The audit manager associated with this GISK.
        """

        if self._audit_manager is None:
            from .audit_manager import AuditManager
            self._audit_manager = AuditManager()
        return self._audit_manager

    def get(self, url: str, params: dict = None) -> dict:
        """
        Makes a synchronous GET request to the specified URL with the provided parameters.
        Injects the API key into the request headers.

        Parameters:
            url (str): The URL to send the GET request to.
            params (dict, optional): Query parameters to include in the request. Defaults to None.

        Returns:
            dict: The JSON-decoded response from the server.

        Raises:
            BadRequest: If the request fails with a 400 status code.
            ServerError: For other HTTP errors or request exceptions.
        """

        headers = {"Authorization": f"key {self._api_key}"}
        logger.debug(f"Making kserver GET request to {url} with params {params}")
        try:
            response = httpx.get(url, headers=headers, params=params, timeout=30)
        except httpx.RequestError as exc:
            logger.error(f"An error occurred while requesting {exc.request.url!r}.")
            raise ServerError(str(exc)) from exc

        if response.status_code == 400:
            raise BadRequest(response.text)
        response.raise_for_status()
        return response.json()

    def reset(self) -> None:
        """
        Resets the GISK instance. 
        This is useful if the API key
        or other configurations change.

        Returns:
            None
        """

        self._content_manager = None
        logger.info("GISK instance reset.")

    def __repr__(self) -> str:
        """
        Returns an unambiguous string representation of the GISK instance.

        Returns:
            str: String representation of the GISK instance.
        """
        return (
            f"GISK(name={self.name!r}, url={self.url!r}, api_key={'***' if self._api_key else None}, "
            f"api_version={self._api_version!r})"
        )

    def __str__(self) -> str:
        """
        Returns a user-friendly string representation of the GISK instance.

        Returns:
            str: User-friendly string representation.
        """
        return f"GISK: {self.name} at {self.url} (API {self._api_version})"
