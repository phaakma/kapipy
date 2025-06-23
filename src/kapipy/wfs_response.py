from .conversion import (
    geojson_to_gdf,
    geojson_to_sdf,
    json_to_df,
)

from .gis import has_geopandas, has_arcgis


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

    def __init__(self, geojson: dict, item: "BaseItem" = None, out_sr=None):
        """
        Initialize a WFSResponse instance.

        Args:
            geojson (dict): The raw GeoJSON data.
            item (BaseItem, optional): The associated item metadata.
            out_sr (Any, optional): The output spatial reference.
        """

        self._json = geojson
        self.item = item
        self.out_sr = out_sr
        self._df = None
        self._gdf = None
        self._sdf = None
        self.total_features = len(geojson["features"])

    @property
    def json(self) -> dict:
        """
        Get the raw GeoJSON data.

        Returns:
            dict: The raw GeoJSON data.
        """
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
            self._gdf = geojson_to_gdf(
                self.json, out_sr=self.out_sr, fields=self.item.data.fields
            )
        return self._gdf

    def __str__(self) -> None:
        """
        Return a user-friendly string representation of the WFSResponse.

        Returns:
            str: A string describing the WFSResponse.
        """

        return f"WFSResponse for item id: {self.item.id}, total feature count: {self.total_features}"
