from django.contrib import admin
from django.urls import path
from dashboard.views import (
    home, login_view, logout_view, transactions_api, 
    totp_setup, totp_disable, process_vehicle,
    anpr_page, anpr_process_api, anpr_results_api
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("api/transactions/", transactions_api, name="transactions_api"),
    path("totp-setup/", totp_setup, name="totp_setup"),
    path("totp-disable/", totp_disable, name="totp_disable"),
    path("anpr/", anpr_page, name="anpr_page"),
    path("api/process-vehicle/", process_vehicle, name="process_vehicle"),
    path("api/anpr/process/", anpr_process_api, name="anpr_process_api"),
    path("api/anpr/results/", anpr_results_api, name="anpr_results_api"),
]
