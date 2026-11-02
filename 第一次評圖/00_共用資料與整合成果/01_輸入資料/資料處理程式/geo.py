"""Shared geometry helpers. All metric maths happens in EPSG:3826 (TWD97 TM2,
metres); everything that is displayed or stored as source data stays in
EPSG:4326. pyproj Transformers are cached module-level because they are the
hot path when reprojecting ~10^5 vertices.
"""
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon, MultiLineString
from shapely.ops import linemerge, transform as shp_transform

TO_M   = Transformer.from_crs("EPSG:4326", "EPSG:3826", always_xy=True)
TO_DEG = Transformer.from_crs("EPSG:3826", "EPSG:4326", always_xy=True)

def to_m(geom):
    return shp_transform(lambda x, y, z=None: TO_M.transform(x, y), geom)

def to_deg(geom):
    return shp_transform(lambda x, y, z=None: TO_DEG.transform(x, y), geom)

def ll_to_m(lon, lat):
    return TO_M.transform(lon, lat)

def m_to_ll(x, y):
    return TO_DEG.transform(x, y)

def bearing_deg(p0, p1):
    """Bearing of a segment in degrees, folded to 0-180 (undirected)."""
    import math
    dx, dy = p1[0]-p0[0], p1[1]-p0[1]
    a = math.degrees(math.atan2(dx, dy)) % 180.0
    return a
