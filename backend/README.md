# Route Optimization & Fuel Planning API

Production-style Django API for route planning + cost-efficient fuel stop optimization across USA routes.

## Features

- `POST /api/route-plan/` with `{ "start": "...", "end": "..." }`
- Route fetch from OpenRouteService or Mapbox
- Fuel stop optimization (`greedy + lookahead`)
- Redis caching for route + geo-station lookups
- Celery wiring for async workloads
- SQLite dev database with indexed fuel station table
- Docker + Gunicorn ready

## Quick Start

### Option 1: Local Development

1. Create environment and install deps:

```bash
pip install -r requirements.txt
cp .env.example .env
```

2. Run migrations and load station data:

```bash
python manage.py migrate
python manage.py load_fuel_data --file ./data/fuel_prices.csv --truncate
```

3. Run API:

```bash
python manage.py runserver
```

### Option 2: Docker (Recommended)

1. Copy environment file:

```bash
cp .env.example .env
```

2. Start services with Docker Compose:

```bash
docker-compose up --build
```

3. Load fuel data (in a new terminal):

```bash
docker-compose exec api python manage.py load_fuel_data --file ./data/fuel_prices.csv --truncate
```

The API will be available at `http://localhost:8000`.

## API

### Request

`POST /api/route-plan/`

```json
{
  "start": "New York, NY",
  "end": "Los Angeles, CA"
}
```

### Response (example)

```json
{
  "distance_miles": 2800.0,
  "duration": "1 day, 16:00:00",
  "route_polyline": "...",
  "map_url": "",
  "fuel_stops": [
    {
      "location": "Columbus, OH",
      "lat": 39.96,
      "lng": -82.99,
      "price_per_gallon": 3.25,
      "gallons_filled": 30.0,
      "cost": 97.5
    }
  ],
  "total_fuel_cost": 780.25
}
```

### Testing

Test the API using curl:

```bash
curl -X POST -H "Content-Type: application/json" -d '{"start":"New York, NY","end":"Los Angeles, CA"}' http://localhost:8000/api/route-plan/
```

Or using PowerShell:

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/route-plan/" -Method POST -ContentType "application/json" -Body '{"start":"New York, NY","end":"Los Angeles, CA"}' -UseBasicParsing | Select-Object -ExpandProperty Content
```

## Optimization Strategy

- Vehicle range: `500 miles`
- Mileage: `10 mpg`
- Max tank: `50 gallons`
- Sample route every ~`75 miles`
- At each sample:
  - Query nearby stations (20-mile radius)
  - Sort by price + distance from route
  - Look ahead 3 upcoming segments
  - If cheaper fuel ahead, buy minimal amount
  - Else fill aggressively while respecting tank max

## Caching Strategy

- Route cache key: `route:{start}:{end}` (1h)
- Geocode cache key: `geo:{query}` (24h)
- Fuel nearby cache key: rounded geo bucket (30m)

## Tests

```bash
python manage.py test
```

## Loom Demo Flow (under 5 min)

1. Show `.env` (`ROUTE_PROVIDER=mapbox`, API key, Redis URL).
2. Run `docker-compose up --build` and `docker-compose exec api python manage.py load_fuel_data --file ./data/fuel_prices.csv --truncate`.
3. Hit `POST /api/route-plan/` in Postman.
4. Explain:
   - Single route call (+ geocoding only)
   - Greedy + lookahead refuel decisions
   - Redis cache keys and response speedups
