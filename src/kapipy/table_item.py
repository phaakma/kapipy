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

    def query(self, cql_filter: str = None, **kwargs: Any) -> dict:
        """
        Executes a WFS query on the item and returns the result as JSON.

        Parameters:
            cql_filter (str, optional): The CQL filter to apply to the query.
            **kwargs: Additional parameters for the WFS query.

        Returns:
            dict: The result of the WFS query in JSON format.
        """
        logger.debug(f"Executing WFS query for item with id: {self.id}")

        query_details = download_wfs_data(
            url=self._wfs_url,
            api_key=self._session.api_key,
            typeNames=f"{self.type_}-{self.id}",
            cql_filter=cql_filter,
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

        return WFSResponse(query_details.get("response", {}), self)


    def changeset(
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

        query_details = download_wfs_data(
            url=self._wfs_url,
            api_key=self._session.api_key,
            typeNames=f"{self.type_}-{self.id}-changeset",
            viewparams=viewparams,
            cql_filter=cql_filter,
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

        return WFSResponse(query_details.get("response", {}), self)

    def __str__(self) -> None:
        """
        User friendly string of a base item.
        """

        return f"Item id: {self.id}, type_: {self.type_}, title: {self.title}"
