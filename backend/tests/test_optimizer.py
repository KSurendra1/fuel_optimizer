from decimal import Decimal

from django.test import TestCase, override_settings

from apps.fuel.models import FuelStation
from services.fuel_service import StationCandidate
from services.optimizer import RouteFuelOptimizer


@override_settings(ROUTE_SEGMENT_SAMPLE_MILES=100, FUEL_SEARCH_RADIUS_MILES=25)
class OptimizerTests(TestCase):
    def setUp(self):
        FuelStation.objects.bulk_create(
            [
                FuelStation(city="A", state="TX", latitude=30.0, longitude=-97.0, price_per_gallon=Decimal("3.50")),
                FuelStation(city="B", state="TX", latitude=31.0, longitude=-98.0, price_per_gallon=Decimal("3.20")),
                FuelStation(city="C", state="TX", latitude=32.0, longitude=-99.0, price_per_gallon=Decimal("3.10")),
            ]
        )

    def test_optimizer_returns_stops_and_total_cost(self):
        points = [(30.0, -97.0), (30.0, -107.0), (30.0, -117.0)]
        station = FuelStation(city="X", state="TX", latitude=30.0, longitude=-97.0, price_per_gallon=Decimal("3.20"))

        class StubFuelService:
            def nearby_stations(self, *args, **kwargs):
                return [StationCandidate(station=station, distance_from_route_miles=1.0)]

        optimizer = RouteFuelOptimizer(fuel_service=StubFuelService())
        stops, total_cost = optimizer.optimize(1200, points)

        self.assertGreaterEqual(len(stops), 1)
        self.assertGreater(total_cost, 0)

    def test_zero_distance_returns_empty(self):
        optimizer = RouteFuelOptimizer()
        stops, total_cost = optimizer.optimize(0, [(30.0, -97.0)])
        self.assertEqual(stops, [])
        self.assertEqual(total_cost, 0.0)
