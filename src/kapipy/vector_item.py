from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import logging

from .job_result import JobResult
from .data_classes import BaseItem, VectorItemData
from .wfs_response import WFSResponse  
from .conversion import (
    bbox_sdf_into_cql_filter,
    geom_sdf_into_cql_filter,
    bbox_gdf_into_cql_filter,
    geom_gdf_into_cql_filter,
    get_data_type,
)
from .wfs_utils import download_wfs_data

logger = logging.getLogger(__name__)


@dataclass
class VectorItem(BaseItem):
    data: VectorItemData

    def query(
        self,
        cql_filter: str = None,
        out_sr: int = None,
        out_fields: str | list[str] = None,
        result_record_count: int = None,
        bbox: str = None,
        bbox_geometry: Union["gpd.GeoDataFrame", "pd.DataFrame"] = None,
        filter_geometry: Union["gpd.GeoDataFrame", "pd.DataFrame"] = None,
        spatial_rel: str = None,
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

        if bbox is not None and cql_filter is not None:
            raise ValueError(
                f"Cannot process both bbox string and cql_filter together."
            )

        if bbox is not None and (
            bbox_geometry is not None or filter_geometry is not None
        ):
            raise ValueError(
                f"Cannot process both a bbox string and a geometry together."
            )

        if bbox_geometry is not None and filter_geometry is not None:
            raise ValueError(
                f"Cannot process both a bbox_geometry and filter_geometry together."
            )

        if bbox_geometry is not None:
            data_type = get_data_type(bbox_geometry)
            if data_type == "sdf":
                cql_filter = bbox_sdf_into_cql_filter(
                    sdf=bbox_geometry,
                    geometry_field=self.data.geometry_field,
                    srid=self.data.crs.srid,
                    cql_filter=cql_filter,
                )
            elif data_type == "gdf":
                cql_filter = bbox_gdf_into_cql_filter(
                    gdf=bbox_geometry,
                    geometry_field=self.data.geometry_field,
                    srid=self.data.crs.srid,
                    cql_filter=cql_filter,
                )

        if filter_geometry is not None:
            data_type = get_data_type(filter_geometry)
            if data_type == "sdf":
                cql_filter = geom_sdf_into_cql_filter(
                    sdf=filter_geometry,
                    geometry_field=self.data.geometry_field,
                    srid=self.data.crs.srid,
                    cql_filter=cql_filter,
                    spatial_rel=spatial_rel,
                )
            elif data_type == "gdf":
                cql_filter = geom_gdf_into_cql_filter(
                    gdf=filter_geometry,
                    geometry_field=self.data.geometry_field,
                    srid=self.data.crs.srid,
                    cql_filter=cql_filter,
                    spatial_rel=spatial_rel,
                )

        query_details = download_wfs_data(
            url=self._wfs_url,
            api_key=self._session.api_key,
            typeNames=f"{self.type_}-{self.id}",
            cql_filter=cql_filter,
            srsName=f"EPSG:{out_sr}" or self.data.crs.srid,
            out_fields=out_fields,
            result_record_count=result_record_count,
            bbox=bbox,
            **kwargs,
        )

        self._audit.add_request_record(
            item_id=self.id,
            item_kind=self.kind,
            item_type=self.type_,
            request_type="wfs-query",
            request_url=query_details.get("request_url", ""),
            request_method=query_details.get("request_method", ""),
            request_time=query_details.get("request_time", ""),
            request_headers=query_details.get("request_headers", ""),
            request_params=query_details.get("request_params", ""),
            response=query_details.get("response", ""),
        )

        return WFSResponse(query_details.get("response", {}), self, out_sr)


    def changeset(
        self,
        from_time: str,
        to_time: str = None,
        out_sr=None,
        cql_filter: str = None,
        out_fields: str | list[str] = None,
        result_record_count: int = None,
        bbox: str = None,
        bbox_geometry: Union["gpd.GeoDataFrame", "pd.DataFrame"] = None,
        filter_geometry: Union["gpd.GeoDataFrame", "pd.DataFrame"] = None,
        spatial_rel: str = None,
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

        if bbox is not None and cql_filter is not None:
            raise ValueError(
                f"Cannot process both bbox string and cql_filter together."
            )

        if bbox is not None and (
            bbox_geometry is not None or filter_geometry is not None
        ):
            raise ValueError(
                f"Cannot process both a bbox string and a geometry together."
            )

        if bbox_geometry is not None and filter_geometry is not None:
            raise ValueError(
                f"Cannot process both a bbox_geometry and filter_geometry together."
            )

        if bbox_geometry is not None:
            data_type = get_data_type(bbox_geometry)
            if data_type == "sdf":
                cql_filter = bbox_sdf_into_cql_filter(
                    sdf=bbox_geometry,
                    geometry_field=self.data.geometry_field,
                    srid=self.data.crs.srid,
                    cql_filter=cql_filter,
                )
            elif data_type == "gdf":
                cql_filter = bbox_gdf_into_cql_filter(
                    gdf=bbox_geometry,
                    geometry_field=self.data.geometry_field,
                    srid=self.data.crs.srid,
                    cql_filter=cql_filter,
                )

        if filter_geometry is not None:
            data_type = get_data_type(filter_geometry)
            if data_type == "sdf":
                cql_filter = geom_sdf_into_cql_filter(
                    sdf=filter_geometry,
                    geometry_field=self.data.geometry_field,
                    srid=self.data.crs.srid,
                    cql_filter=cql_filter,
                    spatial_rel=spatial_rel,
                )
            elif data_type == "gdf":
                cql_filter = geom_gdf_into_cql_filter(
                    gdf=filter_geometry,
                    geometry_field=self.data.geometry_field,
                    srid=self.data.crs.srid,
                    cql_filter=cql_filter,
                    spatial_rel=spatial_rel,
                )

        query_details = download_wfs_data(
            url=self._wfs_url,
            api_key=self._session.api_key,
            typeNames=f"{self.type_}-{self.id}-changeset",
            viewparams=viewparams,
            cql_filter=cql_filter,
            srsName=f"EPSG:{out_sr}" or f"{self.data.crs.id}",
            bbox=bbox,
            out_fields=out_fields,
            result_record_count=result_record_count,
            **kwargs,
        )

        self._audit.add_request_record(
            item_id=self.id,
            item_kind=self.kind,
            item_type=self.type_,
            request_type="wfs-changeset",
            request_url=query_details.get("request_url", ""),
            request_method=query_details.get("request_method", ""),
            request_time=query_details.get("request_time", ""),
            request_headers=query_details.get("request_headers", ""),
            request_params=query_details.get("request_params", ""),
            response=query_details.get("response", ""),
        )

        return WFSResponse(query_details.get("response", {}), self, out_sr)


    def __str__(self) -> None:
        """
        User friendly string of a base item.
        """

        return f"Item id: {self.id}, type_: {self.type_}, title: {self.title}"
