"""
ContentManager is a class that manages the content
of a GIS instance.
"""

from urllib.parse import urljoin
import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional, Any, Union
from dacite import from_dict, Config
import copy

from .data_classes import BaseItem
from .export import validate_export_params, request_export
from .items import VectorItem, TableItem
from .job_result import JobResult
from .conversion import sdf_or_gdf_to_single_polygon_geojson

from .custom_errors import (
    BadRequest,
    ServerError,
    UnknownItemTypeError,
)

# from .layer_item import LayerItem, BaseItem


# from .items.vector_item import VectorItem

logger = logging.getLogger(__name__)

# the API sometimes uses type as a property which is not ideal
safe_keys = {"type_": "type"}
field_config = Config(strict=False, convert_key=lambda k: safe_keys.get(k, k))


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
        self.jobs = []
        self.download_folder = None

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
            VectorItem or TableItem or None: The instantiated item, depending on its kind, or None if not found.

        Raises:
            BadRequest: If the content is not found or the request is invalid.
            UnknownItemTypeError: If the item kind is not supported.
            ServerError: If the item does not have a URL.
        """

        search_result = self._search_by_id(id)
        logger.debug(f'ContentManager getting this id: {id}')
        if len(search_result) == 0:
            return None
        elif len(search_result) > 1:
            raise BadRequest(
                f"Multiple contents found for id {id}. Please refine your search."
            )

        # Assume the first item is the desired content
        itm_properties_json = self._gis.get(search_result[0]["url"])
        # add the raw json as it's own property before converting into a class
        # itm_properties_json["_raw_json"] = copy.copy(itm_properties_json)
        # itm_properties = dacite.from_dict(
        #     data_class=LayerItem, data=itm_properties_json, config=field_config
        # )

        # itm_properties_json['_gis'] = self._gis

        # Based on the kind of item, return the appropriate item class.
        if itm_properties_json.get("kind") == "vector":
            # from kapipy.features import VectorItem
            # item = VectorItem(self._gis, item_details)
            item = from_dict(
                data_class=VectorItem, data=itm_properties_json, config=field_config
            )

        elif itm_properties_json.get("kind") == "table":

            # from kapipy.features import TableItem
            # item = TableItem(self._gis, item_details)
            item = from_dict(
                data_class=TableItem, data=itm_properties_json, config=field_config
            )

        else:
            raise UnknownItemTypeError(
                f"Unsupported item kind: {item_details.get('kind')}"
            )

        item._gis = self._gis
        item._raw_json = copy.deepcopy(itm_properties_json)

        return item

    def _resolve_export_format(self, itm: BaseItem, export_format: str) -> str:
        """
        Validates if the export format is supported by the item and returns the mimetype.

        Parameters:
            export_format (str): The format to validate.

        Returns:
            str: The mimetype of the export format if supported.

        Raises:
            ValueError: If the export format is not supported by this item.
        """

        logger.debug(
            f"Validating export format: {export_format} for item with id: {itm.id}"
        )
        mimetype = None

        # check if the export format is either any of the names or mimetypes in the example_formats
        export_format = export_format.lower()

        # Handle special cases for export formats geopackage and sqlite as it seems a
        # strange string argument to expect a user to pass in
        if export_format in ("geopackage", "sqlite"):
            export_format = "GeoPackage / SQLite".lower()

        export_formats = itm.data.export_formats

        for f in itm.data.export_formats:
            if export_format in (f.name.lower(), f.mimetype.lower()):
                mimetype = f.mimetype

        if mimetype is None:
            raise ValueError(
                f"Export format {export_format} is not supported by this item. Refer supported formats using : itm.data.export_formats"
            )

        logger.debug(f"Resolved export format: {mimetype} from {export_format}")
        return mimetype

    def _validate_export_request(
        self,
        itm: BaseItem,
        export_format: str,
        crs: str = None,
        extent: dict = None,
        **kwargs: Any,
    ) -> bool:
        """
        Validates the export request parameters for the item.

        Parameters:
            export_format (str): The format to export the item in.
            crs (str, optional): The coordinate reference system to use for the export.
            extent (dict, optional): The extent to use for the export. Should be a GeoJSON dictionary.
            **kwargs: Additional parameters for the export request.

        Returns:
            bool: True if the export request is valid, False otherwise.
        """

        export_format = self._resolve_export_format(itm, export_format)

        # log out all the input parameters including kwargs
        logger.debug(
            f"Validating export request for item with id: {itm.id}, {export_format=}, {crs=}, {extent=},  {kwargs=}"
        )

        return validate_export_params(
            self._gis._api_url,
            self._gis._api_key,
            itm.id,
            itm.type_,
            itm.kind,
            export_format,
            crs,
            extent,
            **kwargs,
        )

    def export(
        self,
        itm: BaseItem,
        export_format: str,
        out_sr: Optional[int] = None,
        extent: Optional[Union[dict, "gpd.GeoDataFrame", "pd.DataFrame"]] = None,
        poll_interval: int = 10,
        timeout: int = 600,
        **kwargs: Any,
    ) -> JobResult:
        """
        Exports the item in the specified format.

        Parameters:
            export_format (str): The format to export the item in.
            out_sr (int, optional): The coordinate reference system code to use for the export.
            extent (dict or gpd.GeoDataFrame or pd.DataFrame, optional): The extent to use for the export. Should be a GeoJSON dictionary, GeoDataFrame, or SEDF.
            poll_interval (int, optional): The interval in seconds to poll the export job status. Default is 10 seconds.
            timeout (int, optional): The maximum time in seconds to wait for the export job to complete. Default is 600 seconds (10 minutes).
            **kwargs: Additional parameters for the export request.

        Returns:
            JobResult: A JobResult instance containing the export job details.

        Raises:
            ValueError: If export validation fails.
        """

        logger.debug(f"Exporting item with id: {itm.id} in format: {export_format}")

        crs = None
        if itm.kind in ["vector"]:
            out_sr = out_sr if out_sr is not None else itm.data.crs.srid
            crs = f"EPSG:{out_sr}"
            if extent is not None:
                extent = sdf_or_gdf_to_single_polygon_geojson(extent)

        export_format = self._resolve_export_format(itm, export_format)

        validate_export_request = self._validate_export_request(
            itm,
            export_format,
            crs=crs,
            extent=extent,
            **kwargs,
        )

        if not validate_export_request:
            logger.error(
                f"Export validation failed for item with id: {itm.id} in format: {export_format}"
            )
            raise ValueError(
                f"Export validation failed for item with id: {itm.id} in format: {export_format}"
            )

        export_request = request_export(
            self._gis._api_url,
            self._gis._api_key,
            itm.id,
            itm.type_,
            itm.kind,
            export_format,
            crs=crs,
            extent=extent,
            **kwargs,
        )

        job_result = JobResult(
            export_request, self._gis, poll_interval=poll_interval, timeout=timeout
        )
        self.jobs.append(job_result)
        logger.debug(
            f"Export job created for item with id: {itm.id}, job id: {job_result.id}"
        )
        return job_result

    def download(
        self,
        jobs: list["JobResults"] = None,
        folder: str = None,
        poll_interval: int = 10,
        force_all: bool = False
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
