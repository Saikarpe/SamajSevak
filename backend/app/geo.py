"""GPS helpers: distance between complaints and ward lookup from coordinates."""
from math import asin, cos, radians, sin, sqrt

from app.knowledge import WARDS

PRECISE = ("gps", "pin", "seed")  # geo_source values that are a real point, not a ward centroid
WARD_RADIUS_M = 6000  # a point farther than this from every ward centre is outside the service area


def haversine_m(lat1, lng1, lat2, lng2) -> float:
    dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * 6371000 * asin(sqrt(a))


def nearest_ward(lat, lng):
    """Nearest ward centre, or None when the point is outside the service area."""
    ward, d = min(((w, haversine_m(lat, lng, *c)) for w, c in WARDS.items()), key=lambda x: x[1])
    return ward if d <= WARD_RADIUS_M else None
