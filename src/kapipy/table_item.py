from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from .job_result import JobResult
from .data_classes import BaseItem
from .wfs_response import WFSResponse  
from .wfs_utils import download_wfs_data

logger = logging.getLogger(__name__)


@dataclass
class TableItem(BaseItem):
    """
    Represents a table item in the GISK content system.

    Inherits from BaseItem and provides methods for querying and retrieving changesets via WFS.
    """

    def query(
        self,
        *,
        from_time: str = None,
        to_time: str = None,
        cql_filter: str = None,
        out_fields: str | list[str] = None,
        result_record_count: int = None,
        **kwargs: Any
        ) -> dict:

        """
        Executes a WFS query on the item and returns the result as JSON.

        Parameters:
            cql_filter (str, optional): The CQL filter to apply to the query.
            **kwargs: Additional parameters for the WFS query.

        Returns:
            dict: The result of the WFS query in JSON format.
        """
        logger.debug(f"Executing WFS query for item with id: {self.id}")

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
            out_fields=out_fields,
            result_record_count=result_record_count,
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
            is_changeset=is_changeset_request,
            )


    def __repr__(self) -> str:
        return (
            f"TableItem(id={self.id!r}, type={self.type!r}, title={self.title!r}, kind={self.kind!r})"
        )

    def __str__(self) -> str:
        """
        Returns a user-friendly string representation of the table item.

        Returns:
            str: A string describing the table item.
        """
        return f"Item id: {self.id}, type: {self.type}, title: {self.title}"
