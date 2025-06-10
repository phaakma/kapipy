import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union, Protocol, runtime_checkable

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
class VectorItemData (ItemData):
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
class BaseItem(Protocol):
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

    def __str__(self) -> None:
        """
        User friendly string of a base item.
        """

        return f'Item id: {self.id}, type_: {self.type_}, title: {self.title}'

@dataclass
class WFS:
    """Item is able to be queried."""

    def __post_init__(self):
        self._supports_changesets = None
        self.services_list = None

    @property
    def _wfs_url(self) -> str:
        """
        Returns the WFS URL for the item.

        Returns:
            str: The WFS URL associated with the item.
        """
        return f"{self._gis._service_url}wfs/"

    @property
    def supports_changesets(self) -> bool:
        """
        Returns whether the item supports changesets.

        Returns:
            bool: True if the item supports changesets, False otherwise.
        """
        if self._supports_changesets is None:
            logger.debug(f"Checking if item with id: {self.id} supports changesets")

            # fetch services list
            self.services_list = self._gis.get(self.services)

            self._supports_changesets = any(
                service.get("key") == "wfs-changesets" for service in self.services_list
            )

        return self._supports_changesets


