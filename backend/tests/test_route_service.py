from unittest.mock import patch, Mock

from django.test import SimpleTestCase, override_settings

from services.route_service import RouteService


@override_settings(
    ROUTE_PROVIDER="mapbox",
    MAPBOX_API_KEY="x",
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class RouteServiceTests(SimpleTestCase):
    @patch("services.route_service.requests.get")
    def test_route_parsing_mapbox(self, mock_get):
        geo_start = Mock()
        geo_start.json.return_value = [{"lat": "40.7128", "lon": "-74.0060"}]
        geo_start.raise_for_status.return_value = None
        geo_end = Mock()
        geo_end.json.return_value = [{"lat": "34.0522", "lon": "-118.2437"}]
        geo_end.raise_for_status.return_value = None
        route = Mock()
        route.json.return_value = {"routes": [{"distance": 1000, "duration": 600, "geometry": "_p~iF~ps|U"}]}
        route.raise_for_status.return_value = None
        mock_get.side_effect = [geo_start, geo_end, route]

        data = RouteService().plan_route("New York, NY", "Los Angeles, CA")
        self.assertAlmostEqual(data.distance_miles, 1000 / 1609.344, places=4)
        self.assertEqual(data.polyline, "_p~iF~ps|U")
