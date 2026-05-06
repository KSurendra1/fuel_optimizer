from unittest.mock import patch

from django.test import override_settings
from rest_framework.test import APITestCase


@override_settings(ROOT_URLCONF="config.urls")
class RoutePlanApiTests(APITestCase):
    @patch("api.views.RoutePlanView.optimizer.optimize")
    @patch("api.views.RoutePlanView.route_service.plan_route")
    def test_route_plan_success(self, mock_route, mock_optimize):
        mock_route.return_value = type(
            "R",
            (),
            {"distance_miles": 2800, "duration_seconds": 3600, "polyline": "abc", "route_points": [(1, 1), (2, 2)]},
        )
        mock_optimize.return_value = ([], 780.25)

        resp = self.client.post("/api/route-plan/", {"start": "New York, NY", "end": "Los Angeles, CA"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["distance_miles"], 2800.0)

    def test_route_plan_validation(self):
        resp = self.client.post("/api/route-plan/", {"start": "New York, NY"}, format="json")
        self.assertEqual(resp.status_code, 400)
