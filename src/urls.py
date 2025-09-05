from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from dashboard.views import (
    home, login_view, logout_view, transactions_api, 
    totp_setup, process_vehicle,
    anpr_page, anpr_process_api, anpr_results_api,
    process_vehicle_transaction, transaction_status, recent_transactions,
    register_plate, plate_info, list_registrations, manage_registrations, 
    gemini_plate_api, manual_review_update, initiate_paynow_funding, check_payment_status, paynow_callback,
    # Customer portal views
    customer_portal, customer_transactions, add_funds, account_statements, manage_user_plates,
    # User management views
    manage_users, user_detail
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("api/transactions/", transactions_api, name="transactions_api"),
    path("totp-setup/", totp_setup, name="totp_setup"),
    path("anpr/", anpr_page, name="anpr_page"),
    path("api/process-vehicle/", process_vehicle, name="process_vehicle"),
    path("api/anpr/process/", anpr_process_api, name="anpr_process_api"),
    path("api/anpr/results/", anpr_results_api, name="anpr_results_api"),
    # New transaction flow endpoints
    path("api/process-vehicle-transaction/", process_vehicle_transaction, name="process_vehicle_transaction"),
    path("api/transaction-status/<str:transaction_id>/", transaction_status, name="transaction_status"),
    path("api/recent-transactions/", recent_transactions, name="recent_transactions"),
    # Plate registration endpoints
    path("api/plates/register/", register_plate, name="register_plate"),
    path("api/plates/info/", plate_info, name="plate_info"),
    path("api/plates/", list_registrations, name="list_registrations"),
    path("registrations/", manage_registrations, name="manage_registrations"),
    path("api/gemini-plate/", gemini_plate_api, name="gemini_plate_api"),
    path("api/transactions/manual-review/", manual_review_update, name="manual_review_update"),
    path("api/initiate-paynow-funding/", initiate_paynow_funding, name="initiate_paynow_funding"),
    path("api/check-payment-status/", check_payment_status, name="check_payment_status"),
    path("paynow/callback/", paynow_callback, name="paynow_callback"),
    
    # Customer Portal URLs
    path("portal/", customer_portal, name="customer_portal"),
    path("portal/transactions/", customer_transactions, name="customer_transactions"),
    path("portal/statements/", account_statements, name="account_statements"),
    path("portal/plates/", manage_user_plates, name="manage_user_plates"),
    path("api/add-funds/", add_funds, name="add_funds"),
    
    # User Management URLs (Admin only)
    path("users/", manage_users, name="manage_users"),
    path("users/<int:user_id>/", user_detail, name="user_detail"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
