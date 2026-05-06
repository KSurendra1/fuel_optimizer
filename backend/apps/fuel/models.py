from django.db import models


class FuelStation(models.Model):
    name = models.CharField(max_length=200, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="")
    state = models.CharField(max_length=32, blank=True, default="")
    latitude = models.FloatField()
    longitude = models.FloatField()
    price_per_gallon = models.DecimalField(max_digits=6, decimal_places=3)

    class Meta:
        indexes = [
            models.Index(fields=["latitude", "longitude"], name="fuel_lat_lng_idx"),
            models.Index(fields=["price_per_gallon"], name="fuel_price_idx"),
        ]

    def label(self) -> str:
        if self.city and self.state:
            return f"{self.city}, {self.state}"
        return self.name or f"{self.latitude:.4f},{self.longitude:.4f}"
