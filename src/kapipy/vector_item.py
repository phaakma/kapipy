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
    """
    Represents a vector item in the GISK content system.

    Inherits from BaseItem and provides methods for querying and retrieving changesets via WFS.
    """
    data: VectorItemData

    def query(
        self,
        *,
        from_time: str = None,
        to_time: str = None,
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
            out_fields (str, list of strings, optional): Attribute fields to include in the response.
            result_record_count (int, optional): Restricts the maximum number of results to return.
            bbox (str or gpd.GeoDataFrame or pd.DataFrame, optional): The bounding box to apply to the query.
                If a GeoDataFrame or SEDF is provided, it will be converted to a bounding box string in WGS84.
            bbox_geometry (gdf or sdf): A dataframe that is converted to a bounding box and used to spatially filter the response.  
            filter_geometry (gdf or sdf): A dataframe that is used to spatially filter the response.  
            **kwargs: Additional parameters for the WFS query.

        Returns:
            dict: The result of the WFS query in JSON format.
        """

        logger.info(f"Executing WFS query for item with id: {self.id}")

        viewparams = None
        is_changeset_request = False
        if from_time is not None or to_time is not None:
            is_changeset_request = True
            if not self.supports_changesets:
                logger.error(f"Item with id: {self.id} does not support changesets.")
                raise ValueError("This item does not support changesets.")
            if from_time is None:
                raise ValueError("from_time must be provided when querying with time filter.")
            if from_time == "AUDIT_MANAGER":
                if self._audit.enabled is not True:
                    logger.error("Audit manager is not enabled for this session.")
                    raise ValueError("Audit manager is not enabled for this session.")
                logger.debug(
                    f"Fetching changeset time filter from audit manager for item with id: {self.id}"
                )
                latest_audit_manager_record = self._audit.get_latest_request_for_item(
                    item_id=self.id,
                )
                from_time = latest_audit_manager_record.get("request_time")

            if from_time is None:
                # This means that AUDIT_MANAGER was requested but no record found
                # so we want to return all data
                logger.debug(
                    f"No audit manager record found for item with id: {self.id}. Returning all data."
                )
                is_changeset_request = False
            elif to_time is None:
                to_time = datetime.utcnow().isoformat()
                logger.debug(
                    f"Fetching changeset time filter from {from_time} to {to_time} for item with id: {self.id}"
                )
                viewparams = f"from:{from_time};to:{to_time}"

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

        if out_sr is None:
            out_sr = self.data.crs.srid
        if is_changeset_request:
            type_name = f"{self.type}-{self.id}-changeset"
            request_type = "wfs-changeset"
        else:
            type_name = f"{self.type}-{self.id}"
            request_type = "wfs-query"

        query_details = download_wfs_data(
            url=self._wfs_url,
            api_key=self._session.api_key,
            typeNames=type_name,
            viewparams=viewparams,
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
            item_type=self.type,
            request_type=request_type,
            request_url=query_details.get("request_url", ""),
            request_method=query_details.get("request_method", ""),
            request_time=query_details.get("request_time", ""),
            request_headers=query_details.get("request_headers", ""),
            request_params=query_details.get("request_params", ""),
            response=query_details.get("response", ""),
        )

        return WFSResponse(
            geojson=query_details.get("response", {}),
            item=self,
            out_sr=out_sr,
            is_changeset=is_changeset_request,
        )


    def __str__(self) -> str:
        """
        Returns a user-friendly string representation of the vector item.

        Returns:
            str: A string describing the vector item.
        """

        return f"Item id: {self.id}, type: {self.type}, title: {self.title}"

    def __repr__(self) -> str:
        """
        Returns an unambiguous string representation of the VectorItem.

        Returns:
            str: Detailed string representation of the VectorItem.
        """
        return (
            f"VectorItem(id={self.id!r}, type={self.type!r}, title={self.title!r}, "
            f"kind={self.kind!r}, data={self.data!r})"
        )