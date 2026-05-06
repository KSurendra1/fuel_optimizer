from dataclasses import dataclass

from django.core.cache import cache

from apps.fuel.models import FuelStation
from utils.geo import bbox_for_radius, haversine_miles


@dataclass
class StationCandidate:
    station: FuelStation
    distance_from_route_miles: float


class FuelService:
    def nearby_stations(self, lat: float, lng: float, radius_miles: float = 20, limit: int = 30) -> list[StationCandidate]:
        cache_key = f"fuel-nearby:{round(lat,3)}:{round(lng,3)}:{int(radius_miles)}:{limit}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        min_lat, max_lat, min_lng, max_lng = bbox_for_radius(lat, lng, radius_miles)
        queryset = FuelStation.objects.filter(
            latitude__gte=min_lat,
            latitude__lte=max_lat,
            longitude__gte=min_lng,
            longitude__lte=max_lng,
        ).only("id", "city", "state", "name", "latitude", "longitude", "price_per_gallon")

        candidates: list[StationCandidate] = []
        for station in queryset:
            distance = haversine_miles(lat, lng, station.latitude, station.longitude)
            if distance <= radius_miles:
                candidates.append(StationCandidate(station=station, distance_from_route_miles=distance))

        candidates.sort(key=lambda x: (float(x.station.price_per_gallon), x.distance_from_route_miles))
        result = candidates[:limit]
        cache.set(cache_key, result, timeout=60 * 30)
        return result
