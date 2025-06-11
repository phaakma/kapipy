from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union, Protocol, runtime_checkable
from datetime import datetime
import logging

from .job_result import JobResult
from .data_classes import BaseItem, WFS, VectorItemData
from .conversion import (
    get_default_output_format,
    geojson_to_gdf,
    json_to_df,
    geojson_to_sdf,
    sdf_or_gdf_to_bbox,
)
from .wfs_utils import download_wfs_data

logger = logging.getLogger(__name__)


@dataclass
class VectorItem(BaseItem, WFS):
    data: VectorItemData

    def query_to_json(
        self,
        cql_filter: str = None,
        out_sr: int = None,
        out_fields: str | list[str] = None,
        result_record_count: int = None,
        bbox: Union[str, "gpd.GeoDataFrame", "pd.DataFrame"] = None,
        **kwargs: Any,
    ) -> dict:
        """
        Executes a WFS query on the item and returns the result as JSON.

        Parameters:
            cql_filter (str, optional): The CQL filter to apply to the query.
            out_sr (int, optional): The spatial reference system code to use for the query.
            out_fields (str, list of strings, optional): Attribute fields to include in the response. NOT IMPLEMENTED YET...
            result_record_count (int, optional): Restricts the maximum number of results to return.
            bbox (str or gpd.GeoDataFrame or pd.DataFrame, optional): The bounding box to apply to the query.
                If a GeoDataFrame or SEDF is provided, it will be converted to a bounding box string in WGS84.
            **kwargs: Additional parameters for the WFS query.

        Returns:
            dict: The result of the WFS query in JSON format.
        """

        logger.debug(f"Executing WFS query for item with id: {self.id}")

        # Handle bbox
        if bbox is not None and not isinstance(bbox, str):
            bbox = sdf_or_gdf_to_bbox(bbox)

        result = download_wfs_data(
            url=self._wfs_url,
            api_key=self._gis._api_key,
            typeNames=f"{self.type_}-{self.id}",
            cql_filter=cql_filter,
            srsName=f"EPSG:{out_sr}" or self.data.crs.srid,
            out_fields=out_fields,
            result_record_count=result_record_count,
            bbox=bbox,
            **kwargs,
        )

        return result

    def query(
        self,
        cql_filter: str = None,
        out_sr: int = None,
        out_fields: str | list[str] = None,
        result_record_count: int = None,
        bbox: Union[str, "gpd.GeoDataFrame", "pd.DataFrame"] = None,
        output_format=None,
        **kwargs: Any,
    ) -> "gpd.GeoDataFrame":
        """
        Executes a WFS query on the item and returns the result as a GeoDataFrame, SEDF, or JSON.

        Parameters:
            cql_filter (str, optional): The CQL filter to apply to the query.
            out_sr (int, optional): The spatial reference system code to use for the query.
            out_fields (str, list of strings, optional): Attribute fields to include in the response. NOT IMPLEMENTED YET...
            result_record_count (int, optional): Restricts the maximum number of results to return.
            bbox (str or gpd.GeoDataFrame or pd.DataFrame, optional): The bounding box to apply to the query.
                If a GeoDataFrame or SEDF is provided, it will be converted to a bounding box string in WGS84.
            output_format (str, optional): The output format: 'gdf', 'sdf', or 'json'. Defaults to the best available.
            **kwargs: Additional parameters for the WFS query.

        Returns:
            gpd.GeoDataFrame or arcgis.features.GeoAccessor or dict: The result of the WFS query as a GeoDataFrame, SEDF, or JSON.

        Raises:
            ImportError: If the requested output format requires a package that is not installed.
            ValueError: If the output format is unknown.
        """

        if output_format is None:
            output_format = get_default_output_format()
        output_format = output_format.lower()
        if output_format not in ("sdf", "gdf", "geodataframe", "json", "geojson"):
            raise ValueError(f"Unknown output format: {output_format}")

        out_sr = out_sr if out_sr is not None else self.data.crs.srid

        result = self.query_to_json(
            cql_filter=cql_filter,
            out_sr=out_sr,
            out_fields=out_fields,
            result_record_count=result_record_count,
            bbox=bbox,
            **kwargs,
        )

        if output_format == "sdf":
            return geojson_to_sdf(
                result,
                out_sr=out_sr,
                geometry_type=self.data.geometry_type,
                fields=self.data.fields,
            )
        elif output_format in ("gdf", "geodataframe"):
            return geojson_to_gdf(result, out_sr=out_sr, fields=self.data.fields)
        return result

    def changeset_to_json(
        self,
        from_time: str,
        to_time: str = None,
        out_sr=None,
        cql_filter: str = None,
        bbox: Union[str, "gpd.GeoDataFrame", "pd.DataFrame"] = None,
        out_fields: str | list[str] = None,
        result_record_count: int = None,
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

        result = download_wfs_data(
            url=self._wfs_url,
            api_key=self._gis._api_key,
            typeNames=f"{self.type_}-{self.id}-changeset",
            viewparams=viewparams,
            cql_filter=cql_filter,
            srsName=f"EPSG:{out_sr}" or f"{self.data.crs.id}",
            bbox=bbox,
            out_fields=out_fields,
            result_record_count=result_record_count,
            **kwargs,
        )
        return result

    def changeset(
        self,
        from_time: str,
        to_time: str = None,
        out_sr: int = None,
        cql_filter: str = None,
        bbox: Union[str, "gpd.GeoDataFrame", "pd.DataFrame"] = None,
        output_format=None,
        out_fields: str | list[str] = None,
        result_record_count: int = None,
        **kwargs: Any,
    ) -> "gpd.GeoDataFrame":
        """
        Retrieves a changeset for the item and returns it as a GeoDataFrame, SEDF, or JSON.

        Parameters:
            from_time (str): The start time for the changeset query, ISO format (e.g., "2015-05-15T04:25:25.334974").
            to_time (str, optional): The end time for the changeset query, ISO format. If not provided, the current time is used.
            out_sr (int, optional): The spatial reference system code to use for the query.
            cql_filter (str, optional): The CQL filter to apply to the changeset query.
            bbox (str or gpd.GeoDataFrame or pd.DataFrame, optional): The bounding box to apply to the changeset query.
                If a GeoDataFrame or SEDF is provided, it will be converted to a bounding box string in WGS84.
            output_format (str, optional): The output format: 'gdf', 'sdf', or 'json'. Defaults to the best available.
            **kwargs: Additional parameters for the WFS query.

        Returns:
            gpd.GeoDataFrame or arcgis.features.GeoAccessor or dict: The changeset data as a GeoDataFrame, SEDF, or JSON.

        Raises:
            ImportError: If the requested output format requires a package that is not installed.
            ValueError: If the output format is unknown.
        """

        out_sr = out_sr if out_sr is not None else self.epsg

        if output_format is None:
            output_format = get_default_output_format()
        output_format = output_format.lower()
        if output_format not in ("sdf", "gdf", "geodataframe", "json", "geojson"):
            raise ValueError(f"Unknown output format: {output_format}")

        result = self.changeset_to_json(
            from_time=from_time,
            to_time=to_time,
            out_sr=out_sr,
            cql_filter=cql_filter,
            bbox=bbox,
            out_fields=out_fields,
            result_record_count=result_record_count,
            **kwargs,
        )

        if output_format == "sdf":
            return geojson_to_sdf(
                result,
                out_sr=out_sr,
                geometry_type=self.data.geometry_type,
                fields=self.data.fields,
            )
        elif output_format in ("gdf", "geodataframe"):
            return geojson_to_gdf(result, out_sr=out_sr, fields=self.data.fields)
        return result

    def export(
        self,
        export_format: str,
        out_sr: int = None,
        extent: Union[dict, "gpd.GeoDataFrame", "pd.DataFrame"] = None,
        poll_interval: int = None,
        timeout: int = None,
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

        logger.debug(f"!! Exporting item with id: {self.id} in format: {export_format}")

        job_result = self._gis.content.export(
            itm=self,
            export_format=export_format,
            out_sr=out_sr,
            extent=extent,
            poll_interval=poll_interval,
            timeout=timeout,
            **kwargs,
        )

        logger.debug(
            f"Export job created for item with id: {self.id}, job id: {job_result.id}"
        )
        return job_result


@dataclass
class TableItem(BaseItem, WFS):

    def query_json(self, cql_filter: str = None, **kwargs: Any) -> dict:
        """
        Executes a WFS query on the item and returns the result as JSON.

        Parameters:
            cql_filter (str, optional): The CQL filter to apply to the query.
            **kwargs: Additional parameters for the WFS query.

        Returns:
            dict: The result of the WFS query in JSON format.
        """
        logger.debug(f"Executing WFS query for item with id: {self.id}")

        result = download_wfs_data(
            url=self._wfs_url,
            api_key=self._gis._api_key,
            typeNames=f"{self.type_}-{self.id}",
            cql_filter=cql_filter,
            **kwargs,
        )

        return result

    def query(self, cql_filter: str = None, **kwargs: Any) -> dict:
        """
        Executes a WFS query on the item and returns the result as a DataFrame.

        Parameters:
            cql_filter (str, optional): The CQL filter to apply to the query.
            **kwargs: Additional parameters for the WFS query.

        Returns:
            pandas.DataFrame: The result of the WFS query as a DataFrame.
        """
        logger.debug(f"Executing WFS query for item with id: {self.id}")

        result = self.query_json(cql_filter=cql_filter, **kwargs)

        df = json_to_df(result, fields=self.data.fields)
        return df

    def get_changeset_json(
        self, from_time: str, to_time: str = None, cql_filter: str = None, **kwargs: Any
    ) -> dict:
        """
        Retrieves a changeset for the item in JSON format.

        Parameters:
            from_time (str): The start time for the changeset query, ISO format (e.g., "2015-05-15T04:25:25.334974").
            to_time (str, optional): The end time for the changeset query, ISO format. If not provided, the current time is used.
            cql_filter (str, optional): The CQL filter to apply to the changeset query.
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

        result = download_wfs_data(
            url=self._wfs_url,
            api_key=self._gis._api_key,
            typeNames=f"{self.type_}-{self.id}-changeset",
            viewparams=viewparams,
            cql_filter=cql_filter,
            **kwargs,
        )

        return result

    def get_changeset(
        self, from_time: str, to_time: str = None, cql_filter: str = None, **kwargs: Any
    ) -> dict:
        """
        Retrieves a changeset for the item and returns it as a DataFrame.

        Parameters:
            from_time (str): The start time for the changeset query, ISO format (e.g., "2015-05-15T04:25:25.334974").
            to_time (str, optional): The end time for the changeset query, ISO format. If not provided, the current time is used.
            cql_filter (str, optional): The CQL filter to apply to the changeset query.
            **kwargs: Additional parameters for the WFS query.

        Returns:
            pandas.DataFrame: The changeset data as a DataFrame.
        """

        result = self.get_changeset_json(
            from_time=from_time, to_time=to_time, cql_filter=cql_filter, **kwargs
        )

        df = json_to_df(result, fields=self.data.fields)
        return df

    def export(
        self,
        export_format: str,
        poll_interval: int = None,
        timeout: int = None,
        **kwargs: Any,
    ) -> JobResult:
        """
        Exports the item in the specified format.

        Parameters:
            export_format (str): The format to export the item in.
            poll_interval (int, optional): The interval in seconds to poll the export job status. Default is 10 seconds.
            timeout (int, optional): The maximum time in seconds to wait for the export job to complete. Default is 600 seconds (10 minutes).
            **kwargs: Additional parameters for the export request.

        Returns:
            JobResult: A JobResult instance containing the export job details.

        Raises:
            ValueError: If export validation fails.
        """

        logger.debug(f"!! Exporting item with id: {self.id} in format: {export_format}")

        job_result = self._gis.content.export(
            itm=self,
            export_format=export_format,
            poll_interval=poll_interval,
            timeout=timeout,
            **kwargs,
        )

        logger.debug(
            f"Export job created for item with id: {self.id}, job id: {job_result.id}"
        )
        return job_result
