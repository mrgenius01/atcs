from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from payments.transactions import simulate_transaction_log

@login_required
def home(request):
    return render(request, "dashboard/home.html")

@require_GET
@login_required
def transactions_api(request):
    # stubbed data feed
    return JsonResponse({"transactions": simulate_transaction_log(5)})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        token = request.POST.get("token")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Perform TOTP check (stub)
            from security.auth import verify_totp
            if verify_totp(user, token):
                login(request, user)
                return redirect("home")
        return render(request, "dashboard/login.html", {"error": "Invalid credentials or token."})
    return render(request, "dashboard/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")
