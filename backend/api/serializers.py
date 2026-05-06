from rest_framework import serializers


class RoutePlanRequestSerializer(serializers.Serializer):
    start = serializers.CharField(max_length=200)
    end = serializers.CharField(max_length=200)


class FuelStopSerializer(serializers.Serializer):
    location = serializers.CharField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    price_per_gallon = serializers.FloatField()
    gallons_filled = serializers.FloatField()
    cost = serializers.FloatField()


class RoutePlanResponseSerializer(serializers.Serializer):
    distance_miles = serializers.FloatField()
    duration = serializers.CharField()
    route_polyline = serializers.CharField()
    map_url = serializers.CharField(allow_blank=True)
    fuel_stops = FuelStopSerializer(many=True)
    total_fuel_cost = serializers.FloatField()
