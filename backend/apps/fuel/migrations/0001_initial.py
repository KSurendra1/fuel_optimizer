from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="FuelStation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(blank=True, default="", max_length=200)),
                ("city", models.CharField(blank=True, default="", max_length=120)),
                ("state", models.CharField(blank=True, default="", max_length=32)),
                ("latitude", models.FloatField()),
                ("longitude", models.FloatField()),
                ("price_per_gallon", models.DecimalField(decimal_places=3, max_digits=6)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["latitude", "longitude"], name="fuel_lat_lng_idx"),
                    models.Index(fields=["price_per_gallon"], name="fuel_price_idx"),
                ],
            },
        )
    ]
