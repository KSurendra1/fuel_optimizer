import math
from typing import Iterable


EARTH_RADIUS_MI = 3958.8


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(a))


def bbox_for_radius(lat: float, lon: float, radius_miles: float) -> tuple[float, float, float, float]:
    lat_delta = radius_miles / 69.0
    lon_delta = radius_miles / max(1e-6, 69.0 * math.cos(math.radians(lat)))
    return lat - lat_delta, lat + lat_delta, lon - lon_delta, lon + lon_delta


def decode_polyline(polyline: str, precision: int = 5) -> list[tuple[float, float]]:
    coords: list[tuple[float, float]] = []
    index = lat = lng = 0
    factor = 10**precision
    while index < len(polyline):
        for coord in ("lat", "lng"):
            result = shift = 0
            while True:
                b = ord(polyline[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if (result & 1) else (result >> 1)
            if coord == "lat":
                lat += delta
            else:
                lng += delta
        coords.append((lat / factor, lng / factor))
    return coords


def sample_route_points(route_points: Iterable[tuple[float, float]], sample_every_miles: float) -> list[tuple[float, float]]:
    points = list(route_points)
    if len(points) < 2:
        return points
    sampled = [points[0]]
    bucket = sample_every_miles
    cumulative = 0.0
    for i in range(1, len(points)):
        prev = points[i - 1]
        curr = points[i]
        cumulative += haversine_miles(prev[0], prev[1], curr[0], curr[1])
        if cumulative >= bucket:
            sampled.append(curr)
            bucket += sample_every_miles
    if sampled[-1] != points[-1]:
        sampled.append(points[-1])
    return sampled
