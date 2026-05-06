from celery import shared_task

from services.optimizer import RouteFuelOptimizer


@shared_task
def optimize_route_fuel_task(distance_miles: float, route_points: list[tuple[float, float]]):
    optimizer = RouteFuelOptimizer()
    stops, total_cost = optimizer.optimize(distance_miles, route_points)
    return {"stops": [s.__dict__ for s in stops], "total_cost": total_cost}
