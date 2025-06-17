import pytest
import pandas as pd
import json
from datetime import datetime
from shapely.geometry import Polygon
from kapipy.conversion import (
    map_field_type,
    map_geometry_type,
    is_valid_date,
    geojson_to_featureset,
    geojson_to_gdf,
    geojson_to_sdf,
    json_to_df,
    sdf_to_single_polygon_geojson,
    gdf_to_single_polygon_geojson,
    get_data_type,
    get_default_output_format,
    sdf_to_single_geometry,
    esri_json_to_geojson,
    bbox_gdf_into_cql_filter,
    geom_gdf_into_cql_filter,
    bbox_sdf_into_cql_filter,
    geom_sdf_into_cql_filter,
    has_arcgis,
    has_geopandas,
)
from kapipy.data_classes import (
    FieldDef
)

def test_map_field_type():
    assert map_field_type("integer") == "esriFieldTypeInteger"
    assert map_field_type("float") == "esriFieldTypeDouble"
    assert map_field_type("string") == "esriFieldTypeString"
    assert map_field_type("date") == "esriFieldTypeDate"
    assert map_field_type("unknown_type") == "esriFieldTypeString"

def test_map_geometry_type():
    assert map_geometry_type("Point") == "esriGeometryPoint"
    assert map_geometry_type("MultiPoint") == "esriGeometryMultipoint"
    assert map_geometry_type("LineString") == "esriGeometryPolyline"
    assert map_geometry_type("Polygon") == "esriGeometryPolygon"
    assert map_geometry_type("Unknown") is None

def test_is_valid_date():
    assert is_valid_date("2020-01-01")
    assert is_valid_date("2020-01-01T12:34:56Z")
    assert is_valid_date(1609459200000)
    assert is_valid_date(None)
    assert not is_valid_date("not-a-date")
    assert is_valid_date(datetime.now())

@pytest.mark.skipif(not has_arcgis, reason="arcgis module not installed")
def test_geojson_to_featureset_point():
    from dataclasses import dataclass
    @dataclass
    class FieldDef:
        name: str
        type_: str

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "x": 1.0, "y": 2.0},
                "properties": {"id": 1, "name": "A"},
            }
        ],
    }
    fields = [FieldDef(name="id", type_="integer"), FieldDef(name="name", type_="string")]
    fs = geojson_to_featureset(geojson, "esriGeometryPoint", fields)
    assert hasattr(fs, "features")
    assert len(fs.features) == 1
    assert fs.features[0].attributes["id"] == 1
    assert fs.features[0].attributes["name"] == "A"

@pytest.mark.skipif(not has_arcgis, reason="arcgis module not installed")
def test_geojson_to_featureset_polygon():
    from dataclasses import dataclass
    @dataclass
    class FieldDef:
        name: str
        type_: str

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "rings": [
                        [
                            [0.0, 0.0],
                            [0.0, 1.0],
                            [1.0, 1.0],
                            [1.0, 0.0],
                            [0.0, 0.0],
                        ]
                    ],
                },
                "properties": {"id": 2, "name": "B"},
            }
        ],
    }
    fields = [FieldDef(name="id", type_="integer"), FieldDef(name="name", type_="string")]
    fs = geojson_to_featureset(geojson, "esriGeometryPolygon", fields)
    assert hasattr(fs, "features")
    assert len(fs.features) == 1
    assert fs.features[0].attributes["id"] == 2
    assert fs.features[0].attributes["name"] == "B"

@pytest.mark.skipif(not has_geopandas, reason="geopandas module not installed")
def test_geojson_to_gdf():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                "properties": {"id": 1, "name": "A"},
            }
        ],
    }
    gdf = geojson_to_gdf(geojson, out_sr=4326)
    assert not gdf.empty
    assert list(gdf.columns) == ["id", "name", "geometry"]
    assert gdf.iloc[0]["id"] == 1
    assert gdf.iloc[0]["name"] == "A"

@pytest.mark.skipif(not has_arcgis, reason="arcgis module not installed")
def test_geojson_to_sdf():
    
    from arcgis.features import GeoAccessor
    from arcgis.features import FeatureSet
    # Create a dummy SEDF using FeatureSet
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "x": 1.0, "y": 2.0},
                "properties": {"id": 1, "name": "A"},
            }
        ],
    }
    from dataclasses import dataclass
    @dataclass
    class FieldDef:
        name: str
        type_: str
    fields = [FieldDef(name="id", type_="integer"), FieldDef(name="name", type_="string")]
    sdf = geojson_to_sdf(geojson, out_sr=4326, geometry_type="esriGeometryPoint")
    assert not sdf.empty
    assert "id" in sdf.columns
    assert "name" in sdf.columns

def test_json_to_df():
    json_data = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": None, "properties": {"id": 1, "name": "A"}},
            {"type": "Feature", "geometry": None, "properties": {"id": 2, "name": "B"}},
        ],
    }
    df = json_to_df(json_data)
    assert not df.empty
    assert list(df.columns) == ["id", "name"]
    assert df.iloc[0]["id"] == 1
    assert df.iloc[1]["name"] == "B"

@pytest.mark.skipif(not has_geopandas, reason="geopandas module not installed")
def test_gdf_to_single_polygon_geojson():
    import geopandas as gpd
    poly = Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
    gdf = gpd.GeoDataFrame(geometry=[poly], crs="EPSG:4326")
    geojson = gdf_to_single_polygon_geojson(gdf)
    assert geojson["type"] == "Polygon"
    assert isinstance(geojson["coordinates"], list)

def test_get_data_type_str():
    assert get_data_type("hello") == "str"

@pytest.mark.skipif(not has_geopandas, reason="geopandas module not installed")
def test_get_data_type_gdf():
    import geopandas as gpd
    gdf = gpd.GeoDataFrame(geometry=[])
    assert get_data_type(gdf) == "gdf"

@pytest.mark.skipif(not has_arcgis, reason="arcgis module not installed")
def test_get_data_type_sdf():
    from arcgis.features import GeoAccessor
    from arcgis.features import FeatureSet
    # Create a dummy SEDF using FeatureSet
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "x": 1.0, "y": 2.0},
                "properties": {"id": 1, "name": "A"},
            }
        ],
    }
    from dataclasses import dataclass
    @dataclass
    class FieldDef:
        name: str
        type_: str
    fields = [FieldDef(name="id", type_="integer"), FieldDef(name="name", type_="string")]
    fs = geojson_to_featureset(geojson, "esriGeometryPoint", fields)
    sdf = fs.sdf
    assert get_data_type(sdf) == "sdf"

def test_get_default_output_format():
    fmt = get_default_output_format()
    assert fmt in ("sdf", "gdf", "json")

@pytest.mark.skipif(not has_arcgis, reason="arcgis module not installed")
def test_sdf_to_single_geometry():
    from arcgis.features import FeatureSet
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "x": 1.0, "y": 2.0},
                "properties": {"id": 1, "name": "A"},
            }
        ],
    }
    from dataclasses import dataclass
    @dataclass
    class FieldDef:
        name: str
        type_: str
    fields = [FieldDef(name="id", type_="integer"), FieldDef(name="name", type_="string")]
    fs = geojson_to_featureset(geojson, "esriGeometryPoint", fields)
    sdf = fs.sdf
    geom = sdf_to_single_geometry(sdf)
    assert hasattr(geom, "JSON")

def test_esri_json_to_geojson_point():
    esri_json = {"x": 1.0, "y": 2.0, "spatialReference": {"wkid": 4326}}
    geojson = esri_json_to_geojson(esri_json, "point")
    assert geojson["type"] == "Point"
    assert geojson["coordinates"] == [1.0, 2.0]

def test_esri_json_to_geojson_polygon():
    esri_json = {"rings": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]], "spatialReference": {"wkid": 4326}}
    geojson = esri_json_to_geojson(esri_json, "polygon")
    assert geojson["type"] == "Polygon"
    assert isinstance(geojson["coordinates"], list)

@pytest.mark.skipif(not has_geopandas, reason="geopandas module not installed")
def test_bbox_gdf_into_cql_filter():
    import geopandas as gpd
    poly = Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
    gdf = gpd.GeoDataFrame(geometry=[poly], crs="EPSG:4326")
    cql = bbox_gdf_into_cql_filter(gdf, "geom", 4326)
    assert cql.startswith("bbox(")

@pytest.mark.skipif(not has_geopandas, reason="geopandas module not installed")
def test_geom_gdf_into_cql_filter():
    import geopandas as gpd
    poly = Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
    gdf = gpd.GeoDataFrame(geometry=[poly], crs="EPSG:4326")
    cql = geom_gdf_into_cql_filter(gdf, "geom", 4326)
    assert cql.startswith("INTERSECTS(")

@pytest.mark.skipif(not has_arcgis, reason="arcgis module not installed")
def test_bbox_sdf_into_cql_filter():
    from arcgis.features import FeatureSet
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "x": 1.0, "y": 2.0},
                "properties": {"id": 1, "name": "A"},
            }
        ],
    }
    from dataclasses import dataclass
    @dataclass
    class FieldDef:
        name: str
        type_: str
    fields = [FieldDef(name="id", type_="integer"), FieldDef(name="name", type_="string")]
    fs = geojson_to_featureset(geojson, "esriGeometryPoint", fields)
    sdf = fs.sdf
    cql = bbox_sdf_into_cql_filter(sdf, "geom", 4326)
    assert cql.startswith("bbox(")

@pytest.mark.skipif(not has_arcgis, reason="arcgis module not installed")
def test_geom_sdf_into_cql_filter():
    from arcgis.features import FeatureSet
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "x": 1.0, "y": 2.0},
                "properties": {"id": 1, "name": "A"},
            }
        ],
    }
    from dataclasses import dataclass
    @dataclass
    class FieldDef:
        name: str
        type_: str
    fields = [FieldDef(name="id", type_="integer"), FieldDef(name="name", type_="string")]
    fs = geojson_to_featureset(geojson, "esriGeometryPoint", fields)
    sdf = fs.sdf
    cql = geom_sdf_into_cql_filter(sdf, "geom", 4326)
    assert cql.startswith("INTERSECTS(")