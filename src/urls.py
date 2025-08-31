from django.contrib import admin
from django.urls import path
from dashboard.views import (
    home, login_view, logout_view, transactions_api, 
    totp_setup, process_vehicle
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("api/transactions/", transactions_api, name="transactions_api"),
    path("totp-setup/", totp_setup, name="totp_setup"),
    path("api/process-vehicle/", process_vehicle, name="process_vehicle"),
]
