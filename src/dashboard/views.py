from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Transaction, ANPRResult, AuditLog
from security.auth import verify_totp, get_qr_code, get_or_create_profile
from payments.transactions import process_payment
from anpr.detector import detect_and_recognize_plate


# @login_required  # Temporarily disabled for testing
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
    """TOTP setup page with QR code and verification"""
    profile = get_or_create_profile(request.user)
    
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "enable":
            # User wants to enable TOTP - verify token first
            token = request.POST.get("token")
            if token and profile.verify_totp(token):
                profile.totp_enabled = True
                profile.save()
                return render(request, "dashboard/totp_setup.html", {
                    'qr_code': profile.get_qr_code(),
                    'totp_uri': profile.get_totp_uri(),
                    'success': 'TOTP authentication has been successfully enabled!',
                    'is_enabled': True
                })
            else:
                return render(request, "dashboard/totp_setup.html", {
                    'qr_code': profile.get_qr_code(),
                    'totp_uri': profile.get_totp_uri(),
                    'error': 'Invalid TOTP code. Please try again.',
                    'is_enabled': False
                })
        
        elif action == "disable":
            # User wants to disable TOTP
            profile.totp_enabled = False
            profile.save()
            return render(request, "dashboard/totp_setup.html", {
                'qr_code': profile.get_qr_code(),
                'totp_uri': profile.get_totp_uri(),
                'success': 'TOTP authentication has been disabled.',
                'is_enabled': False
            })
    
    # GET request - show setup page
    return render(request, "dashboard/totp_setup.html", {
        'qr_code': profile.get_qr_code(),
        'totp_uri': profile.get_totp_uri(),
        'is_enabled': profile.totp_enabled,
        'is_first_setup': not profile.totp_enabled
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
        
        # First authenticate username and password
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Check if user has TOTP enabled
            profile = get_or_create_profile(user)
            
            if not profile.totp_enabled:
                # TOTP not set up yet, log them in and redirect to setup
                login(request, user)
                return redirect("totp_setup")
            else:
                # TOTP is enabled, verify the token
                if token and verify_totp(user, token):
                    login(request, user)
                    return redirect("home")
                else:
                    return render(request, "dashboard/login.html", {
                        "error": "Invalid TOTP code. Please check your authenticator app.",
                        "require_totp": True
                    })
        else:
            return render(request, "dashboard/login.html", {
                "error": "Invalid username or password."
            })
    
    return render(request, "dashboard/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def anpr_page(request):
    """ANPR processing page"""
    return render(request, "dashboard/anpr.html")


@login_required 
@require_POST
def anpr_process_api(request):
    """API endpoint for processing ANPR images with real OpenCV detection"""
    try:
        data = json.loads(request.body)
        image_data = data.get('image')
        
        if not image_data:
            return JsonResponse({'error': 'No image provided'}, status=400)
        
        # Process the image using real OpenCV ANPR
        from anpr.lightweight_processor import process_plate_image, validate_international_plate
        
        result = process_plate_image(image_data)
        
        if result.get('success') and result.get('plate_number'):
            print(result["plate_number"])
            # Validate the detected plate format
            validation = validate_international_plate(result['plate_number'])
            
            # Store result in database
            from .models import ANPRResult
            anpr_result = ANPRResult.objects.create(
                image_path="uploads/processed_image",  # In production, save actual file
                detected_plate=result['plate_number'],
                confidence=result.get('confidence', 0.0),
                processing_time=result.get('processing_time', 0.0)
            )
            
            # Return comprehensive result
            response_data = {
                'success': True,
                'plate_number': result['plate_number'],
                'confidence': result.get('confidence', 0.0),
                'processing_time': result.get('processing_time', 0.0),
                'message': result.get('message', ''),
                'validation': validation,
                'detection_region': result.get('detection_region'),
                'id': anpr_result.id
            }
            
            return JsonResponse(response_data)
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Detection failed'),
                'message': result.get('message', 'No license plate detected'),
                'confidence': 0.0
            }, status=400)
            
    except json.JSONDecodeError:
        print("ERROR OF INVALID JSON")
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Processing error: {str(e)}'}, status=500)


@login_required
@require_GET
def anpr_results_api(request):
    """API endpoint for recent ANPR results"""
    from .models import ANPRResult
    
    results = ANPRResult.objects.all()[:20]
    data = {
        'results': [
            {
                'detected_plate': result.detected_plate,
                'confidence': float(result.confidence),
                'processing_time': float(result.processing_time),
                'timestamp': result.timestamp.isoformat(),
            }
            for result in results
        ]
    }
    return JsonResponse(data)


@login_required
@require_POST
@csrf_exempt
def process_vehicle_transaction(request):
    """Complete vehicle transaction flow after plate detection"""
    print("=== TRANSACTION PROCESSING STARTED ===")
    
    try:
        # Parse request data
        data = json.loads(request.body)
        plate_number = data.get('plate_number')
        confidence = data.get('confidence', 0.0)
        location = data.get('location', 'Main Toll Plaza')
        toll_amount = data.get('toll_amount', 2.50)  # Default toll in USD
        
        print(f"Processing transaction for plate: {plate_number}")
        print(f"Confidence: {confidence}%, Location: {location}, Amount: ${toll_amount}")
        
        # Log audit trail
        AuditLog.objects.create(
            user=request.user,
            action='TRANSACTION_CREATE',
            details={
                'plate': plate_number,
                'confidence': confidence,
                'amount': toll_amount,
                'location': location
            },
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        if not plate_number:
            return JsonResponse({
                'success': False,
                'error': 'No plate number provided',
                'transaction_id': None
            })
        
        # Check if confidence is acceptable
        min_confidence = 0.7  # 70% minimum confidence
        if confidence < min_confidence:
            print(f"Low confidence: {confidence}% < {min_confidence}%")
            return JsonResponse({
                'success': False,
                'error': 'Low confidence detection',
                'message': f'Plate detection confidence ({confidence:.1f}%) below minimum threshold ({min_confidence*100}%)',
                'requires_manual_review': True,
                'plate_number': plate_number,
                'confidence': confidence
            })
        
        # 1. Create initial transaction record
        transaction = Transaction.objects.create(
            license_plate=plate_number,
            toll_amount=toll_amount,
            location=location,
            confidence=confidence,
            status='PROCESSING'
        )
        
        print(f"Created transaction: {transaction.transaction_id}")
        
        # 2. Process payment
        payment_result = process_payment(
            plate_number=plate_number,
            amount=toll_amount,
            transaction_id=str(transaction.transaction_id)
        )
        
        print(f"Payment result: {payment_result}")
        
        # 3. Update transaction status
        if payment_result['success']:
            transaction.status = 'COMPLETED'
            transaction.payment_method = payment_result.get('payment_method', 'ECOCASH')
            transaction.payment_reference = payment_result.get('reference', '')
        else:
            transaction.status = 'FAILED'
            transaction.error_message = payment_result.get('error', 'Payment failed')
        
        transaction.save()
        
        # 4. Store blockchain audit trail
        from blockchain.ledger import store_audit_hash
        audit_data = {
            'transaction_id': str(transaction.transaction_id),
            'plate': plate_number,
            'amount': str(toll_amount),
            'status': transaction.status,
            'timestamp': transaction.timestamp.isoformat()
        }
        audit_hash = store_audit_hash(audit_data)
        transaction.blockchain_hash = audit_hash
        transaction.save()
        
        print(f"Stored blockchain hash: {audit_hash[:16]}...")
        
        # 5. Log ANPR result
        ANPRResult.objects.create(
            detected_plate=plate_number,
            confidence=confidence,
            transaction=transaction,
            processing_time=payment_result.get('processing_time', 0),
            detection_method='opencv_real'
        )
        
        # 6. Log audit trail
        AuditLog.objects.create(
            user=request.user,
            action='PAYMENT_PROCESS',
            details={
                'transaction_id': str(transaction.transaction_id),
                'status': transaction.status,
                'payment_method': transaction.payment_method,
                'reference': transaction.payment_reference
            },
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        print("=== TRANSACTION PROCESSING COMPLETED ===")
        
        return JsonResponse({
            'success': payment_result['success'],
            'transaction_id': str(transaction.transaction_id),
            'plate_number': plate_number,
            'amount': float(toll_amount),
            'status': transaction.status,
            'payment_method': transaction.payment_method,
            'payment_reference': transaction.payment_reference,
            'blockchain_hash': audit_hash,
            'message': payment_result.get('message', 'Transaction processed successfully'),
            'balance_remaining': payment_result.get('balance', 0),
            'processing_time': payment_result.get('processing_time', 0)
        })
        
    except json.JSONDecodeError:
        print("ERROR: Invalid JSON in request")
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        print(f"ERROR: Transaction processing failed: {str(e)}")
        AuditLog.objects.create(
            user=request.user,
            action='SYSTEM_ERROR',
            details={'error': str(e), 'endpoint': 'process_vehicle_transaction'},
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return JsonResponse({
            'success': False,
            'error': f'Transaction processing failed: {str(e)}'
        }, status=500)


@login_required
def transaction_status(request, transaction_id):
    """Get transaction status"""
    try:
        transaction = Transaction.objects.get(transaction_id=transaction_id)
        return JsonResponse({
            'transaction_id': str(transaction_id),
            'status': transaction.status,
            'plate_number': transaction.license_plate,
            'amount': float(transaction.toll_amount),
            'timestamp': transaction.timestamp.isoformat(),
            'payment_method': transaction.payment_method,
            'location': transaction.location,
            'blockchain_hash': transaction.blockchain_hash,
            'processing_time': (transaction.processed_at - transaction.timestamp).total_seconds() if transaction.processed_at else None
        })
    except Transaction.DoesNotExist:
        return JsonResponse({
            'error': 'Transaction not found'
        }, status=404)


@login_required
def recent_transactions(request):
    """Get recent transactions for dashboard"""
    transactions = Transaction.objects.all()[:10]
    data = {
        'transactions': [
            {
                'transaction_id': str(t.transaction_id),
                'plate_number': t.license_plate,
                'amount': float(t.toll_amount),
                'status': t.status,
                'timestamp': t.timestamp.isoformat(),
                'location': t.location
            }
            for t in transactions
        ]
    }
    return JsonResponse(data)



