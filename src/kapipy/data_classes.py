import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from abc import ABC, abstractmethod
from .export import validate_export_params, request_export
from .job_result import JobResult
from .conversion import (
    get_data_type,
    sdf_to_single_polygon_geojson,
    gdf_to_single_polygon_geojson,
    arcgis_polygon_to_geojson,
)

logger = logging.getLogger(__name__)


@dataclass
class Ancestor:
    name: str
    slug: str
    key: str
    url: str


@dataclass
class Category:
    name: str
    slug: str
    key: str
    url: str
    ancestors: List[Ancestor]


@dataclass
class License:
    id: int
    title: str
    type_: str
    jurisdiction: str
    version: str
    url: str
    url_html: str
    url_fulltext: str


@dataclass
class Metadata:
    resource: Optional[str]
    native: Optional[str]
    iso: Optional[str]
    dc: Optional[str]


@dataclass
class Theme:
    logo: Optional[str]
    background_color: Optional[str]


@dataclass
class Site:
    url: str
    name: str


@dataclass
class Publisher:
    id: str
    name: str
    html_url: Optional[str]
    slug_for_url: Optional[str]
    theme: Optional[Theme]
    site: Optional[Site]
    url: str
    flags: Dict[str, Any]
    description: Optional[str]


@dataclass
class Group:
    id: int
    url: str
    name: str
    country: str
    org: str
    type_: str


@dataclass
class DocumentVersion:
    id: int
    url: str
    created_at: str
    created_by: Dict[str, Any]


@dataclass
class DocumentCategory:
    name: str
    slug: str
    key: str
    url: str
    ancestors: List[Any]


@dataclass
class DocumentLicense:
    id: int
    title: str
    type_: str
    jurisdiction: str
    version: str
    url: str
    url_html: str
    url_fulltext: str


@dataclass
class DocumentPublisher:
    id: str
    name: str
    html_url: Optional[str]
    slug_for_url: Optional[str]
    theme: Optional[Theme]
    site: Optional[Site]
    url: str
    flags: Dict[str, Any]
    description: Optional[str]


@dataclass
class Document:
    id: int
    title: str
    url: str
    type_: str
    thumbnail_url: Optional[str]
    first_published_at: Optional[str]
    published_at: Optional[str]
    user_capabilities: List[str]
    group: Optional[Group]
    url_html: Optional[str]
    url_download: Optional[str]
    extension: Optional[str]
    file_size: Optional[int]
    file_size_formatted: Optional[str]
    featured_at: Optional[str]
    user_permissions: List[str]
    description: Optional[str]
    description_html: Optional[str]
    publisher: Optional[DocumentPublisher]
    published_version: Optional[str]
    latest_version: Optional[str]
    this_version: Optional[str]
    data: Dict[str, Any]
    categories: List[DocumentCategory]
    tags: List[str]
    license: Optional[DocumentLicense]
    metadata: Optional[Any]
    attached: Optional[str]
    settings: Dict[str, Any]
    num_views: Optional[int]
    num_downloads: Optional[int]
    url_canonical: Optional[str]
    is_starred: Optional[bool]
    version: Optional[DocumentVersion]
    public_access: Optional[str]


@dataclass
class Attachment:
    id: int
    url: str
    url_download: str
    url_html: str
    document: Document


@dataclass
class CRS:
    id: str
    url: str
    name: str
    kind: str
    unit_horizontal: str
    unit_vertical: str
    url_external: str
    component_horizontal: Optional[Any]
    component_vertical: Optional[Any]
    srid: int


@dataclass
class FieldDef:
    name: str
    type_: str


@dataclass
class ChangeSummarySchema:
    added: List[Any]
    changed: List[Any]
    removed: List[Any]
    srid_changed: bool
    geometry_type_changed: bool
    primary_keys_changed: bool


@dataclass
class ChangeSummary:
    inserted: int
    updated: int
    deleted: int
    schema_changes: ChangeSummarySchema


@dataclass
class SourceSummary:
    formats: List[str]
    types: List[str]


@dataclass
class ImportLog:
    invalid_geometries: int
    messages: int
    url: str


@dataclass
class ExportFormat:
    name: str
    mimetype: str


@dataclass
class ItemData:
    storage: Optional[str]
    datasources: Optional[str]
    fields: List[FieldDef]
    encoding: Optional[str]
    primary_key_fields: Optional[List[str]]
    source_revision: Optional[int]
    omitted_fields: List[Any]
    tile_revision: int
    feature_count: int
    datasource_count: int
    change_summary: Optional[ChangeSummary]
    source_summary: Optional[str]
    import_started_at: str
    import_ended_at: str
    import_log: ImportLog
    import_version: str
    update_available: bool
    sample: Optional[str]
    raster_resolution: Optional[Any]
    empty_geometry_count: int
    has_z: bool
    export_formats: List[ExportFormat]


@dataclass
class VectorItemData(ItemData):
    crs: CRS
    geometry_field: str
    geometry_type: str
    extent: Dict[str, Any]


@dataclass
class ServiceTemplateUrl:
    name: str
    service_url: str


@dataclass
class Service:
    id: str
    authority: str
    key: str
    short_name: str
    label: Optional[str]
    auth_method: List[str]
    auth_scopes: List[str]
    domain: str
    template_urls: List[ServiceTemplateUrl]
    capabilities: List[Any]
    permissions: str
    advertised: bool
    user_capabilities: List[str]
    enabled: bool


@dataclass
class RepositorySettings:
    feedback_enabled: bool


@dataclass
class Repository:
    id: str
    full_name: str
    url: str
    clone_location_ssh: str
    clone_location_https: str
    type_: str
    title: str
    first_published_at: str
    published_at: Optional[str]
    settings: RepositorySettings
    user_capabilities: List[str]
    user_permissions: List[str]


@dataclass
class Geotag:
    country_code: str
    state_code: Optional[str]
    name: str
    key: str


@dataclass
class Version:
    id: int
    url: str
    status: str
    created_at: str
    reference: str
    progress: float
    data_import: bool


@dataclass
class BaseItem(ABC):
    """
    Base class for Items. Should not be created directly. Instead, use the ContentManager
    to return an Item.
    """

    id: int
    url: str
    type_: str
    title: str
    description: str
    data: ItemData
    services: str
    kind: str
    categories: List[Any]
    tags: List[str]
    created_at: str
    license: Any
    metadata: Any
    num_views: int
    num_downloads: int

    def __post_init__(self):
        self._session=None
        self._audit=None
        self._content=None
        self._raw_json=None
        self._supports_changesets=None
        self.services_list=None
        self._supports_wfs=None

    def attach_resources(
            self, 
            session: "SessionManager"=None, 
            audit: "AuditManager"=None,
            content: "ContentManager"=None
            ):
        self._session = session
        self._audit = audit
        self._content = content

    @abstractmethod
    def __str__(self) -> None:
        """
        User friendly string of a base item.
        """

        return f"Item id: {self.id}, type_: {self.type_}, title: {self.title}"

    @property
    def supports_changesets(self) -> bool:
        """
        Returns whether the item supports changesets.

        Returns:
            bool: True if the item supports changesets, False otherwise.
        """
        if self._supports_changesets is None:
            logger.debug(f"Checking if item with id: {self.id} supports changesets")

            if self.services_list is None:
                self.services_list = self._session.get(self.services)

            self._supports_changesets = any(
                service.get("key") == "wfs-changesets" for service in self.services_list
            )

        return self._supports_changesets

    @property
    def _wfs_url(self) -> str:
        """
        Returns the WFS URL for the item.

        Returns:
            str: The WFS URL associated with the item.
        """

        if self._supports_wfs is None:
            if self.services_list is None:
                self.services_list = self._session.get(self.services)
            self._supports_wfs = any(
                service.get("key") == "wfs" for service in self.services_list
            )

        if self._supports_wfs is False:
            return None

        return f"{self._session.service_url}wfs/"

    def export(
        self,
        export_format: str,
        out_sr: int = None,
        filter_geometry: Optional[
            Union[dict, "gpd.GeoDataFrame", "pd.DataFrame"]
        ] = None,
        poll_interval: int = None,
        timeout: int = None,
        **kwargs: Any,
    ) -> JobResult:
        """
        Exports the item in the specified format.

        Parameters:
            export_format (str): The format to export the item in.
            out_sr (int, optional): The coordinate reference system code to use for the export.
            filter_geometry (dict or gpd.GeoDataFrame or pd.DataFrame, optional): The filter_geometry to use for the export. Should be a GeoJSON dictionary, GeoDataFrame, or SEDF.
            poll_interval (int, optional): The interval in seconds to poll the export job status. Default is 10 seconds.
            timeout (int, optional): The maximum time in seconds to wait for the export job to complete. Default is 600 seconds (10 minutes).
            **kwargs: Additional parameters for the export request.

        Returns:
            JobResult: A JobResult instance containing the export job details.

        Raises:
            ValueError: If export validation fails.
        """

        logger.debug(f"Exporting item with id: {self.id} in format: {export_format}")

        crs = None
        if self.kind in ["vector"]:
            out_sr = out_sr if out_sr is not None else self.data.crs.srid
            crs = f"EPSG:{out_sr}"
            data_type = get_data_type(filter_geometry)
            if data_type == "unknown":
                filter_geometry = None
            elif data_type == "sdf":
                filter_geometry = sdf_to_single_polygon_geojson(filter_geometry)
            elif data_type == "gdf":
                filter_geometry = gdf_to_single_polygon_geojson(filter_geometry)
            elif data_type == "ARCGIS_POLYGON":
                filter_geometry = arcgis_polygon_to_geojson(filter_geometry)

        export_format = self._resolve_export_format(export_format)

        validate_export_request = self._validate_export_request(
            export_format,
            crs=crs,
            filter_geometry=filter_geometry,
            **kwargs,
        )

        if not validate_export_request:
            raise ValueError(
                f"Export validation failed for item with id: {self.id} in format: {export_format}"
            )

        export_details = request_export(
            self._session.api_url,
            self._session.api_key,
            self.id,
            self.type_,
            self.kind,
            export_format,
            crs=crs,
            filter_geometry=filter_geometry,
            **kwargs,
        )

        job_result = JobResult(
            export_details.get("response"),
            self._session,
            poll_interval=poll_interval,
            timeout=timeout,
        )
        self._content.jobs.append(job_result)
        self._audit.add_request_record(
            item_id=self.id,
            item_kind=self.kind,
            item_type=self.type_,
            request_type="export",
            request_url=export_details.get("request_url", ""),
            request_method=export_details.get("request_method", ""),
            request_time=export_details.get("request_time", ""),
            request_headers=export_details.get("request_headers", ""),
            request_params=export_details.get("request_params", ""),
        )
        logger.debug(
            f"Export job created for item with id: {self.id}, job id: {job_result.id}"
        )
        return job_result

    def _validate_export_request(
        self,
        export_format: str,
        crs: str = None,
        filter_geometry: dict = None,
        **kwargs: Any,
    ) -> bool:
        """
        Validates the export request parameters for the item.

        Parameters:
            export_format (str): The format to export the item in.
            crs (str, optional): The coordinate reference system to use for the export.
            filter_geometry (dict, optional): The filter_geometry to use for the export. Should be a GeoJSON dictionary.
            **kwargs: Additional parameters for the export request.

        Returns:
            bool: True if the export request is valid, False otherwise.
        """

        export_format = self._resolve_export_format(export_format)

        # log out all the input parameters including kwargs
        logger.debug(
            f"Validating export request for item with id: {self.id}, {export_format=}, {crs=}, {filter_geometry=},  {kwargs=}"
        )

        return validate_export_params(
            self._session.api_url,
            self._session.api_key,
            self.id,
            self.type_,
            self.kind,
            export_format,
            crs,
            filter_geometry,
            **kwargs,
        )

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

        export_formats = self.data.export_formats

        for f in self.data.export_formats:
            if export_format in (f.name.lower(), f.mimetype.lower()):
                mimetype = f.mimetype

        if mimetype is None:
            raise ValueError(
                f"Export format {export_format} is not supported by this item. Refer supported formats using : itm.data.export_formats"
            )

        logger.debug(f"Resolved export format: {mimetype} from {export_format}")
        return mimetype
