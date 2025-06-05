import pandas as pd
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.geometry import mapping
from typing import Any, TYPE_CHECKING, Union
import logging
from kapipy.gis import has_geopandas, has_arcgis, has_arcpy

if TYPE_CHECKING:
    if has_geopandas:
        import geopandas as gpd
    if has_arcgis:
        import arcgis

logger = logging.getLogger(__name__)

def map_field_type(field_type: str) -> str:
    mapping = {
        "integer": "esriFieldTypeInteger",
        "float": "esriFieldTypeDouble",
        "numeric": "esriFieldTypeDouble",
        "string": "esriFieldTypeString",
        "date": "esriFieldTypeDate",
        "boolean": "esriFieldTypeSmallInteger",  # or esriFieldTypeInteger if needed
        "objectid": "esriFieldTypeOID",
        "guid": "esriFieldTypeGUID"
    }
    return mapping.get(field_type.lower(), "esriFieldTypeString")  # default fallback


def geojson_to_featureset(geojson, fields, wkid=4326) -> "arcgis.features.FeatureSet":
    """
    Converts a GeoJSON FeatureCollection or list of features into an ArcGIS FeatureSet.

    Args:
        geojson (dict or list): A GeoJSON FeatureCollection (dict with 'features') or a list of GeoJSON features.
        fields (list): A list of field definitions like [{'name': 'id', 'type': 'integer'}, ...].
        wkid (int): The well-known ID of the spatial reference system (e.g., 2193 for NZTM).

    Returns:
        arcgis.features.FeatureSet: An ArcGIS-compatible FeatureSet.
    """

    if not has_arcgis:
        raise ImportError("arcgis is not installed.")

    from arcgis.features import FeatureSet, Feature
    from arcgis.geometry import Geometry, SpatialReference
    import pandas as pd

    # Normalize input to a list of features
    if isinstance(geojson, dict) and "features" in geojson:
        features = geojson["features"]
    elif isinstance(geojson, list):
        features = geojson
    else:
        raise ValueError("geojson must be a FeatureCollection or list of features.")

    arcgis_fields = [
        {**f, "type": map_field_type(f["type"])}
        for f in fields
        if f["type"].lower() != "geometry"  # exclude geometry from field list
    ]


    # Infer geometry type from first feature
    geojson_type = features[0].get("geometry", {}).get("type")
    geometry_type_map = {
        "Point": "esriGeometryPoint",
        "MultiPoint": "esriGeometryMultipoint",
        "LineString": "esriGeometryPolyline",
        "Polygon": "esriGeometryPolygon",
    }
    geometry_type = geometry_type_map.get(geojson_type)
    if not geometry_type:
        raise ValueError(f"Unsupported geometry type: {geojson_type}")

    # Convert features
    arcgis_features = []
    for feature in features:
        geometry = feature.get("geometry")
        attributes = feature.get("properties", {})

        # ArcGIS expects the geometry dict to include spatial reference
        arcgis_geometry = Geometry({"spatialReference": {"wkid": wkid}, **geometry})

        arcgis_feature = Feature(geometry=arcgis_geometry, attributes=attributes)
        arcgis_features.append(arcgis_feature)

    # Construct FeatureSet
    return FeatureSet(
        features=arcgis_features,
        fields=arcgis_fields,
        geometry_type=geometry_type,
        spatial_reference=SpatialReference(wkid),
    )

def geojson_to_gdf(
    geojson: dict[str, Any] | list[dict[str, Any]],
    wkid: int,
    fields: list[dict[str, str]] | None = None,
) -> "gpd.GeoDataFrame":
    """
    Convert GeoJSON features to a GeoDataFrame with enforced data types.

    Parameters:
        geojson (dict or list): A GeoJSON FeatureCollection (dict) or a list of GeoJSON feature dicts.
        wkid (int): The EPSG code for the coordinate reference system (e.g., 4326).
        fields (list[dict], optional): A list of dictionaries specifying field names and their desired data types.

    Returns:
        gpd.GeoDataFrame: A GeoDataFrame with the specified CRS and column types.

    Raises:
        ImportError: If geopandas is not installed.
        ValueError: If the geojson input is invalid.
    """

    logger.debug("Converting GeoJSON to GeoDataFrame...")
    if not has_geopandas:
        raise ImportError("geopandas is not installed.")
    import geopandas as gpd

    # if the geosjon is None, return an empty GeoDataFrame
    if geojson is None:
        logger.warning("Received None as geojson input, returning empty GeoDataFrame.")
        return gpd.GeoDataFrame(columns=[], geometry=[])

    # Extract features from a FeatureCollection if needed
    if isinstance(geojson, dict) and geojson.get("type") == "FeatureCollection":
        features = geojson.get("features", [])
    elif isinstance(geojson, list):
        features = geojson
    else:
        raise ValueError(
            "Invalid geojson input. Expected a FeatureCollection or list of features."
        )

    # Flatten properties and extract geometry
    records = []
    geometries = []
    for feature in features:
        props = feature.get("properties", {})
        geom = feature.get("geometry")
        records.append(props)
        geometries.append(shape(geom) if geom else None)

    # Create GeoDataFrame
    crs = f"EPSG:{wkid}"
    df = pd.DataFrame(records)
    gdf = gpd.GeoDataFrame(df, geometry=geometries, crs=crs)

    # Apply data type mapping
    if fields and False:
        for field in fields:
            col = field.get("name")
            dtype = field.get("type").lower()
            if dtype == "geometry":
                continue  # Skip geometry fields as they are already handled
            if col in gdf.columns:
                try:
                    if dtype in ["int", "bigint", "integer", "int32", "int64"]:
                        gdf[col] = (
                            pd.to_numeric(gdf[col], errors="coerce")
                            .fillna(0)
                            .astype("int32")
                        )
                    elif dtype in ["float", "double"]:
                        gdf[col] = pd.to_numeric(gdf[col], errors="coerce")
                    elif dtype in ["str", "string"]:
                        gdf[col] = gdf[col].astype(str)
                    elif dtype == "bool":
                        gdf[col] = gdf[col].astype(bool)
                    else:
                        logger.warning(
                            f"Unsupported data type '{dtype}' for column '{col}'. Skipping conversion."
                        )
                except Exception as e:
                    raise ValueError(
                        f"Failed to convert column '{col}' to {dtype}: {e}"
                    )
    return gdf


def geojson_to_sdf(
    geojson: dict[str, Any] | list[dict[str, Any]],
    wkid: int,
    fields: list[dict[str, str]] | None = None,
) -> "arcgis.features.GeoAccessor":
    """
    Convert GeoJSON features to a Spatially Enabled DataFrame (SEDF) with enforced data types.

    Parameters:
        geojson (dict or list): A GeoJSON FeatureCollection (dict) or a list of GeoJSON feature dicts.
        wkid (int): The EPSG code for the coordinate reference system (e.g., 4326).
        fields (list[dict], optional): A list of dictionaries specifying field names and their desired data types.

    Returns:
        arcgis.features.GeoAccessor: A Spatially Enabled DataFrame with the specified CRS and column types.

    Raises:
        ImportError: If arcgis is not installed.
        ValueError: If the geojson input is invalid.
    """

    # if the geojson is None, return an empty SEDF
    if geojson is None:
        logger.warning("Received None as geojson input, returning empty SEDF.")
        return pd.DataFrame()

    if not has_arcgis:
        raise ImportError("arcgis is not installed.")

    import pandas as pd
    from arcgis.features import GeoAccessor, GeoSeriesAccessor
    from arcgis.geometry import SpatialReference

    logger.debug(f"{wkid=}")
    feature_set = geojson_to_featureset(geojson=geojson, fields=fields, wkid=wkid)
    sdf = feature_set.sdf

    return sdf

def json_to_df(
    json: dict[str, Any] | list[dict[str, Any]],
    fields: list[dict[str, str]] | None = None,
) -> pd.DataFrame:
    """
    Convert JSON features to a DataFrame with enforced data types.

    Paramters:
        json (dict or list): A JSON FeatureCollection (dict) or a list of JSON feature dicts.
        fields (list[dict], optional): A list of dictionaries specifying field names and their desired data types.

    Returns:
        pd.DataFrame: A DataFrame with the specified column types.

    Raises:
        ValueError: If the json input is invalid.
    """

    logger.debug("Converting JSON to DataFrame...")

    # Extract features from a FeatureCollection if needed
    if isinstance(json, dict) and json.get("type") == "FeatureCollection":
        features = json.get("features", [])
    elif isinstance(json, list):
        features = json
    else:
        raise ValueError(
            "Invalid json input. Expected a FeatureCollection or list of features."
        )

    # Flatten properties and extract geometry
    records = []
    for feature in features:
        props = feature.get("properties", {})
        records.append(props)
    df = pd.DataFrame(records)

    # Apply data type mapping
    if fields and False:
        for field in fields:
            col = field.get("name")
            dtype = field.get("type").lower()
            if col in df.columns:
                try:
                    if dtype in ["int", "bigint", "integer", "int32", "int64"]:
                        df[col] = (
                            pd.to_numeric(df[col], errors="coerce")
                            .fillna(0)
                            .astype("int32")
                        )
                    elif dtype in ["float", "double"]:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                    elif dtype in ["str", "string"]:
                        df[col] = df[col].astype(str)
                    elif dtype == "bool":
                        df[col] = df[col].astype(bool)
                    else:
                        logger.warning(
                            f"Unsupported data type '{dtype}' for column '{col}'. Skipping conversion."
                        )
                except Exception as e:
                    raise ValueError(
                        f"Failed to convert column '{col}' to {dtype}: {e}"
                    )

    return df


def sdf_or_gdf_to_single_polygon_geojson(
    df: Union["gpd.GeoDataFrame", "pd.DataFrame"],
) -> dict[str, Any] | None:
    """
    Convert a GeoDataFrame or SEDF to a single GeoJSON Polygon geometry object.

    Parameters:
        df (gpd.GeoDataFrame or arcgis.features.GeoAccessor): A GeoDataFrame or SEDF containing only Polygon geometries.

    Returns:
        dict: A GeoJSON Polygon geometry object.

    Raises:
        ValueError: If the DataFrame is empty or contains non-polygon geometries.
    """

    if df.empty:
        raise ValueError("sdf or gdf must contain at least one geometry.")

    data_type = get_data_type(df)
    if data_type == "sdf":
        if not all(g.lower() == "polygon" for g in df.spatial.geometry_type):
            raise ValueError("All geometries must be of type 'polygon'.")
        if df.spatial.sr.wkid != 4326:
            df.spatial.project({"wkid": 4326})
        geometries = df[df.spatial.name]
        shapes = [shape(geom) for geom in geometries]
        unioned = unary_union(shapes)
        # Convert the Shapely geometry to GeoJSON format
        ext = mapping(unioned)
        return ext

    elif data_type == "gdf":
        if not all(df.geometry.type == "Polygon"):
            raise ValueError("GeoDataFrame must contain only Polygon geometries.")

        # convert crs to EPSG:4326 if not already
        if df.crs is None:
            df.set_crs(epsg=4326, inplace=True)
        elif df.crs.to_epsg() != 4326:
            df = df.to_crs(epsg=4326)

        # Union all geometries into a single geometry
        single_geometry = df.unary_union
        if single_geometry.is_empty:
            raise ValueError("Resulting geometry is empty after union.")

        return single_geometry.__geo_interface__


def sdf_or_gdf_to_bbox(df: Any) -> str:
    """
    Convert a GeoDataFrame or SEDF to a bounding box string in EPSG:4326.

    Parameters:
        df (gpd.GeoDataFrame or arcgis.features.GeoAccessor): A GeoDataFrame or SEDF.

    Returns:
        str: Bounding box string in the format "minx,miny,maxx,maxy,EPSG:4326".

    Raises:
        ValueError: If the DataFrame is empty or does not contain valid geometries.
    """

    if df.empty:
        raise ValueError("sdf or gdf must contain at least one geometry.")

    data_type = get_data_type(df)
    if data_type == "sdf":
        if not df.spatial.geometry_type in ["polygon", "multipolygon"]:
            raise ValueError("sdf must contain polygon geometries.")
        if df.spatial.sr.wkid != 4326:
            df.spatial.project({"wkid": 4326})
        return ",".join(map(str, df.spatial.full_extent))

    elif data_type == "gdf":
        if not all(df.geometry.type.isin(["Polygon", "MultiPolygon"])):
            raise ValueError(
                "gdf must contain only Polygon or MultiPolygon geometries."
            )
        if df.crs is None:
            df.set_crs(epsg=4326, inplace=True)
        elif df.crs.to_epsg() != 4326:
            df = df.to_crs(epsg=4326)
        bounds = df.total_bounds  # returns (minx, miny, maxx, maxy)
        return f"{bounds[0]},{bounds[1]},{bounds[2]},{bounds[3]},EPSG:4326"


def get_data_type(obj: Union[str, "gpd.GeoDataFrame", "pd.DataFrame"]) -> str:
    """
    Determines if the object is a string, a GeoDataFrame (gdf), or an ArcGIS SEDF (sdf).

    Parameters:
        obj: The object to check.

    Returns:
        str: "str" if string, "gdf" if GeoDataFrame, "sdf" if ArcGIS SEDF, or "unknown" if none match.
    """

    # Check for string
    if isinstance(obj, str):
        return "str"

    # Check for GeoDataFrame
    if has_geopandas:
        try:
            import geopandas as gpd

            if isinstance(obj, gpd.GeoDataFrame):
                return "gdf"
        except ImportError:
            pass

    # Check for ArcGIS SEDF (Spatially Enabled DataFrame)
    if has_arcgis:
        try:
            import pandas as pd
            from arcgis.features import GeoAccessor

            # SEDF is a pandas.DataFrame with a _spatial accessor
            # pandas.core.frame.DataFrame
            if isinstance(obj, pd.DataFrame) and hasattr(obj, "spatial"):
                return "sdf"
        except ImportError:
            pass

    return "unknown"


def get_default_output_format() -> str:
    """
    Return a default output format based on which packages are available.

    Returns:
        str: "sdf" if arcgis is installed, "gdf" if geopandas is installed, otherwise "json".
    """

    if has_arcgis:
        return "sdf"
    if has_geopandas:
        return "gdf"
    return "json"
