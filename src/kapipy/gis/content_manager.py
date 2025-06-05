"""
ContentManager is a class that manages the content
of a GIS instance.
"""

from urllib.parse import urljoin
import logging
import time
from kapipy.custom_errors import (
    BadRequest,
    ServerError,
    UnknownItemTypeError,
)

logger = logging.getLogger(__name__)

class ContentManager:
    """
    Manages content for a GIS instance.

    Provides methods to search for, retrieve, and instantiate Koordinates items (layers, tables, etc.)
    based on their IDs or URLs.

    Attributes:
        _gis (GIS): The GIS instance this manager is associated with.
    """

    def __init__(self, gis: "GIS") -> None:
        """
        Initializes the ContentManager with a GIS instance.

        Parameters:
            gis (GIS): The GIS instance to manage content for.
        """
        self._gis = gis

    def _search_by_id(self, id: str) -> dict:
        """
        Searches for content by ID in the GIS.

        Parameters:
            id (str): The ID of the content to search for.

        Returns:
            dict: The search result(s) from the GIS API.
        """

        # Example: https://data.linz.govt.nz/services/api/v1.x/data/?id=51571
        url = urljoin(self._gis._api_url, f"data/?id={id}")
        response = self._gis.get(url)
        return response

    def get(self, id: str) -> dict:
        """
        Retrieves and instantiates a content item by ID from the GIS.

        Parameters:
            id (str): The ID of the content to retrieve.

        Returns:
            VectorItem or TableItem: The instantiated item, depending on its kind.

        Raises:
            BadRequest: If the content is not found or the request is invalid.
            UnknownItemTypeError: If the item kind is not supported.
            ServerError: If the item does not have a URL.
        """

        search_result = self._search_by_id(id)
        if not search_result or "error" in search_result:
            raise BadRequest(f"Content with id {id} not found or invalid request.")
        if len(search_result) == 0:
            return None
        elif len(search_result) > 1:
            raise BadRequest(
                f"Multiple contents found for id {id}. Please refine your search."
            )

        # Assuming the first item is the desired content
        item_json = search_result[0]
        if "url" not in item_json:
            raise ServerError(f"Item with id {id} does not have a URL.")
        item_details = self._gis.get(item_json.get("url"))

        # Based on the kind of item, return the appropriate item class.
        if item_details.get("kind") == "vector":
            from kapipy.features import VectorItem

            item = VectorItem(self._gis, item_details)
        elif item_details.get("kind") == "table":
            from kapipy.features import TableItem

            item = TableItem(self._gis, item_details)
        else:
            raise UnknownItemTypeError(
                f"Unsupported item kind: {item_details.get('kind')}"
            )

        return item

    def download(
        self, jobs: list["JobResults"], folder: str, poll_interval=10
    ) -> list["JobResults"]:

        """
        Downloads all exports from a list of jobs.
        Polls the jobs until they are finished. As soon as it encounters a finished job,
        it pauses polling and downloads that file, then resumes polling the remainder.

        Parameters:
            jobs (list[JobResults]): The list of job result objects to download.
            folder (str): The output folder where files will be saved.
            poll_interval (int, optional): The interval in seconds to poll the jobs. Default is 10.

        Returns:
            list[JobResults]: The list of job result objects after download.
        """

        pending_jobs = list(jobs)

        while pending_jobs:
            logger.info("Polling export jobs...")
            time.sleep(poll_interval)

            for job in pending_jobs[:]:  # iterate over a copy
                state = job.state

                if state != "processing":
                    job.download(folder=folder)
                    pending_jobs.remove(job)

            logger.info(f"{len(pending_jobs)} jobs remaining...")

        logger.info("All jobs completed and downloaded.")
        return jobs

    def __repr__(self) -> str:
        """
        Returns an unambiguous string representation of the ContentManager instance.

        Returns:
            str: String representation of the ContentManager.
        """
        return f"ContentManager(gis={repr(self._gis)})"

    def __str__(self) -> str:
        """
        Returns a user-friendly string representation of the ContentManager instance.

        Returns:
            str: User-friendly string representation.
        """
        return f"ContentManager for GIS: {getattr(self._gis, 'name', None) or getattr(self._gis, 'url', 'Unknown')}"