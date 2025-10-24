import httpx
import os
import tempfile
import json
import logging
from datetime import datetime
from typing import Any, Literal
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_random,
    RetryError,
    retry_if_not_exception_type,
    retry_if_exception_type,
)

from .custom_errors import BadRequest, HTTPError, ServerError

logger = logging.getLogger(__name__)

# --- Configuration ---
DEFAULT_WFS_SERVICE = "WFS"
DEFAULT_WFS_VERSION = "2.0.0"
DEFAULT_WFS_REQUEST = "GetFeature"
DEFAULT_WFS_OUTPUT_FORMAT = "json"
DEFAULT_SRSNAME = "EPSG:2193"
MAX_PAGE_FETCHES = 1000
DEFAULT_FEATURES_PER_PAGE = 10000

_http_client = httpx.Client(
    timeout=httpx.Timeout(connect=15, read=90, write=30, pool=10)
)


def _get_kapipy_temp_file(suffix=".geojson", prefix="wfs_") -> str:
    """
    Returns a path to a unique temp file inside a 'kapipy' subdirectory
    of the system temp directory. The file is not opened, only created securely.
    """
    temp_root = tempfile.gettempdir()
    kapipy_dir = os.path.join(temp_root, "kapipy")

    # Ensure directory exists (safe to call even if it already exists)
    os.makedirs(kapipy_dir, exist_ok=True)

    # Create a unique temporary file path
    fd, temp_file_path = tempfile.mkstemp(
        dir=kapipy_dir, prefix=prefix, suffix=suffix, text=True
    )
    os.close(fd)  # We only need the path; we'll reopen later

    return temp_file_path


# --- Internal helper to fetch a single page ---
@retry(
    retry=(
        retry_if_exception_type(httpx.RequestError)
        | retry_if_exception_type(httpx.ReadTimeout)
    ),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10) + wait_random(0, 3),
    reraise=True,
)
def _fetch_single_page_data(url: str, headers: dict, params: dict, timeout=30) -> dict:
    try:
        response = _http_client.post(url, headers=headers, data=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response else None
        if status and 400 <= status < 500:
            raise BadRequest(
                f"Bad request ({status}): {getattr(e.response, 'text', '')}"
            )
        raise
    except httpx.RequestError as e:
        logger.warning(f"Request failed for URL {url}: {e}")
        raise


# --- Helper for building WFS params ---
def _build_wfs_params(
    typeNames: str,
    srsName: str,
    cql_filter: str | None,
    bbox: str | None,
    out_fields: str | list[str] | None,
    **other_wfs_params,
):
    params = {
        "service": DEFAULT_WFS_SERVICE,
        "version": DEFAULT_WFS_VERSION,
        "request": DEFAULT_WFS_REQUEST,
        "outputFormat": DEFAULT_WFS_OUTPUT_FORMAT,
        "typeNames": typeNames,
        "srsName": srsName,
        **{k: v for k, v in other_wfs_params.items()},
    }

    if cql_filter is not None:
        params["cql_filter"] = cql_filter
    if bbox is not None:
        params["bbox"] = bbox
    if out_fields is not None:
        if isinstance(out_fields, list):
            out_fields = ",".join(out_fields)
        params["PropertyName"] = f"({out_fields})"

    return params


# --- DISK mode implementation ---
def _download_to_disk(
    url: str,
    headers: dict,
    wfs_params: dict,
    temp_file_path: str,
    page_count: int,
    result_record_count: int | None,
) -> int:
    """Stream features to disk as a valid GeoJSON FeatureCollection."""
    os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)

    total_features = 0
    pages_fetched = 0
    start_index = 0
    first_feature_written = False

    with open(temp_file_path, "w", encoding="utf-8") as f:
        f.write('{"type": "FeatureCollection", "features": [\n')
        f.flush()

        while pages_fetched < MAX_PAGE_FETCHES:
            wfs_params["startIndex"] = start_index
            wfs_params["count"] = page_count

            try:
                page_data = _fetch_single_page_data(url, headers, wfs_params)
            except (BadRequest, HTTPError, RetryError) as e:
                logger.error(f"Error fetching page {pages_fetched}: {e}")
                raise
            if not page_data or not isinstance(page_data, dict):
                break

            features = page_data.get("features", [])
            if not features:
                break

            for feature in features:
                if first_feature_written:
                    f.write(",\n")
                else:
                    first_feature_written = True
                json.dump(feature, f)
                total_features += 1

            f.flush()
            logger.debug(f"Written {total_features} features so far...")

            if len(features) < page_count:
                break
            if (
                result_record_count is not None
                and total_features >= result_record_count
            ):
                break

            start_index += page_count
            pages_fetched += 1

        f.write(f'\n], "totalFeatures": {total_features}}}')
        f.flush()

    return total_features


# --- MEMORY mode implementation ---
def _download_to_memory(
    url: str,
    headers: dict,
    wfs_params: dict,
    page_count: int,
    result_record_count: int | None,
) -> dict:
    """Load all features into memory (original behaviour)."""
    all_features = []
    start_index = 0
    pages_fetched = 0
    result = None

    while pages_fetched < MAX_PAGE_FETCHES:
        wfs_params["startIndex"] = start_index
        wfs_params["count"] = page_count

        try:
            page_data = _fetch_single_page_data(url, headers, wfs_params)
        except (BadRequest, HTTPError, RetryError) as e:
            logger.error(f"Error fetching page {pages_fetched}: {e}")
            raise

        if not page_data or not isinstance(page_data, dict):
            break

        if result is None:
            result = page_data

        features = page_data.get("features", [])
        if not features:
            break

        all_features.extend(features)
        if len(features) < page_count:
            break
        if result_record_count is not None and len(all_features) >= result_record_count:
            break

        start_index += page_count
        pages_fetched += 1

    result["features"] = all_features
    result["totalFeatures"] = len(all_features)
    result.pop("numberReturned", None)
    return result


# --- Public main method ---
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
    cache_mode: Literal["DISK", "MEMORY"] = "MEMORY",
    temp_file_path: str | None = None,
    **other_wfs_params: Any,
) -> dict:
    """
    Downloads features from a WFS service.
    - In DISK mode: streams to a GeoJSON file (safe, low memory).
    - In MEMORY mode: stores all features in memory (fast but risky for large data).
    """
    if not api_key:
        raise HTTPError("API key must be provided.")
    if not typeNames:
        raise HTTPError("Typenames must be provided.")

    headers = {
        "Authorization": f"key {api_key}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    if result_record_count is not None and result_record_count < page_count:
        page_count = result_record_count

    wfs_params = _build_wfs_params(
        typeNames, srsName, cql_filter, bbox, out_fields, **other_wfs_params
    )
    request_datetime = datetime.utcnow()

    if cache_mode == "DISK":
        if not temp_file_path:
            # Create a unique, writable temp file automatically
            temp_file_path = _get_kapipy_temp_file(suffix=".geojson")
            logger.info(
                f"No temp_file_path specified; using system temp file: '{temp_file_path}'"
            )
        total_features = _download_to_disk(
            url, headers, wfs_params, temp_file_path, page_count, result_record_count
        )
        response = {
            "file_path": os.path.abspath(temp_file_path),
            "totalFeatures": total_features,
        }
    elif cache_mode == "MEMORY":
        geojson = _download_to_memory(
            url, headers, wfs_params, page_count, result_record_count
        )
        response = {
            "geojson": geojson,
            "totalFeatures": geojson.get("totalFeatures", None),
        }
    else:
        raise ValueError("Invalid cache_mode. Use 'DISK' or 'MEMORY'.")

    headers.pop("Authorization", None)
    wfs_params.pop("startIndex", None)
    wfs_params.pop("count", None)

    return {
        "request_url": url,
        "request_method": "POST",
        "request_time": request_datetime,
        "request_headers": headers,
        "request_params": wfs_params,
        "cache_mode": cache_mode,
        "response": response,
    }
