"""
vector_item.py
A class to represent a vector dataset.
"""

import logging
import json
from datetime import datetime
from typing import Any, TYPE_CHECKING, Union
from kapipy.gis.base_item import BaseItem
from kapipy.gis.job_result import JobResult
from . import wfs as wfs_features
from . import export as export_features
from .conversion import (
    geojson_to_gdf,
    geojson_to_sdf,
    sdf_or_gdf_to_single_polygon_geojson,
    sdf_or_gdf_to_bbox,
    get_data_type,
    get_default_output_format
)
from kapipy.gis import has_geopandas, has_arcgis
if TYPE_CHECKING:
    if has_geopandas:
        import geopandas as gpd
    if has_arcgis:
        import arcgis

logger = logging.getLogger(__name__)


class VectorItem(BaseItem):
    """
    Represents a vector dataset item in the Koordinates system.

    Inherits from BaseItem and provides methods to interact with vector datasets, including
    querying features, exporting data, and retrieving changesets.

    Attributes:
        _supports_changesets (bool or None): Whether the item supports changesets.
        _services (list or None): Cached list of services for this item.
        _gis (GIS): The GIS instance this item belongs to.
        _raw_json (dict): The raw JSON dictionary representing the item.
        id (str): The unique identifier of the item.
        type (str): The type of the item (should be 'layer').
        kind (str): The kind of the item (should be 'vector').
        title (str): The title of the item.
        description (str): The description of the item.
        _jobs (list): List of JobResult objects associated with this item.
    """

    def __init__(self, gis: "GIS", item_dict: dict) -> None:
        """
        Initializes the VectorItem with a dictionary of item details.

        Parameters:
            gis (GIS): The GIS instance this item belongs to.
            item_dict (dict): A dictionary containing the item's details, typically from an API response.
        """

        super().__init__(gis, item_dict)
        self._supports_changesets = None
        self._services = None
        logger.debug(
            f"Initializing KVectorItem with id: {self.id}, title: {self.title}"
        )

    @property
    def fields(self) -> list:
        """
        Returns the fields of the item.

        Returns:
            list: A list of fields associated with the item.
        """
        return self._raw_json.get("data", {}).get("fields", [])

    @property
    def epsg(self) -> int | None:
        """
        Returns the EPSG code of the item.

        Returns:
            int or None: The EPSG code associated with the item, or None if not available.
        """
        return self._raw_json.get("data", {}).get("crs", {}).get("srid", None)

    @property
    def primary_key_fields(self) -> list:
        """
        Returns the primary key fields of the item.

        Returns:
            list: A list of primary key fields associated with the item.
        """
        return self._raw_json.get("data", {}).get("primary_key_fields", [])

    @property
    def geometry_type(self) -> str | None:
        """
        Returns the geometry type of the item.

        Returns:
            str or None: The geometry type associated with the item, or None if not available.
        """
        return self._raw_json.get("data", {}).get("geometry_type", None)

    @property
    def feature_count(self) -> int | None:
        """
        Returns the number of features in the item.

        Returns:
            int or None: The number of features associated with the item, or None if not available.
        """
        return self._raw_json.get("data", {}).get("feature_count", None)

    @property
    def extent(self) -> dict | None:
        """
        Returns the extent of the item.

        Returns:
            dict or None: A dictionary containing the extent of the item, or None if not available.
        """
        return self._raw_json.get("data", {}).get("extent", None)

    @property
    def export_formats(self) -> list | None:
        """
        Returns the export formats available for the item.

        Returns:
            list or None: A list of export formats associated with the item, or None if not available.
        """
        return self._raw_json.get("data", {}).get("export_formats", None)

    @property
    def supports_changesets(self) -> bool:
        """
        Returns whether the item supports changesets.

        Returns:
            bool: True if the item supports changesets, False otherwise.
        """
        if self._supports_changesets is None:
            logger.debug(f"Checking if item with id: {self.id} supports changesets")
            self._supports_changesets = any(
                service.get("key") == "wfs-changesets" for service in self.services
            )

        return self._supports_changesets

    @property
    def _wfs_url(self) -> str:
        """
        Returns the WFS URL for the item.

        Returns:
            str: The WFS URL associated with the item.
        """
        return f"{self._gis._service_url}wfs/"

    def get_wfs_service(self) -> str:
        """
        Returns the item's WFS service URL.

        Returns:
            str: The WFS service URL.
        """

        logger.debug(f"Creating WFS service for item with id: {self.id}")
        wfs_service = self._gis.wfs.operations

    def query_to_json(
        self,
        cql_filter: str = None,
        wkid: int = None,
        bbox: Union[str, "gpd.GeoDataFrame", "pd.DataFrame"] = None,
        **kwargs: Any,
    ) -> dict:
        """
        Executes a WFS query on the item and returns the result as JSON.

        Parameters:
            cql_filter (str, optional): The CQL filter to apply to the query.
            srsName (str, optional): The spatial reference system name to use for the query.
            bbox (str or gpd.GeoDataFrame, optional): The bounding box to apply to the query.
                If a GeoDataFrame is provided, it will be converted to a bounding box string in WGS84.
            **kwargs: Additional parameters for the WFS query.

        Returns:
            dict: The result of the WFS query in JSON format.
        """

        logger.debug(f"Executing WFS query for item with id: {self.id}")

        # Handle bbox
        if bbox is not None and not isinstance(bbox, str):              
            bbox = sdf_or_gdf_to_bbox(bbox)

        result = wfs_features.download_wfs_data(
            url=self._wfs_url,
            api_key=self._gis._api_key,
            typeNames=f"{self.type}-{self.id}",
            cql_filter=cql_filter,
            srsName=f'EPSG:{wkid}' or f"EPSG:{self.epsg}" if self.epsg else None,
            bbox=bbox,
            **kwargs,
        )

        return result

    def query(
        self,
        cql_filter: str = None,
        wkid: int = None,
        bbox: Union[str, "gpd.GeoDataFrame", "pd.DataFrame"] = None,
        output_format = None,
        **kwargs: Any,
    ) -> "gpd.GeoDataFrame":
        """
        Executes a WFS query on the item and returns the result as a GeoDataFrame.
        Only works if geopandas is installed.

        Parameters:
            cql_filter (str, optional): The CQL filter to apply to the query.
            srsName (str, optional): The spatial reference system name to use for the query.
            bbox (str or gpd.GeoDataFrame, optional): The bounding box to apply to the query.
                If a GeoDataFrame is provided, it will be converted to a bounding box string in WGS84.
            output_format (sdef or gdf or json)
            **kwargs: Additional parameters for the WFS query.

        Returns:
            gpd.GeoDataFrame: The result of the WFS query as a GeoDataFrame.

        Raises:
            ImportError if geopandas is not installed.
        """

        if output_format is None:
            output_format = get_default_output_format()
        output_format = output_format.lower()
        if output_format not in ('sdf', 'gdf', 'geodataframe', 'json', 'geojson'):
            raise ValueError(f'Unknown output format: {output_format}')

        wkid = wkid if wkid is not None else self.epsg

        result = self.query_to_json(
            cql_filter=cql_filter,
            wkid=wkid,
            bbox=bbox,
            **kwargs,
        )

        if output_format == 'sdf':
            return geojson_to_sdf(result, wkid=wkid, fields=self.fields)
        elif output_format in ('gdf', 'geodataframe'):
            return geojson_to_gdf(result, wkid=wkid, fields=self.fields)
        return result


    def changeset_to_json(
        self,
        from_time: str,
        to_time: str = None,
        wkid = None,
        cql_filter: str = None,
        bbox: Union[str, "gpd.GeoDataFrame", "pd.DataFrame"] = None,
        **kwargs: Any,
    ) -> dict:
        """
        Retrieves a changeset for the item in JSON format.

        Parameters:
            from_time (str): The start time for the changeset query, ISO format (e.g., "2015-05-15T04:25:25.334974").
            to_time (str, optional): The end time for the changeset query, ISO format. If not provided, the current time is used.
            cql_filter (str, optional): The CQL filter to apply to the changeset query.
            bbox (str or gpd.GeoDataFrame, optional): The bounding box to apply to the changeset query.
                If a GeoDataFrame is provided, it will be converted to a bounding box string in WGS84.
            **kwargs: Additional parameters for the WFS query.

        Returns:
            dict: The changeset data in JSON format.

        Raises:
            ValueError: If the item does not support changesets.
        """

        if not self.supports_changesets:
            logger.error(f"Item with id: {self.id} does not support changesets.")
            raise ValueError("This item does not support changesets.")

        if to_time is None:
            to_time = datetime.now().isoformat()
        logger.debug(
            f"Fetching changeset for item with id: {self.id} from {from_time} to {to_time}"
        )

        viewparams = f"from:{from_time};to:{to_time}"

        # Handle bbox
        if bbox is not None and not isinstance(bbox, str):              
            bbox = sdf_or_gdf_to_bbox(bbox)

        result = wfs_features.download_wfs_data(
            url=self._wfs_url,
            api_key=self._gis._api_key,
            typeNames=f"layer-{self.id}-changeset",
            viewparams=viewparams,
            cql_filter=cql_filter,
            srsName=f'EPSG:{wkid}' or f"EPSG:{self.epsg}" if self.epsg else None,
            bbox=bbox,
            **kwargs,
        )
        return result

    def changeset(
        self,
        from_time: str,
        to_time: str = None,
        wkid: int = None,
        cql_filter: str = None,
        bbox: Union[str, "gpd.GeoDataFrame", "pd.DataFrame"] = None,
        output_format = None,
        **kwargs: Any,
    ) -> "gpd.GeoDataFrame":
        """
        Retrieves a changeset for the item and returns it as a GeoDataFrame.

        Parameters:
            from_time (str): The start time for the changeset query, ISO format (e.g., "2015-05-15T04:25:25.334974").
            to_time (str, optional): The end time for the changeset query, ISO format. If not provided, the current time is used.
            cql_filter (str, optional): The CQL filter to apply to the changeset query.
            bbox (str or gpd.GeoDataFrame, optional): The bounding box to apply to the changeset query.
                If a GeoDataFrame is provided, it will be converted to a bounding box string in WGS84.
            **kwargs: Additional parameters for the WFS query.

        Returns:
            gpd.GeoDataFrame: The changeset data as a GeoDataFrame.
        """

        wkid = wkid if wkid is not None else self.epsg

        if output_format is None:
            output_format = get_default_output_format()
        output_format = output_format.lower()
        if output_format not in ('sdf', 'gdf', 'geodataframe', 'json', 'geojson'):
            raise ValueError(f'Unknown output format: {output_format}')

        result = self.changeset_to_json(
            from_time=from_time,
            to_time=to_time,
            wkid=wkid,
            cql_filter=cql_filter,
            bbox=bbox,
            **kwargs,
        )

        if output_format == 'sdf':
            return geojson_to_sdf(result, wkid=wkid, fields=self.fields)
        elif output_format in ('gdf', 'geodataframe'):
            return geojson_to_gdf(result, wkid=wkid, fields=self.fields)
        return result

    @property
    def services(self) -> list:
        """
        Returns the services associated with the item.

        Returns:
            list: A list of services associated with the item.
        """

        if self._services is None:
            logger.debug(f"Fetching services for item with id: {self.id}")
            url = self._gis._api_url + f"layers/{self.id}/services/"
            self._services = self._gis.get(url)
        logger.debug(
            f"Returning {len(self._services)} services for item with id: {self.id}"
        )
        return self._services

    def reset(self) -> None:
        """
        Resets the VectorItem instance, clearing cached properties.
        This is useful for refreshing the item state.
        """
        logger.debug(f"Resetting KVectorItem with id: {self.id}")
        self._supports_changesets = None
        self._services = None
        self._raw_json = None

    def _resolve_export_format(self, export_format: str) -> str:
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
            f"Validating export format: {export_format} for item with id: {self.id}"
        )
        mimetype = None

        # check if the export format is either any of the names or mimetypes in the example_formats
        export_format = export_format.lower()

        # Handle special cases for export formats geopackage and sqlite as it seems a
        # strange string argument to expect a user to pass in
        if export_format in ("geopackage", "sqlite"):
            export_format = "GeoPackage / SQLite".lower()

        for f in self.export_formats:
            if export_format in (f["name"].lower(), f["mimetype"].lower()):
                mimetype = f["mimetype"]

        if mimetype is None:
            raise ValueError(
                f"Export format {export_format} is not supported by this item. Refer supported formats using : itm.export_formats"
            )

        logger.debug(f"Resolved export format: {mimetype} from {export_format}")
        return mimetype

    def _validate_export_request(
        self,
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

        export_format = self._resolve_export_format(export_format)

        # log out all the input parameters including kwargs
        logger.debug(
            f"Validating export request for item with id: {self.id}, {export_format=}, {crs=}, {extent=},  {kwargs=}"
        )

        return export_features.validate_export_params(
            self._gis._api_url,
            self._gis._api_key,
            self.id,
            self.type,
            self.kind,
            export_format,
            crs,
            extent,
            **kwargs,
        )

    def export(
        self,
        export_format: str,
        wkid: int = None,
        extent: Union[dict, "gpd.GeoDataFrame", "pd.DataFrame"] = None,
        poll_interval: int = 10,
        timeout: int = 600,
        **kwargs: Any,
    ) -> JobResult:
        """
        Exports the item in the specified format.

        Parameters:
            export_format (str): The format to export the item in.
            crs (str, optional): The coordinate reference system to use for the export.
            extent (dict or gpd.GeoDataFrame, optional): The extent to use for the export. Should be a GeoJSON dictionary or a GeoDataFrame.
            poll_interval (int, optional): The interval in seconds to poll the export job status. Default is 10 seconds.
            timeout (int, optional): The maximum time in seconds to wait for the export job to complete. Default is 600 seconds (10 minutes).
            **kwargs: Additional parameters for the export request.

        Returns:
            JobResult: A JobResult instance containing the export job details.

        Raises:
            ValueError: If export validation fails.
        """

        logger.debug(f"Exporting item with id: {self.id} in format: {export_format}")

        wkid = wkid if wkid is not None else self.epsg
        crs = f'EPSG:{wkid}'

        if extent is not None:
            extent = sdf_or_gdf_to_single_polygon_geojson(extent)

        export_format = self._resolve_export_format(export_format)

        validate_export_request = self._validate_export_request(
            export_format,
            crs=crs,
            extent=extent,
            **kwargs,
        )

        if not validate_export_request:
            logger.error(
                f"Export validation failed for item with id: {self.id} in format: {export_format}"
            )
            raise ValueError(
                f"Export validation failed for item with id: {self.id} in format: {export_format}"
            )

        export_request = export_features.request_export(
            self._gis._api_url,
            self._gis._api_key,
            self.id,
            self.type,
            self.kind,
            export_format,
            crs=crs,
            extent=extent,
            **kwargs,
        )

        job_result = JobResult(
            export_request, self._gis, poll_interval=poll_interval, timeout=timeout
        )
        self._jobs.append(job_result)
        logger.debug(
            f"Export job created for item with id: {self.id}, job id: {job_result.id}"
        )
        return job_result

    def __repr__(self) -> str:
        """
        Returns an unambiguous string representation of the VectorItem instance.

        Returns:
            str: String representation of the VectorItem.
        """
        return f"VectorItem(id={self.id}, title={self.title}, type={self.type}, kind={self.kind})"

    def __str__(self) -> str:
        """
        Returns a user-friendly string representation of the VectorItem instance.

        Returns:
            str: User-friendly string representation.
        """
        return f"{self.title or 'Unnamed Vector'} (ID: {self.id}, Type: {self.type})"
