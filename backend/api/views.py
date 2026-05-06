import logging
import time
from datetime import timedelta

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import RoutePlanRequestSerializer, RoutePlanResponseSerializer
from services.optimizer import RouteFuelOptimizer
from services.route_service import RouteService


logger = logging.getLogger("api.views")


class RoutePlanView(APIView):
    route_service = RouteService()
    optimizer = RouteFuelOptimizer()

    def post(self, request):
        start_time = time.time()
        serializer = RoutePlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        start = serializer.validated_data["start"]
        end = serializer.validated_data["end"]

        logger.info(f"RoutePlanRequest received: start='{start}' end='{end}'")

        try:
            route = self.route_service.plan_route(start, end)
            stops, total_cost = self.optimizer.optimize(route.distance_miles, route.route_points)
        except ValueError as exc:
            logger.warning(f"Validation error planning route: {exc}")
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error(f"Unexpected error planning route: {exc}", exc_info=True)
            return Response({"detail": f"Route planning failed: {exc}"}, status=status.HTTP_502_BAD_GATEWAY)

        map_url = ""
        if settings.MAPBOX_API_KEY and route.polyline and "|" not in route.polyline:
            map_url = (
                "https://api.mapbox.com/styles/v1/mapbox/streets-v11/static/"
                f"path-5+ff0000({route.polyline})/auto/800x500?access_token={settings.MAPBOX_API_KEY}"
            )

        payload = {
            "distance_miles": round(route.distance_miles, 2),
            "duration": str(timedelta(seconds=route.duration_seconds)),
            "route_polyline": route.polyline,
            "map_url": map_url,
            "fuel_stops": [stop.__dict__ for stop in stops],
            "total_fuel_cost": total_cost,
        }
        
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(f"RoutePlanRequest completed: distance={payload['distance_miles']}mi cost=${total_cost} duration={duration_ms}ms stops={len(stops)}")
        
        out = RoutePlanResponseSerializer(payload)
        return Response(out.data)
