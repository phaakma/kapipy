"""
ContentManager is a class that manages the content
of a GISK instance.
"""

from urllib.parse import urljoin
import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional, Any, Union
from dacite import from_dict, Config
import copy

# from .data_classes import BaseItem
from .export import validate_export_params, request_export
from .vector_item import VectorItem
from .table_item import TableItem
from .job_result import JobResult
from .conversion import (
    get_data_type,
    sdf_to_single_polygon_geojson,
    gdf_to_single_polygon_geojson,
)

from .custom_errors import (
    BadRequest,
    ServerError,
    UnknownItemTypeError,
)

logger = logging.getLogger(__name__)

# the API sometimes uses type as a property which is not ideal
safe_keys = {"type_": "type"}
field_config = Config(strict=False, convert_key=lambda k: safe_keys.get(k, k))


class ContentManager:
    """
    Manages content for a GISK instance.

    Provides methods to search for, retrieve, and instantiate Koordinates items (layers, tables, etc.)
    based on their IDs or URLs.

    Attributes:
        jobs (list): Export jobs list.
        download_folder (str): Default folder for downloads.
    """

    def __init__(self, session: "SessionManager", audit: "AuditManager") -> None:
        """
        Initializes the ContentManager with a GISK instance.

        Parameters:
            gis (GISK): The GISK instance to manage content for.
        """
        self._session = session
        self._audit=audit
        self.jobs = []
        self.download_folder = None
        self._crop_layers_manager = None

    def _search_by_id(self, id: str) -> dict:
        """
        Searches for content by ID in the GISK.

        Parameters:
            id (str): The ID of the content to search for.

        Returns:
            dict: The search result(s) from the GISK API.
        """

        # Example: https://data.linz.govt.nz/services/api/v1.x/data/?id=51571
        url = urljoin(self._session.api_url, f"data/?id={id}")
        response = self._session.get(url)
        return response

    def _get_item_details(self, url: str) -> dict:
        """
        Fetch the item details using the item url.
        """
        return self._session.get(url)

    def get(self, id: str) -> dict:
        """
        Retrieves and instantiates a content item by ID from the GISK.

        Parameters:
            id (str): The ID of the content to retrieve.

        Returns:
            VectorItem or TableItem or None: The instantiated item, depending on its kind, or None if not found.

        Raises:
            BadRequest: If the content is not found or the request is invalid.
            UnknownItemTypeError: If the item kind is not supported.
            ServerError: If the item does not have a URL.
        """

        search_result = self._search_by_id(id)
        logger.debug(f"ContentManager getting this id: {id}")
        if len(search_result) == 0:
            return None
        elif len(search_result) > 1:
            raise BadRequest(
                f"Multiple contents found for id {id}. Please refine your search."
            )

        # Assume the first item is the desired content
        itm_properties_json = self._get_item_details(search_result[0]["url"])
        # Based on the kind of item, return the appropriate item class.
        if itm_properties_json.get("kind") == "vector":
            item = from_dict(
                data_class=VectorItem, data=itm_properties_json, config=field_config
            )

        elif itm_properties_json.get("kind") == "table":
            item = from_dict(
                data_class=TableItem, data=itm_properties_json, config=field_config
            )

        else:
            raise UnknownItemTypeError(
                f"Unsupported item kind: {item_details.get('kind')}"
            )

        item.attach_resources(session=self._session, audit=self._audit, content=self)
        item._raw_json = copy.deepcopy(itm_properties_json)

        return item

    def download(
        self,
        jobs: list["JobResults"] = None,
        folder: str = None,
        poll_interval: int = 10,
        force_all: bool = False,
    ) -> list["JobResults"]:
        """
        Downloads all exports from a list of jobs.
        Polls the jobs until they are finished. As soon as it encounters a finished job,
        it pauses polling and downloads that file, then resumes polling the remainder.

        Parameters:
            jobs (list[JobResult]): The list of job result objects to download.
            folder (str): The output folder where files will be saved.
            poll_interval (int, optional): The interval in seconds to poll the jobs. Default is 10.

        Returns:
            list[JobResult]: The list of job result objects after download.
        """

        if folder is None and self.download_folder is None:
            raise ValueError(
                "No download folder provided. Please either provide a download folder or set the download_folder attribute of the content manager class."
            )

        folder = folder if folder is not None else self.download_folder
        jobs = jobs if jobs is not None else self.jobs

        logger.info(f"Number of jobs to review: {len(jobs)}")
        if force_all:
            pending_jobs = list(jobs)
        else:
            pending_jobs = [job for job in jobs if job.downloaded == False]
        logger.info(f"Number of jobs to download: {len(pending_jobs)}")

        while pending_jobs:
            logger.info("Polling export jobs...")

            for job in pending_jobs[:]:  # iterate over a copy
                job_status = job.status

                if job_status.state != "processing":
                    job.download(folder=folder)
                    pending_jobs.remove(job)
                else:
                    logger.info(job)
            logger.info(f"{len(pending_jobs)} jobs remaining...")
            time.sleep(poll_interval)

        logger.info("All jobs completed and downloaded.")
        return jobs

    @property
    def crop_layers(self) -> "CropLayersManager":
        if self._crop_layers_manager is None:
            from .crop_layers_manager import CropLayersManager
            self._crop_layers_manager = CropLayersManager(self._session)
        return self._crop_layers_manager

    def __repr__(self) -> str:
        """
        Returns an unambiguous string representation of the ContentManager instance.

        Returns:
            str: String representation of the ContentManager.
        """
        return f"ContentManager()"

    def __str__(self) -> str:
        """
        Returns a user-friendly string representation of the ContentManager instance.

        Returns:
            str: User-friendly string representation.
        """
        return f"ContentManager"


@dataclass
class SearchResult:
    id: int
    url: str
    type_: str
    title: str
    first_published_at: Optional[str] = None
    thumbnail_url: Optional[str] = None
    published_at: Optional[str] = None
    featured_at: Optional[str] = None
    services: Optional[str] = None
    user_capabilities: Optional[List[str]] = None
    user_permissions: Optional[List[str]] = None
