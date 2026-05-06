from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

from services.fuel_service import FuelService, StationCandidate
from utils.geo import haversine_miles, sample_route_points


@dataclass
class FuelStop:
    location: str
    lat: float
    lng: float
    price_per_gallon: float
    gallons_filled: float
    cost: float


class RouteFuelOptimizer:
    def __init__(self, fuel_service: FuelService | None = None):
        self.fuel_service = fuel_service or FuelService()
        self.mpg = float(settings.MILES_PER_GALLON)
        self.max_gallons = float(settings.MAX_GALLONS_PER_TANK)
        self.max_leg_miles = float(settings.VEHICLE_RANGE_MILES)
        self.segment_miles = float(settings.ROUTE_SEGMENT_SAMPLE_MILES)

    def optimize(self, distance_miles: float, route_points: list[tuple[float, float]]) -> tuple[list[FuelStop], float]:
        if distance_miles <= 0:
            return [], 0.0

        sampled = sample_route_points(route_points, self.segment_miles)
        if len(sampled) < 2:
            return [], 0.0

        remaining_distance = distance_miles
        tank_gallons = self.max_gallons  # assume trip starts with full tank
        total_cost = Decimal("0")
        stops: list[FuelStop] = []

        miles_progress = 0.0
        for i, point in enumerate(sampled[:-1]):
            next_point = sampled[i + 1]
            leg_miles = haversine_miles(point[0], point[1], next_point[0], next_point[1])
            remaining_distance = max(0.0, distance_miles - miles_progress)
            fuel_left_range = tank_gallons * self.mpg

            need_refuel = fuel_left_range < leg_miles or fuel_left_range < min(self.max_leg_miles * 0.4, remaining_distance)
            if need_refuel:
                nearby = self.fuel_service.nearby_stations(point[0], point[1], radius_miles=settings.FUEL_SEARCH_RADIUS_MILES)
                if nearby:
                    chosen = self._choose_station_with_lookahead(nearby, sampled, i)
                    target_range = min(self.max_leg_miles, remaining_distance)
                    required_gallons = max(0.0, (target_range / self.mpg) - tank_gallons)

                    cheapest_ahead = self._cheaper_station_ahead_price(sampled, i)
                    current_price = float(chosen.station.price_per_gallon)
                    if cheapest_ahead is not None and cheapest_ahead < current_price:
                        required_gallons = min(required_gallons, 15.0)
                    else:
                        required_gallons = min(self.max_gallons - tank_gallons, max(required_gallons, 20.0))

                    if required_gallons > 0:
                        tank_gallons += required_gallons
                        leg_cost = Decimal(str(required_gallons)) * chosen.station.price_per_gallon
                        total_cost += leg_cost

                        stops.append(
                            FuelStop(
                                location=chosen.station.label(),
                                lat=chosen.station.latitude,
                                lng=chosen.station.longitude,
                                price_per_gallon=float(chosen.station.price_per_gallon),
                                gallons_filled=round(required_gallons, 2),
                                cost=round(float(leg_cost), 2),
                            )
                        )

            tank_gallons = max(0.0, tank_gallons - (leg_miles / self.mpg))
            miles_progress += leg_miles

        return stops, round(float(total_cost), 2)

    def _choose_station_with_lookahead(self, nearby: list[StationCandidate], sampled_points: list[tuple[float, float]], idx: int) -> StationCandidate:
        cheapest_ahead = self._cheaper_station_ahead_price(sampled_points, idx)
        if cheapest_ahead is None:
            return nearby[0]
        viable = [s for s in nearby if float(s.station.price_per_gallon) <= cheapest_ahead + 0.05]
        return viable[0] if viable else nearby[0]

    def _cheaper_station_ahead_price(self, sampled_points: list[tuple[float, float]], idx: int) -> float | None:
        lookahead_prices: list[float] = []
        for j in range(idx + 1, min(idx + 4, len(sampled_points))):
            stations = self.fuel_service.nearby_stations(
                sampled_points[j][0], sampled_points[j][1], radius_miles=settings.FUEL_SEARCH_RADIUS_MILES, limit=5
            )
            if stations:
                lookahead_prices.append(float(stations[0].station.price_per_gallon))
        return min(lookahead_prices) if lookahead_prices else None
