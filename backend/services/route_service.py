from dataclasses import dataclass
import logging
from django.conf import settings
from django.core.cache import cache
import requests
import re

logger = logging.getLogger("services.route_service")

from utils.geo import decode_polyline


@dataclass
class RouteData:
    distance_miles: float
    duration_seconds: int
    polyline: str
    route_points: list[tuple[float, float]]


class RouteService:
    GEOCODE_URL = "https://nominatim.openstreetmap.org/search"
    ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"
    MAPBOX_GEOCODE_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json"
    MAPBOX_DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox/driving/{coords}"

    def _geocode(self, query: str) -> tuple[float, float]:
        cache_key = f"geo:{_safe_cache_key(query)}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        headers = {"User-Agent": settings.NOMINATIM_USER_AGENT}
        resp = requests.get(self.GEOCODE_URL, params={"q": f"{query}, USA", "format": "json", "limit": 1}, headers=headers, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            raise ValueError(f"Could not geocode location: {query}")
        value = (float(data[0]["lat"]), float(data[0]["lon"]))
        cache.set(cache_key, value, timeout=60 * 60 * 24)
        return value

    def _fetch_ors_route(self, start: tuple[float, float], end: tuple[float, float]) -> RouteData:
        headers = {"Authorization": settings.OPENROUTESERVICE_API_KEY}
        payload = {"coordinates": [[start[1], start[0]], [end[1], end[0]]]}
        resp = requests.post(self.ORS_DIRECTIONS_URL, json=payload, headers=headers, timeout=12)
        resp.raise_for_status()
        feature = resp.json()["features"][0]
        summary = feature["properties"]["summary"]
        polyline = feature["geometry"]["coordinates"]
        encoded = feature["properties"].get("segments", [])

        # ORS default geometry is line string coordinates. Convert to [lat,lng] points and a pseudo polyline.
        route_points = [(latlng[1], latlng[0]) for latlng in polyline]
        route_polyline = _encode_line_string_fallback(route_points)
        if encoded and isinstance(encoded, str):
            route_polyline = encoded

        return RouteData(
            distance_miles=summary["distance"] / 1609.344,
            duration_seconds=int(summary["duration"]),
            polyline=route_polyline,
            route_points=route_points,
        )

    def _fetch_mapbox_route(self, start: tuple[float, float], end: tuple[float, float]) -> RouteData:
        coords = f"{start[1]},{start[0]};{end[1]},{end[0]}"
        resp = requests.get(
            self.MAPBOX_DIRECTIONS_URL.format(coords=coords),
            params={"geometries": "polyline", "overview": "full", "access_token": settings.MAPBOX_API_KEY},
            timeout=12,
        )
        resp.raise_for_status()
        route = resp.json()["routes"][0]
        polyline = route["geometry"]
        return RouteData(
            distance_miles=route["distance"] / 1609.344,
            duration_seconds=int(route["duration"]),
            polyline=polyline,
            route_points=decode_polyline(polyline),
        )

    def plan_route(self, start_query: str, end_query: str) -> RouteData:
        cache_key = f"route:{_safe_cache_key(start_query)}:{_safe_cache_key(end_query)}"
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"Route Cache HIT: {start_query} -> {end_query}")
            return cached

        logger.info(f"Route Cache MISS: {start_query} -> {end_query}")
        start = self._geocode(start_query)
        end = self._geocode(end_query)
        if start == end:
            raise ValueError("Start and end locations cannot be the same.")

        logger.info(f"Fetching route via {settings.ROUTE_PROVIDER}...")
        if settings.ROUTE_PROVIDER == "mapbox":
            route_data = self._fetch_mapbox_route(start, end)
        else:
            route_data = self._fetch_ors_route(start, end)

        cache.set(cache_key, route_data, timeout=60 * 60)
        return route_data


def _encode_line_string_fallback(points: list[tuple[float, float]]) -> str:
    # Lightweight fallback for ORS line string mode if encoded polyline is unavailable.
    return "|".join(f"{lat:.5f},{lng:.5f}" for lat, lng in points)


def _safe_cache_key(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", value.lower().strip()).strip("-")
