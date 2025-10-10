import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from abc import ABC, abstractmethod
import re
from .export import validate_export_params, request_export
from .job_result import JobResult
from .conversion import (
    get_data_type,
    sdf_to_single_polygon_geojson,
    gdf_to_single_polygon_geojson,
    arcgis_polygon_to_geojson,
    gdf_to_single_extent_geojson,
)

logger = logging.getLogger(__name__)


@dataclass
class Ancestor:
    name: str
    slug: str
    key: str
    url: str

    def __repr__(self):
        return f"Ancestor(name={self.name!r}, slug={self.slug!r}, key={self.key!r}, url={self.url!r})"

@dataclass
class Category:
    name: str
    slug: str
    key: str
    url: str
    ancestors: List[Ancestor]

    def __repr__(self):
        return f"Category(name={self.name!r}, slug={self.slug!r}, key={self.key!r}, url={self.url!r})"

@dataclass
class License:
    id: int
    title: str
    type: str
    jurisdiction: str
    version: str
    url: str
    url_html: str
    url_fulltext: str

    def __repr__(self):
        return f"License(id={self.id!r}, title={self.title!r}, type={self.type!r}, version={self.version!r})"

@dataclass
class Metadata:
    resource: Optional[str]
    native: Optional[str]
    iso: Optional[str]
    dc: Optional[str]

    def __repr__(self):
        return f"Metadata(resource={self.resource!r}, native={self.native!r}, iso={self.iso!r}, dc={self.dc!r})"

@dataclass
class Theme:
    logo: Optional[str]
    background_color: Optional[str]

    def __repr__(self):
        return f"Theme(logo={self.logo!r}, background_color={self.background_color!r})"

@dataclass
class Site:
    url: str
    name: str

    def __repr__(self):
        return f"Site(url={self.url!r}, name={self.name!r})"

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

    def __repr__(self):
        return f"Publisher(id={self.id!r}, name={self.name!r}, url={self.url!r})"

@dataclass
class Group:
    id: int
    url: str
    name: str
    country: str
    org: str
    type: str

    def __repr__(self):
        return f"Group(id={self.id!r}, name={self.name!r}, org={self.org!r}, type={self.type!r})"

@dataclass
class DocumentVersion:
    id: int
    url: str
    created_at: str
    created_by: Dict[str, Any]

    def __repr__(self):
        return f"DocumentVersion(id={self.id!r}, url={self.url!r}, created_at={self.created_at!r})"

@dataclass
class DocumentCategory:
    name: str
    slug: str
    key: str
    url: str
    ancestors: List[Any]

    def __repr__(self):
        return f"DocumentCategory(name={self.name!r}, slug={self.slug!r}, key={self.key!r}, url={self.url!r})"

@dataclass
class DocumentLicense:
    id: int
    title: str
    type: str
    jurisdiction: str
    version: str
    url: str
    url_html: str
    url_fulltext: str

    def __repr__(self):
        return f"DocumentLicense(id={self.id!r}, title={self.title!r}, type={self.type!r}, version={self.version!r})"

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

    def __repr__(self):
        return f"DocumentPublisher(id={self.id!r}, name={self.name!r}, url={self.url!r})"

@dataclass
class Document:
    id: int
    title: str
    url: str
    type: str
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

    def __repr__(self):
        return f"Document(id={self.id!r}, title={self.title!r}, type={self.type!r})"

@dataclass
class Attachment:
    id: int
    url: str
    url_download: str
    url_html: str
    document: Document

    def __repr__(self):
        return f"Attachment(id={self.id!r}, url={self.url!r})"

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

    def __repr__(self):
        return f"CRS(id={self.id!r}, name={self.name!r}, srid={self.srid!r})"

@dataclass
class FieldDef:
    name: str
    type: str

    def __repr__(self):
        return f"FieldDef(name={self.name!r}, type={self.type!r})"

@dataclass
class ChangeSummarySchema:
    added: List[Any]
    changed: List[Any]
    removed: List[Any]
    srid_changed: bool
    geometry_type_changed: bool
    primary_keys_changed: bool

    def __repr__(self):
        return f"ChangeSummarySchema(added={self.added!r}, changed={self.changed!r}, removed={self.removed!r})"
@dataclass
class ChangeSummary:
    inserted: int
    updated: int
    deleted: int
    schema_changes: ChangeSummarySchema

    def __repr__(self):
        return f"ChangeSummary(inserted={self.inserted!r}, updated={self.updated!r}, deleted={self.deleted!r})"

@dataclass
class SourceSummary:
    formats: List[str]
    types: List[str]

    def __repr__(self):
        return f"SourceSummary(formats={self.formats!r}, types={self.types!r})"

@dataclass
class ImportLog:
    invalid_geometries: int
    messages: int
    url: str

    def __repr__(self):
        return f"ImportLog(invalid_geometries={self.invalid_geometries!r}, url={self.url!r})"

@dataclass
class ExportFormat:
    name: str
    mimetype: str

    def __repr__(self):
        return f"ExportFormat(name={self.name!r}, mimetype={self.mimetype!r})"

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

    def __repr__(self):
        return f"ItemData(fields={self.fields!r}, feature_count={self.feature_count!r})"

@dataclass
class VectorItemData(ItemData):
    crs: CRS
    geometry_field: str
    geometry_type: str
    extent: Dict[str, Any]

    def __repr__(self):
        return f"VectorItemData(crs={self.crs!r}, geometry_field={self.geometry_field!r}, geometry_type={self.geometry_type!r})"

@dataclass
class ServiceTemplateUrl:
    name: str
    service_url: str

    def __repr__(self):
        return f"ServiceTemplateUrl(name={self.name!r}, service_url={self.service_url!r})"

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

    def __repr__(self):
        return f"Service(id={self.id!r}, key={self.key!r}, domain={self.domain!r}, enabled={self.enabled!r})"

@dataclass
class RepositorySettings:
    feedback_enabled: bool

    def __repr__(self):
        return f"RepositorySettings(feedback_enabled={self.feedback_enabled!r})"

@dataclass
class Repository:
    id: str
    full_name: str
    url: str
    clone_location_ssh: str
    clone_location_https: str
    type: str
    title: str
    first_published_at: str
    published_at: Optional[str]
    settings: RepositorySettings
    user_capabilities: List[str]
    user_permissions: List[str]

    def __repr__(self):
        return f"Repository(id={self.id!r}, full_name={self.full_name!r}, type={self.type!r})"

@dataclass
class Geotag:
    country_code: str
    state_code: Optional[str]
    name: str
    key: str

    def __repr__(self):
        return f"Geotag(country_code={self.country_code!r}, name={self.name!r}, key={self.key!r})"

@dataclass
class Version:
    id: int
    url: str
    status: str
    created_at: str
    reference: str
    progress: float
    data_import: bool

    def __repr__(self):
        return f"Version(id={self.id!r}, status={self.status!r}, reference={self.reference!r})"

@dataclass
class BaseItem(ABC):
    """
    Base class for Items. Should not be created directly. Instead, use the ContentManager
    to return an Item.
    """

    id: int
    url: str
    type: str
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
        """
        Initializes internal attributes after dataclass initialization.
        """
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
        """
        Attaches session, audit, and content manager resources to the item.

        Parameters:
            session (SessionManager, optional): The session manager to attach.
            audit (AuditManager, optional): The audit manager to attach.
            content (ContentManager, optional): The content manager to attach.
        """
        self._session = session
        self._audit = audit
        self._content = content

    @abstractmethod
    def __str__(self) -> None:
        """
        Returns a user-friendly string representation of the item.

        Returns:
            str: A string describing the item.
        """
        return f"Item id: {self.id}, type: {self.type}, title: {self.title}"


    @property
    def feature_class_name(self) -> str:
        """
        Return the feature class name that would be used in an export to file geodatabase request.
        
        Replace any non-alphanumeric characters with underscore
        This seems to be the Koordinates method for setting the feature class names

        NOTE: This logic is observed from running exports only and does not appear to be documented
        anywhere by Koordinates.  
        """

        return re.sub(r'[^0-9A-Za-z]', '_', self.title)

    @property 
    def fgb_name(self) -> str:
        """
        Return the file geodatabase name that would be used in an export to file geodatabase request.

        NOTE: This logic is observed from running exports only and does not appear to be documented
        anywhere by Koordinates.

        """

        # Remove parentheses and commas completely
        cleaned = re.sub(r"[(),]", "", self.title)
        
        # Convert scale "1:50k" to "150k" by removing colon
        cleaned = re.sub(r"(\d):(\d+k)", r"\1\2", cleaned)
        
        # Replace any remaining non-alphanumeric characters (including spaces) with dash
        cleaned = re.sub(r"[^0-9a-zA-Z]+", "-", cleaned)
        
        # Remove leading/trailing dashes and lowercase
        return f"{cleaned.strip('-').lower()}.gdb"


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
        bbox_geometry: Union["gpd.GeoDataFrame", "pd.DataFrame"] = None,
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
            timeout (int, optional): The maximum time in seconds to wait for the export job to complete.
            **kwargs: Additional parameters for the export request.

        Returns:
            JobResult: A JobResult instance containing the export job details.

        Raises:
            ValueError: If export validation fails.
        """

        logger.debug(f"Exporting item with id: {self.id} in format: {export_format}")

        crs = None
        if self.kind in ["vector"]:
            if bbox_geometry is not None and filter_geometry is not None:
                raise ValueError(
                    f"Cannot process both a bbox_geometry and filter_geometry together."
                )

            out_sr = out_sr if out_sr is not None else self.data.crs.srid
            crs = f"EPSG:{out_sr}"

            ## Since a bbox_geometry ends up as a Polygon with four points anyway, we can just convert  
            ## the bbox_geometry to the necessary format and assign to the filter_geometry variable
            ## and it will get processed exactly the same.  

            if bbox_geometry is not None:
                data_type = get_data_type(bbox_geometry)
                if data_type == "unknown":
                    filter_geometry = None              
                elif data_type == "sdf":
                    filter_geometry = arcgis_polygon_to_geojson(bbox_geometry.spatial.bbox)
                elif data_type == "gdf":
                    filter_geometry = gdf_to_single_extent_geojson(bbox_geometry)
                elif data_type == "ARCGIS_POLYGON":
                    filter_geometry = arcgis_polygon_to_geojson(bbox_geometry)

            elif filter_geometry is not None:
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
            self.type,
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
            item_type=self.type,
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
            self.type,
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

    def __repr__(self):
        return f"BaseItem(id={self.id!r}, type={self.type!r}, title={self.title!r}, kind={self.kind!r})"