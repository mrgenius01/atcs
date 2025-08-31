from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Transaction
from security.auth import verify_totp, get_qr_code
from payments.transactions import process_payment
from anpr.detector import detect_and_recognize_plate


@login_required
def home(request):
    recent_transactions = Transaction.objects.all()[:10]
    return render(request, "dashboard/home.html", {
        'recent_transactions': recent_transactions
    })


@require_GET
@login_required
def transactions_api(request):
    """API endpoint for live transaction data"""
    transactions = Transaction.objects.all()[:20]
    data = []
    for tx in transactions:
        data.append({
            'plate': tx.license_plate,
            'timestamp': tx.timestamp.isoformat(),
            'amount': float(tx.amount),
            'payment_method': tx.payment_method,
            'status': tx.status,
            'gate_id': tx.gate_id
        })
    return JsonResponse({"transactions": data})


@login_required
def totp_setup(request):
    """TOTP setup page with QR code"""
    qr_code = get_qr_code(request.user)
    return render(request, "dashboard/totp_setup.html", {
        'qr_code': qr_code
    })


@csrf_exempt
@require_POST
def process_vehicle(request):
    """Process vehicle detection and payment"""
    try:
        data = json.loads(request.body)
        image_data = data.get('image')
        
        if not image_data:
            return JsonResponse({'error': 'No image provided'}, status=400)
        
        # Detect license plate
        plate_result = detect_and_recognize_plate(image_data)
        
        if not plate_result or not plate_result.get('plate'):
            return JsonResponse({'error': 'Could not detect license plate'}, status=400)
        
        plate_number = plate_result['plate']
        confidence = plate_result.get('confidence', 0.0)
        
        # Process payment
        payment_result = process_payment(plate_number, 2.00)  # $2 toll
        
        # Create transaction record
        transaction = Transaction.objects.create(
            license_plate=plate_number,
            amount=2.00,
            status=payment_result['status'],
            payment_method='EcoCash'
        )
        
        return JsonResponse({
            'transaction_id': transaction.id,
            'plate': plate_number,
            'confidence': confidence,
            'amount': 2.00,
            'status': payment_result['status'],
            'message': payment_result.get('message', '')
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        token = request.POST.get("token")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Perform TOTP check
            if verify_totp(user, token):
                login(request, user)
                return redirect("home")
        return render(request, "dashboard/login.html", {"error": "Invalid credentials or token."})
    return render(request, "dashboard/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")
