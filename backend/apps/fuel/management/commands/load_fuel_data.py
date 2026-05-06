import csv
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.fuel.models import FuelStation


class Command(BaseCommand):
    help = "Load fuel station data from CSV into FuelStation table using offline geocoding."

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, default=str(settings.BASE_DIR.parent / "fuel-prices-for-be-assessment.csv"))
        parser.add_argument("--truncate", action="store_true")

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        if not file_path.exists():
            raise CommandError(f"Fuel data file not found: {file_path}")

        us_cities_path = settings.BASE_DIR / "data" / "us_cities.csv"
        if not us_cities_path.exists():
            raise CommandError(f"Offline geocoding mapping not found at {us_cities_path}. Please download it.")

        # Build mapping: (city.lower(), state.lower()) -> (lat, lng)
        self.stdout.write("Building offline geocoding index...")
        geo_index = {}
        with us_cities_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    city = row["CITY"].strip().lower()
                    state = row["STATE_CODE"].strip().lower()
                    lat = float(row["LATITUDE"])
                    lng = float(row["LONGITUDE"])
                    geo_index[(city, state)] = (lat, lng)
                except (KeyError, ValueError):
                    pass

        if options["truncate"]:
            FuelStation.objects.all().delete()
            self.stdout.write("Truncated existing fuel stations.")

        batch = []
        missing_geo = 0
        self.stdout.write("Loading fuel prices...")
        
        with file_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader, None)  # Skip header row
            
            # Expected format: OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price
            for row in reader:
                if len(row) < 7:
                    continue
                
                name = row[1].strip()
                address = row[2].strip()
                city = row[3].strip()
                state = row[4].strip()
                
                try:
                    price_str = row[6].strip()
                    if not price_str:
                        continue
                    price_per_gallon = Decimal(price_str)
                except ValueError:
                    continue
                
                # Geocode using our offline dictionary
                coords = geo_index.get((city.lower(), state.lower()))
                if not coords:
                    # fallback to state only? no, skip missing
                    missing_geo += 1
                    continue
                
                lat, lng = coords
                
                batch.append(
                    FuelStation(
                        name=f"{name} ({address})",
                        city=city[:120],
                        state=state[:32],
                        latitude=lat,
                        longitude=lng,
                        price_per_gallon=price_per_gallon,
                    )
                )

                if len(batch) >= 2000:
                    FuelStation.objects.bulk_create(batch, batch_size=2000)
                    batch = []

        if batch:
            FuelStation.objects.bulk_create(batch, batch_size=2000)

        self.stdout.write(self.style.SUCCESS(f"Fuel data loaded successfully! Skipped {missing_geo} stations due to missing offline geocoding."))
