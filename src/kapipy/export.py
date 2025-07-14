# export.py
import httpx
import os
import json
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
from .custom_errors import ExportError

logger = logging.getLogger(__name__)


def validate_export_params(
    api_url: str,
    api_key: str,
    id: str,
    data_type: str,
    kind: str,
    export_format: str,
    crs: str = None,
    filter_geometry: dict = None,
    **kwargs: Any,
) -> bool:
    """
    Validates export parameters for a given item.

    Parameters:
        api_url (str): The base URL of the Koordinates API.
        api_key (str): The API key for authentication.
        id (str): The ID of the item to export.
        data_type (str): The type of data ('layer' or 'table').
        kind (str): The kind of export (e.g., 'shp', 'geojson').
        export_format (str): The format for the export.
        crs (str, optional): Coordinate Reference System, if applicable.
        filter_geometry (dict, optional): Spatial filter_geometry for the export.
        **kwargs: Additional parameters for the export.

    Returns:
        bool: True if the export parameters are valid, False otherwise.

    Raises:
        ValueError: If the data type is unsupported or not implemented, or if validation fails.
    """

    logger.debug("Validating export parameters")

    api_url = api_url if api_url.endswith("/") else f"{api_url}/"
    if data_type == "layer":
        download_url = f"{api_url}layers/"
    elif data_type == "table":
        download_url = f"{api_url}tables/"
    else:
        raise ValueError(f"Unsupported or not implemented data type: {data_type}")
    validation_url = f"{api_url}exports/validate/"

    logger.debug(f"{download_url=}")

    data = {
        "items": [{"item": f"{download_url}{id}/"}],
        "formats": {f"{kind}": export_format},
        **kwargs,
    }

    if data_type == "layer" and crs:
        data["crs"] = crs
    if data_type == "layer" and filter_geometry:
        data["extent"] = filter_geometry

    logger.debug(f"Validate:\n{json.dumps(data, indent=2)}")

    headers = {"Authorization": f"key {api_key}"}
    is_valid = False

    try:
        response = httpx.post(validation_url, headers=headers, json=data)
        response.raise_for_status()

        # if response has any 200 status code, check for validation errors
        if response.status_code in (200, 201):
            try:
                json_response = response.json()
                if any(
                    not item.get("is_valid", "true") for item in json_response["items"]
                ):
                    err = "An error occurred when attempting to validate an export with this configuration. Check for 'invalid_reasons' in the logs."
                    logger.error(err)
                    logger.error(json_response["items"])
                    raise ValueError(err)
                is_valid = True
            except ValueError as e:
                err = f"Error parsing JSON from export validation: {e}"
                logger.debug(err)
                raise ValueError(err)

    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else None
        logger.error(
            f"HTTP error during validation: {status} - {getattr(e.response, 'text', '')}"
        )
        if status is not None and 400 <= status < 500:
            raise ValueError(
                f"Bad request ({status}) for URL {validation_url}: {getattr(e.response, 'text', '')}"
            ) from e
        raise

    logger.debug(f"Export parameters passed validation check. {is_valid=}")
    return is_valid


def request_export(
    api_url: str,
    api_key: str,
    id: str,
    data_type: str,
    kind: str,
    export_format: str,
    crs: str = None,
    filter_geometry: dict = None,
    **kwargs: Any,
) -> dict:
    """
    Requests an export of a given item from the Koordinates API.

    Parameters:
        api_url (str): The base URL of the Koordinates API.
        api_key (str): The API key for authentication.
        id (str): The ID of the item to export.
        data_type (str): The type of data ('layer' or 'table').
        kind (str): The kind of export (e.g., 'shp', 'geojson').
        export_format (str): The format for the export.
        crs (str, optional): Coordinate Reference System, if applicable.
        filter_geometry (dict, optional): Spatial filter_geometry for the export.
        **kwargs: Additional parameters for the export.

    Returns:
        dict: The response from the export request, typically containing job details.

    Raises:
        ExportError: If the export request fails or if the response cannot be parsed.
        ValueError: If the data type is unsupported or not implemented.
    """

    api_url = api_url if api_url.endswith("/") else f"{api_url}/"
    export_url = f"{api_url}exports/"
    if data_type == "layer":
        download_url = f"{api_url}layers/"
    elif data_type == "table":
        download_url = f"{api_url}tables/"
    else:
        raise ValueError(f"Unsupported or not implemented data type: {data_type}")
    logger.debug(f"{download_url=}")

    data = {
        "items": [{"item": f"{download_url}{id}/"}],
        "formats": {f"{kind}": export_format},
        **kwargs,
    }

    if data_type == "layer" and crs:
        data["crs"] = crs
    if data_type == "layer" and filter_geometry:
        data["extent"] = filter_geometry

    logger.debug(f"Export request: {data=}")

    headers = {"Authorization": f"key {api_key}"}

    request_datetime = datetime.utcnow()
    try:
        response = httpx.post(export_url, headers=headers, json=data)
        response.raise_for_status()
        try:
            json_response = response.json()
        except ValueError as e:
            err = f"Error parsing JSON from export request: {e}"
            logger.debug(err)
            raise ExportError(err)
    except httpx.HTTPStatusError as e:
        err = f"Failed export request with status code: {e.response.status_code if e.response else 'unknown'}"
        logger.debug(err)
        logger.debug(e)
        raise ExportError(err)
    
    headers.pop('Authorization', None)
    return {
        "request_url": export_url,
        "request_method": "POST",
        "request_time": request_datetime,
        "request_headers": headers,
        "request_params": data,
        "response": json_response
    }