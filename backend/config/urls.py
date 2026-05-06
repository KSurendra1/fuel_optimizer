from django.contrib import admin
from django.urls import path

from api.views import RoutePlanView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/route-plan/", RoutePlanView.as_view(), name="route-plan"),
]
