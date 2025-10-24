import logging
import json

from .conversion import (
    geojson_to_gdf,
    geojson_to_sdf,
    json_to_df,
)

from .gis import has_geopandas, has_arcgis

logger = logging.getLogger(__name__)

class WFSResponse:
    """
    Represents a response from a WFS (Web Feature Service) request.

    Holds the raw GeoJSON data and provides properties and methods to convert
    the data into various dataframe formats (Pandas, GeoPandas, Spatially Enabled DataFrame).

    Attributes:
        _json (dict): The raw GeoJSON data.
        item (BaseItem, optional): The associated item metadata.
        out_sr (Any, optional): The output spatial reference.
        _df (pd.DataFrame or None): Cached Pandas DataFrame.
        _gdf (gpd.GeoDataFrame or None): Cached GeoPandas DataFrame.
        _sdf (SpatialDataFrame or None): Cached Spatially Enabled DataFrame.
        total_features (int): The number of features in the GeoJSON.
    """

    def __init__(self, geojson: dict | None, data_file_path: str | None, item: "BaseItem" = None, out_sr=None, is_changeset: bool = False):
        """
        Initialize a WFSResponse instance.

        Args:
            geojson (dict): The raw GeoJSON data.
            item (BaseItem, optional): The associated item metadata.
            out_sr (Any, optional): The output spatial reference.
        """

        self._json = geojson
        self._data_file_path = data_file_path
        self.item = item
        self.out_sr = out_sr
        self._df = None
        self._gdf = None
        self._sdf = None
        if geojson:
            self.total_features = len(geojson["features"])
        else:
            self.total_features = None
        self.is_changeset = is_changeset

    @property
    def json(self) -> dict:
        """
        Get the raw GeoJSON data.

        Returns:
            dict: The raw GeoJSON data.
        """
        if self._json is None and self._data_file_path:
            with open(self._data_file_path, "r", encoding="utf-8") as f:
                self._json = json.load(f)
        return self._json

    @property
    def df(self) -> "pd.DataFrame":
        """
        Convert the GeoJSON to a Pandas DataFrame.

        Returns:
            pd.DataFrame: The features as a Pandas DataFrame.

        Raises:
            Exception: If conversion fails.
        """
        if self._df is None:
            self._df = json_to_df(self.json, fields=self.item.data.fields)
        return self._df

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
                self.json,
                out_sr=self.out_sr,
                geometry_type=self.item.data.geometry_type,
                fields=self.item.data.fields,
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

        if self._gdf is None:
            if self.json is not None:
                j = self.json
            elif self._json is None and self._data_file_path:
                # this is a temporary implementation to read from file if json is not loaded
                # ideally, we pass a file path only when json is not available
                # and the helper function loads directly from disk
                # but at least this way the j variable goes out of scope after this block
                # and is garbage collected
                with open(self._data_file_path, "r", encoding="utf-8") as f:
                    j = json.load(f)
            else:
                raise ValueError("No GeoJSON data available for conversion to GeoDataFrame")
            self._gdf = geojson_to_gdf(
                j, out_sr=self.out_sr, fields=self.item.data.fields
            )
        return self._gdf

    def __str__(self) -> str:
        """
        Return a user-friendly string representation of the WFSResponse.

        Returns:
            str: A string describing the WFSResponse.
        """
        item_id = getattr(self.item, "id", None)
        return f"WFSResponse for item id: {item_id}, total feature count: {self.total_features}"

    def __repr__(self) -> str:
        """
        Return an unambiguous string representation of the WFSResponse.

        Returns:
            str: A detailed string representation of the WFSResponse.
        """
        item_id = getattr(self.item, "id", None)
        return (
            f"WFSResponse(item_id={item_id!r}, total_features={self.total_features}, "
            f"out_sr={self.out_sr!r})"
        )