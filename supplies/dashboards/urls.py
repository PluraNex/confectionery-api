# supplies/dashboards/urls.py

from django.urls import path
from .views import supplies_dashboard

app_name = "supplies_dashboard"

urlpatterns = [
    path("admin/supplies/dashboard/", supplies_dashboard, name="dashboard"),
]
