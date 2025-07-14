import httpx
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, api_key: str, api_url: str, service_url: str, wfs_url: str):
        self.api_key = api_key
        self.headers = {"Authorization": f"key {self.api_key}"}
        self.api_url = api_url
        self.service_url = service_url
        self.wfs_url = wfs_url

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

        logger.debug(f"Making kserver GET request to {url} with params {params}")
        try:
            response = httpx.get(url, headers=self.headers, params=params, timeout=30)
        except httpx.RequestError as exc:
            logger.error(f"An error occurred while requesting {exc.request.url!r}.")
            raise ServerError(str(exc)) from exc

        if response.status_code == 400:
            raise BadRequest(response.text)
        response.raise_for_status()
        return response.json()

    def post(self, url, data=None, json=None, **kwargs):
        """
        Makes a synchronous POST request to the specified URL with the provided data or JSON.
        Injects the API key into the request headers.

        Parameters:
            url (str): The URL to send the POST request to.
            data (dict, optional): Form data to include in the request. Defaults to None.
            json (dict, optional): JSON data to include in the request. Defaults to None.

        Returns:
            dict: The JSON-decoded response from the server.

        Raises:
            BadRequest: If the request fails with a 400 status code.
            ServerError: For other HTTP errors or request exceptions.
        """

        logger.debug(f"Making kserver POST request to {url} with data {data} and json {json}")
        try:
            response = httpx.post(url, headers=self.headers, data=data, json=json, **kwargs)
        except httpx.RequestError as exc:
            logger.error(f"An error occurred while requesting {exc.request.url!r}.")
            raise ServerError(str(exc)) from exc

        if response.status_code == 400:
            raise BadRequest(response.text)
        response.raise_for_status()
        return response.json()

