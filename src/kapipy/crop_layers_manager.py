import copy
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from dacite import from_dict, Config
import logging

from .conversion import (
    geojson_to_gdf,
    geojson_to_sdf,
    json_to_df,
)

from .gis import has_geopandas, has_arcgis

logger = logging.getLogger(__name__)

@dataclass
class CropFeature:
    """
    Represents a single crop feature.
    
    Attributes:
        id (int): The feature's unique identifier.
        name (str): The feature's name.
        geometry (dict): The feature's geometry in GeoJSON format.
        url (str): The API URL for this crop feature.
    """

    id: int
    name: str
    url: str
    geometry: dict

    def __post_init__(self):
        self._sdf = None
        self._gdf = None

    @property
    def geojson(self):
        return {
            "properties": {
                "id": self.id,
                "name": self.name,
                "url": self.url
            },
            "geometry": self.geometry
        }
        
    @property
    def sdf(self) -> "pd.DataFrame":
        """
        Convert the GeoJSON to a Spatially Enabled DataFrame (ArcGIS SEDF).

        Requires the arcgis package to be installed.

        Returns:
            SpatialDataFrame: The features as a Spatially Enabled DataFrame.

        Raises:
            ValueError: If the arcgis package is not installed.
            Exception: If conversion fails.
        """

        if not has_arcgis:
            raise ValueError("Arcgis is not installed")

        if self._sdf is None:
            self._sdf = geojson_to_sdf(
                [self.geojson],
                out_sr=4326,
                geometry_type=self.geometry.get("type")
            )
        return self._sdf

    @property
    def gdf(self) -> "gpd.GeoDataFrame":
        """
        Convert the GeoJSON to a GeoPandas DataFrame.

        Requires the geopandas package to be installed.

        Returns:
            gpd.GeoDataFrame: The features as a GeoPandas DataFrame.

        Raises:
            ValueError: If the geopandas package is not installed.
            Exception: If conversion fails.
        """

        if not has_geopandas:
            raise ValueError(f"Geopandas is not installed")

        logger.info(self.geometry)

        if self._gdf is None:
            self._gdf = geojson_to_gdf(
                [self.geojson], out_sr=4326,
            )
        return self._gdf

    def __repr__(self):
        return f"<CropFeature id={self.id} name={self.name} url={self.url}>"

@dataclass
class CropFeaturesManager:
    """
    Manages crop features for a specific crop layer.
    """
    id: int
    name: str
    url: str
    _session: Any = field(default=None, repr=False, compare=False, init=False)

    def __post_init__(self):
        self._features = None    

    def _fetch_features(self):
        data = self._session.get(self.features_url)

        self._features = [
            from_dict(data_class=CropFeature, data=_data)
            for _data in data
        ]

    def all(self):
        """
        Returns a list of all crop features.
        """
        if self._features is None:
            self._fetch_features()
        return self._features

    def get(self):
        """
        Get a crop feature by id.
        """
        data = self._session.get(self.url)
        return from_dict(data_class=CropFeature, data=data)

    def find_item(self, name):
        """
        Find a crop feature by name (case-insensitive, exact match).

        Args:
            name (str): The name to search for.

        Returns:
            CropFeature or None: The matching feature, or None if not found.
        """
        name = name.lower()
        for feat in self.all():
            if feat.name.lower() == name:
                return feat
        return None

    def __getitem__(self, key):
        """
        Access a crop feature by ID (int) or name (str).
        """
        if isinstance(key, int):
            for feat in self.all():
                if feat.id == key:
                    return feat
        elif isinstance(key, str):
            return self.find(key)
        raise KeyError(f"Crop feature not found: {key}")

    def refresh(self):
        """
        Refresh the crop features from the API.
        """
        self._features = None
        self._fetch_features()

    def __iter__(self):
        return iter(self.all())

    def __repr__(self):
        return f"<CropFeaturesManager id={self.id} name={self.name} url={self.url}>"

@dataclass
class CropLayer:
    """
    Represents a single crop layer.
    """
    id: int
    name: str
    url: str
    features: str
    extent: dict
    source_layer: str
    _session: Any = field(default=None, repr=False, compare=False, init=False)

    def __post_init__(self):
        self._features = None

    def _fetch_features(self):
        data = self._session.get(self.features)

        logger.info(data)
        for d in data:
            d["_session"] = self._session

        self._features = [
            from_dict(data_class=CropFeaturesManager, data=_data)
            for _data in data
        ]


    def all(self):
        """
        Returns a list of all crop features.
        """
        if self._features is None:
            self._fetch_features()
        return self._features

    def get(self, id):
        """
        Get a crop feature manager by id.
        """
        for layer in self.all():
            if layer.id == id:
                return layer
        return None

    def find(self, name):
        """
        Find a feature manager by name (case-insensitive, exact match).

        Args:
            name (str): The name to search for.

        Returns:
            CropFeatureManager or None: The matching layer, or None if not found.
        """
        name = name.lower()
        for layer in self.all():
            if layer.name.lower() == name:
                return layer
        return None

    def filter_items(self, search: str) -> list[dict]:
        """
        Filter the list of feature managers by name (case-insensitive).
        """
        return [item for item in self.all() if search.lower() in item.name.lower()]

    def __getitem__(self, key):
        """
        Access a crop layer by ID (int) or name (str).
        """
        if isinstance(key, int):
            for layer in self.all():
                if layer.id == key:
                    return layer
        elif isinstance(key, str):
            return self.find(key)
        raise KeyError(f"Crop layer not found: {key}")

    def refresh(self):
        """
        Refresh the crop layers from the API.
        """
        self._features = None
        self._fetch_features()

    def __iter__(self):
        return iter(self.all())

class CropLayersManager:
    """
    Manages all crop layers.
    """
    BASE_URL = "https://data.linz.govt.nz/services/api/v1.x/exports/croplayers/"

    def __init__(self, session: "SessionManager", base_url=None):
        self._session=session
        self.base_url = base_url or self.BASE_URL
        self._layers = None

    def _fetch_layers(self):
        data = self._session.get(self.base_url)
        for d in data:
            d["_session"] = self._session

        self._layers = [
            from_dict(data_class=CropLayer, data=_data)
            for _data in data
        ]

    def all(self):
        """
        Returns a list of all crop layers.
        """
        if self._layers is None:
            self._fetch_layers()
        return self._layers

    def get(self, id):
        """
        Get a crop layer by id.
        """
        for layer in self.all():
            if layer.id == id:
                return layer
        return None

    def find_item(self, name):
        """
        Find a crop layer by name (case-insensitive, exact match).

        Args:
            name (str): The name to search for.

        Returns:
            CropLayer or None: The matching layer, or None if not found.
        """
        name = name.lower()
        for layer in self.all():
            if layer.name.lower() == name:
                return layer
        return None

    def __getitem__(self, key):
        """
        Access a crop layer by ID (int) or name (str).
        """
        if isinstance(key, int):
            for layer in self.all():
                if layer.id == key:
                    return layer
        elif isinstance(key, str):
            return self.find(key)
        raise KeyError(f"Crop layer not found: {key}")

    def refresh(self):
        """
        Refresh the crop layers from the API.
        """
        self._layers = None
        self._fetch_layers()

    def __iter__(self):
        return iter(self.all())

    def __repr__(self):
        return f"<CropLayersManager url={self.base_url!r} count={len(self.all()) if self._layers else 0}>"