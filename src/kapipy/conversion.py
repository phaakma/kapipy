import pandas as pd
import json
import re
from dateutil.parser import parse as date_parse
from dataclasses import asdict
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.geometry import mapping
from typing import Any, TYPE_CHECKING, Union
import logging
from .gis import has_geopandas, has_arcgis, has_arcpy

if TYPE_CHECKING:
    if has_geopandas:
        import geopandas as gpd
    if has_arcgis:
        import arcgis

logger = logging.getLogger(__name__)

VALID_SPATIAL_RELATIONSHIPS = (
    "INTERSECTS",
    "WITHIN",
    "DISJOINT",
    "CONTAINS",
    "TOUCHES",
    "CROSSES",
    "OVERLAPS",
    "EQUALS",
)


def map_field_type(field_type: str) -> str:
    mapping = {
        "integer": "esriFieldTypeInteger",
        "float": "esriFieldTypeDouble",
        "numeric": "esriFieldTypeDouble",
        "string": "esriFieldTypeString",
        "date": "esriFieldTypeDate",
        "boolean": "esriFieldTypeSmallInteger",  # or esriFieldTypeInteger if needed
        "objectid": "esriFieldTypeOID",
        "guid": "esriFieldTypeGUID",
    }
    return mapping.get(field_type.lower(), "esriFieldTypeString")  # default fallback


def map_geometry_type(geom_type: str) -> str:
    mapping = {
        "Point": "esriGeometryPoint",
        "MultiPoint": "esriGeometryMultipoint",
        "LineString": "esriGeometryPolyline",
        "Polygon": "esriGeometryPolygon",
    }
    return mapping.get(geom_type, None)


def is_valid_date(val):
    if val is None:
        return True  # Accept nulls
    try:
        # Accept int/float as epoch
        if isinstance(val, (int, float)):
            return True
        # Try parsing as date string
        date_parse(str(val))
        return True
    except Exception:
        return False


def geojson_to_featureset(
    geojson: dict | list, geometry_type: str, fields: list["FieldDef"], out_sr: int = 4326
) -> "arcgis.features.FeatureSet":
    """
    Converts a GeoJSON FeatureCollection or list of features into an ArcGIS FeatureSet.

    Args:
        geojson (dict or list): A GeoJSON FeatureCollection (dict with 'features') or a list of GeoJSON features.
        fields (list): A list of field definitions like [{'name': 'id', 'type': 'integer'}, ...].
        out_sr (int): The well-known ID of the spatial reference system (e.g., 2193 for NZTM).

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

    # validate that any date fields can be parsed
    # If any value is not parseable, set the field type to string
    for field in fields:        
        if field.type_.lower() == "date":
            for feature in features:
                val = feature.get("properties", {}).get(field.name)
                if not is_valid_date(val):
                    # Set this field to string
                    logger.debug(
                        f"Data for date field '{field.name}' was unable to be parsed. Overriding field type to string."
                    )
                    field.type_ = "string"

                    break  # No need to check further for this field

    arcgis_fields = [
        {**asdict(f), "type": map_field_type(f.type_)}
        for f in fields
        if f.type_.lower() != "geometry"  # exclude geometry from field list
    ]

    # Convert features
    arcgis_features = []
    for feature in features:
        geometry = feature.get("geometry")
        attributes = feature.get("properties", {})

        # ArcGIS expects the geometry dict to include spatial reference
        arcgis_geometry = Geometry({"spatialReference": {"wkid": out_sr}, **geometry})

        arcgis_feature = Feature(geometry=arcgis_geometry, attributes=attributes)
        arcgis_features.append(arcgis_feature)

    # Construct FeatureSet
    return FeatureSet(
        features=arcgis_features,
        fields=arcgis_fields,
        geometry_type=geometry_type,
        spatial_reference=SpatialReference(out_sr),
    )


def geojson_to_gdf(
    geojson: dict[str, Any] | list[dict[str, Any]],
    out_sr: int,
    fields: list[dict[str, str]] | None = None,
) -> "gpd.GeoDataFrame":
    """
    Convert GeoJSON features to a GeoDataFrame with enforced data types.

    Parameters:
        geojson (dict or list): A GeoJSON FeatureCollection (dict) or a list of GeoJSON feature dicts.
        out_sr (int): The EPSG code for the coordinate reference system (e.g., 4326).
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
        logger.debug(geojson)
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
    crs = f"EPSG:{out_sr}"
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
    out_sr: int,
    geometry_type: str,
    fields: list["FieldDef"] | None = None,
) -> "arcgis.features.GeoAccessor":
    """
    Convert GeoJSON features to a Spatially Enabled DataFrame (SEDF) with enforced data types.

    Parameters:
        geojson (dict or list): A GeoJSON FeatureCollection (dict) or a list of GeoJSON feature dicts.
        out_sr (int): The EPSG code for the coordinate reference system (e.g., 4326).
        fields (list[FieldDef], optional): A list of dictionaries specifying field names and their desired data types.

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
    from .data_classes import FieldDef

    # If fields is None, infer fields from geojson properties
    if fields is None:
        # Normalize input to a list of features
        if isinstance(geojson, dict) and "features" in geojson:
            features = geojson["features"]
        elif isinstance(geojson, list):
            features = geojson
        else:
            raise ValueError("geojson must be a FeatureCollection or list of features.")
        # Collect all property keys and infer types as string (or improve as needed)
        if features:
            sample_props = features[0].get("properties", {})
            fields = [FieldDef(name=k, type_="string") for k in sample_props.keys()]
        else:
            fields = []

    logger.debug(f"{out_sr=}")
    feature_set = geojson_to_featureset(
        geojson=geojson, geometry_type=geometry_type, fields=fields, out_sr=out_sr
    )
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

def sdf_to_single_polygon_geojson(
    sdf: "pd.DataFrame"
) -> dict[str, Any] | None:

    if sdf.empty:
        raise ValueError("sdf must contain at least one geometry.")

    if sdf.spatial.sr.wkid != 4326:
        sdf.spatial.project({"wkid": 4326})

    geom = sdf_to_single_geometry(sdf)
    geo_json = geom.JSON  # this is Esri JSON
    return esri_json_to_geojson(geom.JSON, geom.geometry_type)

def arcgis_polygon_to_geojson(geom):
    geom = geom.project_as(4326)
    geo_json = geom.JSON  # this is Esri JSON
    return esri_json_to_geojson(geom.JSON, geom.geometry_type)

def gdf_to_single_polygon_geojson(
    gdf: "gpd.GeoDataFrame",
) -> dict[str, Any] | None:

    if gdf.empty:
        raise ValueError("gdf must contain at least one geometry.")

    if not all(gdf.geometry.type == "Polygon"):
        raise ValueError("GeoDataFrame must contain only Polygon geometries.")    

    # convert crs to EPSG:4326 if not already
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)

    # Union all geometries into a single geometry
    single_geometry = gdf.union_all()
    if single_geometry.is_empty:
        raise ValueError("Resulting geometry is empty after union.")

    import geopandas as gpd
    gdf_single = gpd.GeoDataFrame(geometry=[single_geometry], crs=gdf.crs)
    geojson_str = gdf_single.to_json(to_wgs84=True)
    return json.loads(geojson_str)['features'][0]['geometry']

def get_data_type(obj: Any) -> str:
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
            from arcgis.geometry import Polygon

            # SEDF is a pandas.DataFrame with a _spatial accessor
            # pandas.core.frame.DataFrame
            if isinstance(obj, pd.DataFrame) and hasattr(obj, "spatial"):
                return "sdf"
            if isinstance(obj, Polygon):
                return "ARCGIS_POLYGON"
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


def sdf_to_single_geometry(sdf: "pd.DataFrame") -> Any:
    """
    Convert a spatially enabled dataframe to a single geometry.
    """

    import pandas as pd
    from arcgis.features import GeoAccessor

    geoms = sdf[sdf.spatial.name]
    union_geom = geoms[0]
    for geom in geoms[1:]:
        union_geom = union_geom.union(geom)
    return union_geom


def esri_json_to_geojson(esri_json: dict, geom_type: str) -> dict:
    """
    Convert an Esri JSON geometry (Polygon, Polyline, Point, MultiPoint) to GeoJSON format.

    Parameters:
        esri_json (dict): The Esri JSON geometry dictionary.
        geom_type (str): The geometry type ("point", "multipoint", "polyline", "polygon")

    Returns:
        dict: The equivalent GeoJSON geometry dictionary.

    Raises:
        ValueError: If the geometry type is not supported or the input is invalid.
    """
    VALID_GEOM_TYPES = ("point", "multipoint", "polyline", "polygon")
    geom_type = geom_type.lower()

    if isinstance(esri_json, str):
        esri_json = json.loads(esri_json)

    if not isinstance(esri_json, dict) or geom_type not in VALID_GEOM_TYPES:
        raise ValueError("Invalid Esri JSON geometry.")

    if geom_type == "point":
        return {
            "type": "Point",
            "coordinates": [esri_json["x"], esri_json["y"]],
        }
    elif geom_type == "multipoint":
        return {
            "type": "MultiPoint",
            "coordinates": esri_json["points"],
        }
    elif geom_type == "polyline":
        # Esri JSON uses "paths" for polylines
        return {
            "type": "MultiLineString" if len(esri_json["paths"]) > 1 else "LineString",
            "coordinates": (
                esri_json["paths"]
                if len(esri_json["paths"]) > 1
                else esri_json["paths"][0]
            ),
        }
    elif geom_type == "polygon":
        # Esri JSON uses "rings" for polygons
        return {
            "type": "Polygon",
            "coordinates": esri_json["rings"],
        }
    else:
        raise ValueError(f"Unsupported geometry type: {geom_type}")


def bbox_gdf_into_cql_filter(
    gdf: "gpd.GeoDataFrame", geometry_field: str, srid: int, cql_filter: str = None
):
    """
    Construct cql_filter and bbox parameters from GeoDataFrame.
    """
    if not all(gdf.geometry.type.isin(["Polygon", "MultiPolygon"])):
        raise ValueError("gdf must contain only Polygon or MultiPolygon geometries.")
    if gdf.crs is None:
        gdf.set_crs(epsg=srid, inplace=True)
    elif gdf.crs.to_epsg() != srid:
        gdf = gdf.to_crs(epsg=srid)
    minX, minY, maxX, maxY = gdf.total_bounds
    bbox = f"bbox({geometry_field},{minY},{minX},{maxY},{maxX})"
    if cql_filter is None or cql_filter == "":
        cql_filter = bbox
    elif cql_filter > "":
        cql_filter = f"{bbox} AND {cql_filter}"
    return cql_filter


def geom_gdf_into_cql_filter(
    gdf: "gpd.GeoDataFrame",
    geometry_field: str,
    srid: int,
    spatial_rel: str = None,
    cql_filter: str = None,
):
    """
    Construct cql_filter and geometry filter parameters.
    """
    if spatial_rel is None:
        spatial_rel = "INTERSECTS"
    spatial_rel = spatial_rel.upper()
    if spatial_rel not in VALID_SPATIAL_RELATIONSHIPS:
        raise ValueError(f"Invalid spatial_rel parameter supplied: {spatial_rel}")

    if not all(gdf.geometry.type == "Polygon"):
        raise ValueError("GeoDataFrame must contain only Polygon geometries.")

    # convert crs to EPSG:4326 if not already
    if gdf.crs is None:
        gdf.set_crs(epsg=srid, inplace=True)
    elif gdf.crs.to_epsg() != srid:
        gdf = gdf.to_crs(epsg=srid)

    # Union all geometries into a single geometry
    single_geometry = gdf.union_all()
    if single_geometry.is_empty:
        raise ValueError("Resulting geometry is empty after union.")

    # wkt coordinate x,y pairs need to be reversed
    # Pattern to match coordinate pairs
    pattern = r"(-?\d+\.\d+)\s+(-?\d+\.\d+)"
    # Swap each (x y) to (y x)
    reversed_wkt = re.sub(pattern, r"\2 \1", single_geometry.wkt)

    spatial_filter = f"{spatial_rel}({geometry_field},{reversed_wkt})"

    if cql_filter is None or cql_filter == "":
        cql_filter = spatial_filter
    elif cql_filter > "":
        cql_filter = f"{spatial_filter} AND {cql_filter}"

    return cql_filter

def bbox_sdf_into_cql_filter(
    sdf: "pd.DataFrame", geometry_field: str, srid: int, cql_filter: str = None
):
    """
    Construct cql_filter and bbox parameters from SDF.
    """

    if sdf.spatial.sr.wkid != srid:
        sdf.spatial.project({"wkid": srid})
    minX, minY, maxX, maxY = sdf.spatial.full_extent
    bbox = f"bbox({geometry_field},{minY},{minX},{maxY},{maxX})"
    if cql_filter is None or cql_filter == "":
        cql_filter = bbox
    elif cql_filter > "":
        cql_filter = f"{bbox} AND {cql_filter}"

    return cql_filter


def geom_sdf_into_cql_filter(
    sdf: "pd.DataFrame",
    geometry_field: str,
    srid: int,
    spatial_rel: str = None,
    cql_filter: str = None,
):
    """
    Construct cql_filter and geometry filter parameters from SDF.
    """

    if spatial_rel is None:
        spatial_rel = "INTERSECTS"
    spatial_rel = spatial_rel.upper()
    if spatial_rel not in VALID_SPATIAL_RELATIONSHIPS:
        raise ValueError(f"Invalid spatial_rel parameter supplied: {spatial_rel}")

    if sdf.spatial.sr.wkid != srid:
        sdf.spatial.project({"wkid": srid})

    geom = sdf_to_single_geometry(sdf)

    # wkt coordinate x,y pairs need to be reversed
    # Pattern to match coordinate pairs
    pattern = r"(-?\d+\.\d+)\s+(-?\d+\.\d+)"
    # Swap each (x y) to (y x)
    reversed_wkt = re.sub(pattern, r"\2 \1", geom.WKT)

    spatial_filter = f"{spatial_rel}({geometry_field},{reversed_wkt})"

    if cql_filter is None or cql_filter == "":
        cql_filter = spatial_filter
    elif cql_filter > "":
        cql_filter = f"{spatial_filter} AND {cql_filter}"

    return cql_filter
