import httpx
import os
from datetime import datetime
from typing import Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    RetryError,
    retry_if_not_exception_type,
)
import logging
from .custom_errors import BadRequest, HTTPError, ServerError

logger = logging.getLogger(__name__)

# --- Configuration ---


DEFAULT_WFS_SERVICE = "WFS"
DEFAULT_WFS_VERSION = "2.0.0"
DEFAULT_WFS_REQUEST = "GetFeature"
DEFAULT_WFS_OUTPUT_FORMAT = "json"
DEFAULT_SRSNAME = "EPSG:2193"
MAX_PAGE_FETCHES = 50  # Maximum number of pages to fetch, to prevent infinite loops
DEFAULT_FEATURES_PER_PAGE = 10000


@retry(
    retry=retry_if_not_exception_type((HTTPError, BadRequest)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _fetch_single_page_data(url: str, headers: dict, params: dict, timeout=30) -> dict:
    """
    Fetches a single page of WFS data with retry logic for transient issues.

    Parameters:
        url (str): The WFS service endpoint URL.
        headers (dict): HTTP headers for the request (including API key).
        params (dict): Query parameters for the WFS request.
        timeout (int, optional): Timeout for the request in seconds. Default is 30.

    Returns:
        dict: The JSON response from the WFS service for the page.

    Raises:
        BadRequest: If a 400 Bad Request is returned from the WFS service.
        HTTPError: For other HTTP errors that should not be retried.
        httpx.RequestError: For other request issues that tenacity will handle.
    """
    try:
        logger.debug(f"Requesting WFS data. URL: {url}, Params: {params}")
        response = httpx.post(url, headers=headers, data=params, timeout=timeout)
        response.raise_for_status()
        json_data = response.json()
        logger.debug(
            f"Successfully fetched page. Status: {response.status_code}, Features: {len(json_data.get('features', []))}"
        )
        return json_data
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else None
        logger.warning(
            f"HTTP ## error for URL {url}: {status} - {getattr(e.response, 'text', '')}"
        )
        if status is not None and 400 <= status < 500:
            raise BadRequest(
                f"Bad request ({status}) for URL {url}: {getattr(e.response, 'text', '')}"
            ) from e
        raise  # Let tenacity retry for other HTTP errors
    except httpx.RequestError as e:
        logger.warning(f"Request failed for URL {url}: {e}")
        raise  # Reraise for tenacity to handle


def download_wfs_data(
    url: str,
    typeNames: str,
    api_key: str,
    srsName: str = DEFAULT_SRSNAME,
    cql_filter: str = None,
    bbox: str = None,
    out_fields: str | list[str] = None,
    result_record_count: int = None,
    page_count: int = DEFAULT_FEATURES_PER_PAGE,
    **other_wfs_params: Any,
) -> dict:
    """
    Downloads features from a WFS service, handling pagination and retries.

    Parameters:
        url (str): The base URL of the WFS service (e.g., "https://data.linz.govt.nz/services/wfs").
        typeNames (str): The typeNames for the desired layer (e.g., "layer-12345").
        api_key (str): API key.
        srsName (str, optional): Spatial Reference System name (e.g., "EPSG:2193"). Defaults to "EPSG:2193".
        cql_filter (str, optional): CQL filter to apply to the WFS request. Defaults to None.
        bbox (str, optional): Bounding box string to filter the request by extent. Defaults to None.
        out_fields (str, list of strings, optional): Attribute fields to include in the response. NOT IMPLEMENTED YET...
        result_record_count (int, optional): Maximum number of features to fetch.
        page_count (int, optional): Number of features per page request. Defaults to 2000.
        **other_wfs_params: Additional WFS parameters.

    Returns:
        dict: A GeoJSON FeatureCollection-like dictionary containing all fetched features.

    Raises:
        HTTPError: If the API key or typeNames is missing, or if data fetching fails after all retries.
        BadRequest: If a 400 Bad Request is returned from the WFS service.
    """

    if not api_key:
        raise HTTPError("API key must be provided.")
    if not typeNames:
        raise HTTPError("Typenames (i.e. layer id) must be provided.")

    headers = {
        "Authorization": f"key {api_key}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    all_features = []
    start_index = 0
    if result_record_count is not None and result_record_count < page_count:
        page_count = result_record_count
    crs_info = None
    total_features_service_reported = None

    result = None

    logger.debug(f"Starting WFS data download for typeNames: '{typeNames}'")

    wfs_request_params = {
        "service": DEFAULT_WFS_SERVICE,
        "version": DEFAULT_WFS_VERSION,
        "request": DEFAULT_WFS_REQUEST,
        "outputFormat": DEFAULT_WFS_OUTPUT_FORMAT,
        "typeNames": typeNames,
        "srsName": srsName,
        **{k: v for k, v in other_wfs_params.items()},
    }

    if cql_filter is not None:
        logger.debug(f"{cql_filter=}")
        wfs_request_params["cql_filter"] = cql_filter
    if bbox is not None:
        logger.debug(f"{bbox=}")
        wfs_request_params["bbox"] = bbox
    if out_fields is not None:
        if isinstance(out_fields, list):
            out_fields = ",".join(out_fields)
        out_fields = f"({out_fields})"
        logger.debug(f"{out_fields=}")
        wfs_request_params["PropertyName"] = out_fields

    request_datetime = datetime.utcnow()

    pages_fetched = 0
    while pages_fetched < MAX_PAGE_FETCHES:
        logger.debug(f"Pages fetched: {pages_fetched} of max: {MAX_PAGE_FETCHES}")
        pages_fetched += 1
        wfs_request_params["startIndex"] = start_index
        wfs_request_params["count"] = page_count

        logger.debug(f"{start_index=}, {page_count=}")

        try:
            page_data = _fetch_single_page_data(url, headers, wfs_request_params)
        except BadRequest as e:
            logger.error(f"### Bad request error: {e}")
            raise
        except RetryError as e:
            last_exception = e.last_attempt.exception() if e.last_attempt else e
            logger.error(
                f"All retries failed for '{typeNames}' at startIndex {start_index}. Last error: {last_exception}"
            )
            raise HTTPError(
                f"Failed to download WFS data for '{typeNames}' after multiple retries. Last error: {last_exception}"
            ) from last_exception
        except HTTPError:
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error for '{typeNames}' at startIndex {start_index}: {e}"
            )
            raise HTTPError(
                f"Failed to download WFS data for '{typeNames}' due to unexpected error: {e}"
            ) from e

        if not page_data or not isinstance(page_data, dict):
            logger.warning(
                f"Received empty or invalid data for '{typeNames}' at startIndex {start_index}. Assuming end of data."
            )
            break

        result = page_data if result is None else result
        features_on_page = page_data.get("features", [])
        if not features_on_page:
            logger.debug(
                f"No more features found for '{typeNames}' at startIndex {start_index}. Download likely complete."
            )
            break
        all_features.extend(features_on_page)
        logger.debug(
            f"Fetched {len(features_on_page)} features for '{typeNames}'. Total fetched so far: {len(all_features)}."
        )
        if len(features_on_page) < page_count:
            logger.debug(
                f"Last page fetched for '{typeNames}' (received {len(features_on_page)} features, requested up to {page_count})."
            )
            break
        if result_record_count is not None and len(all_features) >= result_record_count:
            logger.debug(
                f"Reached maximum count of {result_record_count} features for '{typeNames}'. Stopping download."
            )
            break

        start_index += page_count
        if (
            result_record_count is not None
            and result_record_count - len(all_features) < page_count
        ):
            page_count = result_record_count - len(all_features)

    result["features"] = all_features
    result["totalFeatures"] = len(all_features)
    result.pop("numberReturned", None)

    logger.debug(
        f"Finished WFS data download for '{typeNames}'. Total features retrieved: {len(all_features)}."
    )

    headers.pop('Authorization', None)
    wfs_request_params.pop('startIndex', None)
    wfs_request_params.pop('count', None)

    return {
        "request_url": url,
        "request_method": "POST",
        "request_time": request_datetime,
        "request_headers": headers,
        "request_params": wfs_request_params,
        "response": result
    }


