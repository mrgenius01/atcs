from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from decimal import Decimal
import json
import logging
from .models import (
    Transaction, ANPRResult, AuditLog, PlateRegistration, normalize_plate, 
    FeedbackThread, FeedbackReply, UserProfile, AccountTransaction, UserRole
)
from django.db import models
from security.auth import verify_totp, get_qr_code, get_or_create_profile
from payments.transactions import process_payment
from anpr.detector import detect_and_recognize_plate
from anpr.gemini_recognizer import recognize_plate_with_gemini

logger = logging.getLogger(__name__)

# Role-based access decorators
def admin_required(view_func):
    """Decorator to require admin role"""
    def check_admin(user):
        if not user.is_authenticated:
            return False
        profile = get_or_create_profile(user)
        return profile.role == UserRole.ADMIN
    
    return user_passes_test(check_admin)(view_func)


def operator_or_admin_required(view_func):
    """Decorator to require operator or admin role"""
    def check_operator_admin(user):
        if not user.is_authenticated:
            return False
        profile = get_or_create_profile(user)
        return profile.role in [UserRole.ADMIN, UserRole.OPERATOR]
    
    return user_passes_test(check_operator_admin)(view_func)


@csrf_exempt
@require_POST
@login_required
def gemini_plate_api(request):
    """API endpoint to test raw Gemini plate detection from image data."""
    try:
        data = json.loads(request.body)
        image_data = data.get('image')
        if not image_data:
            return JsonResponse({'error': 'No image provided'}, status=400)
        result = recognize_plate_with_gemini(image_data)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
@login_required
def transactions_api(request):
    """API endpoint for live transaction data"""
    transactions = Transaction.objects.all()[:20]
    data = []
    for tx in transactions:
        data.append({
            'transaction_id': str(tx.transaction_id),
            'plate': tx.license_plate,
            'timestamp': tx.timestamp.isoformat(),
            'amount': float(tx.toll_amount),  # Fixed: was tx.amount
            'payment_method': tx.payment_method or 'N/A',
            'status': tx.status,
            'location': tx.location,  # Fixed: was tx.gate_id
            'confidence': tx.confidence
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
        
        # Process payment (legacy simple flow)
        payment_result = process_payment(plate_number, 2.00)  # $2 toll
        
        # Create transaction record
        transaction = Transaction.objects.create(
            license_plate=plate_number,
            toll_amount=2.00,
            status='COMPLETED' if payment_result.get('status') == 'SUCCESS' else 'FAILED',
            payment_method='ECOCASH'
        )
        
        return JsonResponse({
            'transaction_id': transaction.id,
            'plate': plate_number,
            'confidence': confidence,
            'amount': 2.00,
            'status': payment_result.get('status', 'ERROR'),
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


@operator_or_admin_required
def anpr_page(request):
    """ANPR processing page - Admin/Operator only"""
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
                detected_plate=result['plate_number'],
                confidence=result.get('confidence', 0.0),
                processing_time=result.get('processing_time', 0.0),
                detection_method=result.get('method', 'opencv_real'),
                detection_region=result.get('detection_region')
            )
            
            # Process transaction with payment simulation after successful ANPR detection
            try:
                from .models import Transaction
                import uuid
                from decimal import Decimal
                from django.utils import timezone
                
                # Create initial transaction record
                transaction = Transaction.objects.create(
                    transaction_id=str(uuid.uuid4()),
                    license_plate=result['plate_number'],
                    toll_amount=Decimal('2.50'),  # Default toll amount
                    confidence=result.get('confidence', 0.0),
                    location='Gate A',  # Default location
                    status='PROCESSING',  # Start as processing
                    processed_at=timezone.now()
                )
                # Attach image data if available (store original upload)
                try:
                    if isinstance(image_data, str) and image_data.startswith('data:image'):
                        import base64, io
                        from django.core.files.base import ContentFile
                        header, b64 = image_data.split(',', 1)
                        content = base64.b64decode(b64)
                        transaction.image.save(f"{transaction.transaction_id}.png", ContentFile(content), save=True)
                except Exception as _:
                    pass
                
                # Process payment simulation
                payment_result = process_payment(result['plate_number'], 2.50)
                
                # Update transaction based on payment result
                if payment_result['status'] == 'SUCCESS':
                    transaction.status = 'COMPLETED'
                    transaction.payment_method = 'ECOCASH'
                    transaction.payment_reference = payment_result.get('audit_hash', '')[:20]
                else:
                    transaction.status = 'FAILED'
                    transaction.error_message = payment_result.get('message', 'Payment failed')
                    transaction.payment_method = 'ECOCASH'
                
                transaction.save()
                
                # Add transaction info to response
                transaction_info = {
                    'transaction_id': transaction.transaction_id,
                    'toll_amount': str(transaction.toll_amount),
                    'status': transaction.status,
                    'payment_method': transaction.payment_method,
                    'payment_simulation': payment_result['status'],
                    'payment_message': payment_result.get('message', '')
                }
                
            except Exception as e:
                print(f"Transaction creation error: {str(e)}")
                transaction_info = {'error': 'Transaction creation failed'}
            
            # Return comprehensive result
            response_data = {
                'success': True,
                'plate_number': result['plate_number'],
                'confidence': result.get('confidence', 0.0),
                'processing_time': result.get('processing_time', 0.0),
                'message': result.get('message', ''),
                'validation': validation,
                'detection_region': result.get('detection_region'),
                'id': anpr_result.id,
                'transaction': transaction_info
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
def register_plate(request):
    """Register or update a license plate with a phone number."""
    try:
        payload = json.loads(request.body)
        plate = payload.get('license_plate') or payload.get('plate')
        phone = payload.get('phone_number') or payload.get('phone')
        owner = payload.get('owner_name')
        if not plate or not phone:
            return JsonResponse({'error': 'license_plate and phone_number are required'}, status=400)

        norm = normalize_plate(plate)
        obj, created = PlateRegistration.objects.update_or_create(
            normalized_plate=norm,
            defaults={
                'user': request.user,  # Associate with current user
                'license_plate': plate.upper(),
                'phone_number': phone,
                'owner_name': owner,
                'is_active': True,
            }
        )

        AuditLog.objects.create(
            user=request.user,
            action='TRANSACTION_UPDATE',
            details={'plate': obj.license_plate, 'phone_number': obj.phone_number, 'created': created}
        )

        return JsonResponse({
            'success': True,
            'created': created,
            'license_plate': obj.license_plate,
            'phone_number': obj.phone_number,
            'owner_name': obj.owner_name,
            'is_active': obj.is_active,
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)


@login_required
@require_GET
def plate_info(request):
    """Lookup a plate; returns phone if registered."""
    plate = request.GET.get('plate') or request.GET.get('license_plate')
    if not plate:
        return JsonResponse({'error': 'plate is required'}, status=400)
    reg = PlateRegistration.objects.filter(normalized_plate=normalize_plate(plate), is_active=True).first()
    if not reg:
        return JsonResponse({'registered': False, 'message': 'Plate not registered'}, status=404)
    return JsonResponse({
        'registered': True,
        'license_plate': reg.license_plate,
        'phone_number': reg.phone_number,
        'owner_name': reg.owner_name,
        'is_active': reg.is_active,
    })


@login_required
@require_GET
def list_registrations(request):
    qs = PlateRegistration.objects.all()[:100]
    return JsonResponse({'registrations': [
        {
            'license_plate': r.license_plate,
            'phone_number': r.phone_number,
            'owner_name': r.owner_name,
            'is_active': r.is_active,
            'updated_at': r.updated_at.isoformat(),
        }
        for r in qs
    ]})


@operator_or_admin_required
def manage_registrations(request):
    """Render/manage plate registrations with a form and a table."""
    flash = None
    error = None
    if request.method == 'POST':
        action = request.POST.get('action', 'upsert')
        plate = request.POST.get('license_plate')
        phone = request.POST.get('phone_number')
        owner = request.POST.get('owner_name')
        reg_id = request.POST.get('id')
        try:
            if action in ('deactivate', 'activate') and reg_id:
                r = PlateRegistration.objects.get(id=reg_id)
                r.is_active = (action == 'activate')
                r.save()
                flash = f"Registration {action}d."
            elif action == 'delete' and reg_id:
                PlateRegistration.objects.filter(id=reg_id).delete()
                flash = "Registration deleted."
            else:
                if not plate or not phone:
                    error = 'license_plate and phone_number are required'
                else:
                    # Get user_id from form or default to current user for admin
                    user_id = request.POST.get('user_id') 
                    if user_id:
                        from django.contrib.auth.models import User
                        try:
                            assigned_user = User.objects.get(id=user_id)
                        except User.DoesNotExist:
                            error = 'Selected user not found'
                            assigned_user = None
                    else:
                        assigned_user = request.user  # Default to current user
                    
                    if assigned_user:
                        obj, created = PlateRegistration.objects.update_or_create(
                            normalized_plate=normalize_plate(plate),
                            defaults={
                                'user': assigned_user,
                                'license_plate': plate.upper(),
                                'phone_number': phone,
                                'owner_name': owner,
                                'is_active': True,
                            }
                        )
                        # If a plate image was uploaded, attach it
                        img = request.FILES.get('plate_image')
                        if img:
                            obj.plate_image = img
                            obj.save()
                        flash = 'Registration created.' if created else 'Registration updated.'
        except PlateRegistration.DoesNotExist:
            error = 'Registration not found'
        except Exception as e:
            error = str(e)

    from django.contrib.auth.models import User
    regs = PlateRegistration.objects.select_related('user').all().order_by('-updated_at')[:200]
    all_users = User.objects.all().order_by('username')
    
    return render(request, 'dashboard/registrations.html', {
        'registrations': regs,
        'all_users': all_users,
        'flash': flash,
        'error': error,
    })


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
        
        # 2. Lookup plate registration
        reg = PlateRegistration.objects.filter(normalized_plate=normalize_plate(plate_number), is_active=True).first()
        if not reg:
            transaction.status = 'FAILED'
            transaction.error_message = 'Plate not registered'
            transaction.save()
            return JsonResponse({
                'success': False,
                'error': 'Plate not registered in system',
                'plate_number': plate_number,
                'transaction_id': str(transaction.transaction_id)
            }, status=404)

        # 3. Process payment using registered phone number
        payment_result = process_payment(
            license_plate=plate_number,
            amount=toll_amount,
            transaction_id=str(transaction.transaction_id),
            phone_number=reg.phone_number
        )
        
        print(f"Payment result: {payment_result}")
        
    # 4. Update transaction status
        if payment_result['success']:
            transaction.status = 'COMPLETED'
            transaction.payment_method = payment_result.get('payment_method', 'ECOCASH')
            transaction.payment_reference = payment_result.get('reference', '')
        else:
            transaction.status = 'FAILED'
            transaction.error_message = payment_result.get('error', 'Payment failed')
        
        transaction.save()
        
    # 5. Store blockchain audit trail
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
        
    # 6. Log ANPR result
        ANPRResult.objects.create(
            detected_plate=plate_number,
            confidence=confidence,
            transaction=transaction,
            processing_time=payment_result.get('processing_time', 0),
            detection_method='opencv_real'
        )
        
    # 7. Log audit trail
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
            'balance': payment_result.get('balance', 0),
            'requires_funding': payment_result.get('requires_funding', False),
            'funding_amount': payment_result.get('funding_amount', 0),
            'phone_number': payment_result.get('phone_number', ''),
            'payment_provider': payment_result.get('payment_provider', ''),
            'processing_time': payment_result.get('processing_time', 0)
        })
        
    except json.JSONDecodeError:
        print("ERROR: Invalid JSON in request")
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data',
            'plate_number': 'Unknown',
            'amount': 0,
            'status': 'FAILED',
            'transaction_id': 'N/A',
            'blockchain_hash': None,
            'message': 'Invalid request format'
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
            'error': f'Transaction processing failed: {str(e)}',
            'plate_number': data.get('plate_number', 'Unknown'),
            'amount': 0,
            'status': 'FAILED',
            'transaction_id': 'N/A',
            'blockchain_hash': None,
            'message': f'Error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def initiate_paynow_funding(request):
    """
    Initiate Paynow payment for account funding
    """
    try:
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        amount = data.get('amount', 10.00)
        payment_provider = data.get('payment_provider', 'ECOCASH')
        
        print(f"Initiating Paynow funding: {phone_number}, ${amount}, {payment_provider}")
        
        # Validate phone number format
        if not phone_number or not phone_number.startswith('07'):
            return JsonResponse({
                'success': False,
                'error': 'Invalid phone number format',
                'message': 'Phone number must be in format 077xxxxxxx or 071xxxxxxx'
            })
        
        # Determine payment method based on phone number
        if phone_number.startswith('071'):
            actual_provider = 'ONEMONEY'
            method_name = 'OneMoney'
        elif phone_number.startswith('077'):
            actual_provider = 'ECOCASH'
            method_name = 'EcoCash'
        else:
            return JsonResponse({
                'success': False,
                'error': 'Unsupported network',
                'message': 'Only NetOne (071) and Econet (077) numbers are supported'
            })
        
        # Create Paynow payment request (simulate for now)
        import uuid
        poll_url = f"/api/payment-status/{uuid.uuid4()}"
        
        # For now, simulate successful payment initiation
        payment_success = True
        
        if payment_success:
            # Log funding attempt
            AuditLog.objects.create(
                user=request.user,
                action='FUNDING_INITIATED',
                details={
                    'phone': phone_number,
                    'amount': amount,
                    'provider': actual_provider,
                    'poll_url': poll_url
                },
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': f'{method_name} payment request sent to {phone_number}. Please check your phone and authorize the $${amount:.2f} payment.',
                'poll_url': poll_url,
                'payment_provider': actual_provider,
                'amount': amount
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Payment initiation failed',
                'message': 'Could not initiate mobile payment'
            })
            
    except Exception as e:
        print(f"Error initiating Paynow funding: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'System error occurred while initiating payment'
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


@login_required
@require_GET
def critical_feedback_alerts(request):
    """Return open feedback threads labeled CRITICAL for alert badges."""
    threads = FeedbackThread.objects.filter(severity='CRITICAL', status='OPEN').order_by('-last_activity')[:20]
    return JsonResponse({
        'count': threads.count(),
        'items': [
            {
                'id': t.id,
                'subject': t.subject,
                'severity': t.severity,
                'status': t.status,
                'last_activity': t.last_activity.isoformat(),
            } for t in threads
        ]
    })


@login_required
@require_GET
def pending_reply_notifications(request):
    """Return replies that are pending or unread, optionally scoped to the current user."""
    # Replies awaiting action: status=PENDING or unread ones in OPEN threads assigned to user
    base_qs = FeedbackReply.objects.select_related('thread')

    # If assigned_to is set, highlight unread in their threads
    unread_qs = base_qs.filter(is_read=False, thread__status='OPEN')
    if request.user.is_authenticated:
        unread_qs = unread_qs.filter(models.Q(thread__assigned_to=request.user) | models.Q(thread__assigned_to__isnull=True))

    pending_qs = base_qs.filter(status='PENDING', thread__status='OPEN')
    replies = (unread_qs | pending_qs).order_by('-created_at').distinct()[:20]

    return JsonResponse({
        'count': replies.count(),
        'items': [
            {
                'id': r.id,
                'thread_id': r.thread_id,
                'thread_subject': r.thread.subject,
                'status': r.status,
                'is_read': r.is_read,
                'created_at': r.created_at.isoformat(),
            } for r in replies
        ]
    })


@login_required
@require_POST
@csrf_exempt
def manual_review_update(request):
    """Allow manual correction of a transaction's plate and attempt payment if registered."""
    try:
        payload = json.loads(request.body)
        tx_id = payload.get('transaction_id')
        plate = payload.get('plate_number')
        if not tx_id or not plate:
            return JsonResponse({'success': False, 'error': 'transaction_id and plate_number required'}, status=400)

        tx = Transaction.objects.get(transaction_id=tx_id)
        tx.license_plate = plate.upper()
        tx.confidence = max(tx.confidence, 0.7)  # mark as reviewed
        tx.status = 'PROCESSING'
        tx.save()

        # Lookup registration
        reg = PlateRegistration.objects.filter(normalized_plate=normalize_plate(plate), is_active=True).first()
        if not reg:
            tx.status = 'FAILED'
            tx.error_message = 'Plate not registered'
            tx.save()
            return JsonResponse({'success': False, 'error': 'Plate not registered'}, status=404)

        # Process payment
        payment_result = process_payment(
            license_plate=tx.license_plate,
            amount=float(tx.toll_amount),
            transaction_id=tx.transaction_id,
            phone_number=reg.phone_number
        )

        if payment_result['success']:
            tx.status = 'COMPLETED'
            tx.payment_method = payment_result.get('payment_method', 'ECOCASH')
            tx.payment_reference = payment_result.get('reference', '')
        else:
            tx.status = 'FAILED'
            tx.error_message = payment_result.get('error', 'Payment failed')
        tx.save()

        return JsonResponse({
            'success': payment_result['success'],
            'transaction_id': tx.transaction_id,
            'status': tx.status,
            'payment_method': tx.payment_method,
            'payment_reference': tx.payment_reference,
        })
    except Transaction.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Transaction not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# Customer Portal Views
@login_required
def customer_portal(request):
    """Customer portal dashboard showing account balance, recent transactions, and plates"""
    profile = get_or_create_profile(request.user)
    
    # Get user's plate registrations
    user_plates = PlateRegistration.objects.filter(user=request.user)
    
    # Get user's recent transactions
    recent_transactions = Transaction.objects.filter(
        Q(user=request.user) | Q(license_plate__in=[p.license_plate for p in user_plates])
    ).order_by('-timestamp')[:10]
    
    # Get recent account transactions
    account_transactions = AccountTransaction.objects.filter(user=request.user)[:5]
    
    context = {
        'profile': profile,
        'user_plates': user_plates,
        'recent_transactions': recent_transactions,
        'account_transactions': account_transactions,
    }
    return render(request, 'dashboard/customer_portal.html', context)


@login_required
def customer_transactions(request):
    """Customer's transaction history"""
    profile = get_or_create_profile(request.user)
    user_plates = PlateRegistration.objects.filter(user=request.user)
    
    # Get all transactions for user's plates
    transactions = Transaction.objects.filter(
        Q(user=request.user) | Q(license_plate__in=[p.license_plate for p in user_plates])
    ).order_by('-timestamp')
    
    # Pagination
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'profile': profile,
        'page_obj': page_obj,
        'transactions': page_obj,
    }
    return render(request, 'dashboard/customer_transactions.html', context)


@login_required
@require_POST
@csrf_exempt
def add_funds(request):
    """Add funds to customer account using Paynow"""
    try:
        data = json.loads(request.body)
        amount = float(data.get('amount', 0))
        phone_number = data.get('phone_number', '')
        
        if amount <= 0:
            return JsonResponse({'success': False, 'error': 'Invalid amount'}, status=400)
        
        if amount > 1000:  # Limit to $1000 per transaction
            return JsonResponse({'success': False, 'error': 'Amount exceeds limit of $1000'}, status=400)
        
        profile = get_or_create_profile(request.user)
        
        # Use user's phone number if not provided
        if not phone_number:
            phone_number = profile.phone_number
            
        if not phone_number:
            return JsonResponse({
                'success': False, 
                'error': 'Phone number is required for mobile payment'
            }, status=400)
        
        # Validate phone number format
        if not phone_number.startswith('07'):
            return JsonResponse({
                'success': False,
                'error': 'Invalid phone number format. Use format: 07xxxxxxxx'
            }, status=400)
        
        # Determine payment method based on phone number
        if phone_number.startswith('071'):
            payment_method = 'ONEMONEY'
            method_name = 'OneMoney'
        elif phone_number.startswith('077') or phone_number.startswith('078'):
            payment_method = 'ECOCASH' 
            method_name = 'EcoCash'
        else:
            return JsonResponse({
                'success': False,
                'error': 'Unsupported network. Only NetOne (071) and Econet (077/078) supported.'
            }, status=400)
        
        # Initiate Paynow payment
        from payments.ecocash_api import initiate_paynow_payment
        
        payment_result = initiate_paynow_payment(
            phone_number=phone_number,
            amount=amount,
            method=payment_method.lower(),
            description=f"Account funding - ${amount:.2f}"
        )
        
        if payment_result.get('success'):
            # Log funding attempt
            AuditLog.objects.create(
                user=request.user,
                action='FUNDING_INITIATED',
                details={
                    'amount': amount,
                    'phone': phone_number,
                    'method': payment_method,
                    'poll_url': payment_result.get('poll_url'),
                    'paynow_reference': payment_result.get('paynow_reference')
                },
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': f'{method_name} payment request sent to {phone_number}. Please check your phone and authorize the payment.',
                'payment_method': payment_method,
                'payment_reference': payment_result.get('payment_reference'),
                'poll_url': payment_result.get('poll_url'),
                'browser_url': payment_result.get('browser_url'),
                'phone_number': phone_number,
                'amount': amount,
                'paynow_reference': payment_result.get('paynow_reference')
            })
        else:
            error_msg = payment_result.get('message', 'Payment initiation failed')
            logger.error(f"Paynow funding failed for user {request.user.id}: {error_msg}")
            
            return JsonResponse({
                'success': False,
                'error': error_msg,
                'payment_method': payment_method
            }, status=400)
            
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': 'Invalid request data'}, status=400)
    except Exception as e:
        logger.error(f"Add funds error: {e}")
        return JsonResponse({'success': False, 'error': 'System error occurred'}, status=500)


@login_required
def account_statements(request):
    """Customer account statements and transaction history"""
    profile = get_or_create_profile(request.user)
    
    # Get account transactions
    account_transactions = AccountTransaction.objects.filter(user=request.user).order_by('-timestamp')
    
    # Calculate monthly summary
    from django.db.models import Sum
    from datetime import datetime, timedelta
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    monthly_summary = AccountTransaction.objects.filter(
        user=request.user,
        timestamp__gte=thirty_days_ago
    ).aggregate(
        total_credits=Sum('amount', filter=Q(transaction_type='CREDIT')),
        total_debits=Sum('amount', filter=Q(transaction_type__in=['DEBIT', 'TOLL_PAYMENT']))
    )
    
    # Pagination
    paginator = Paginator(account_transactions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'profile': profile,
        'page_obj': page_obj,
        'monthly_summary': monthly_summary,
    }
    return render(request, 'dashboard/account_statements.html', context)


@login_required
def manage_user_plates(request):
    """Customer can manage their own plate registrations"""
    profile = get_or_create_profile(request.user)
    user_plates = PlateRegistration.objects.filter(user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            license_plate = request.POST.get('license_plate', '').strip().upper()
            phone_number = request.POST.get('phone_number', '').strip()
            owner_name = request.POST.get('owner_name', '').strip()
            
            if not license_plate or not phone_number:
                context = {
                    'profile': profile,
                    'user_plates': user_plates,
                    'error': 'License plate and phone number are required'
                }
                return render(request, 'dashboard/manage_user_plates.html', context)
            
            # Check if plate already exists
            existing = PlateRegistration.objects.filter(
                normalized_plate=normalize_plate(license_plate)
            ).first()
            
            if existing:
                context = {
                    'profile': profile,
                    'user_plates': user_plates,
                    'error': 'This license plate is already registered'
                }
                return render(request, 'dashboard/manage_user_plates.html', context)
            
            # Create new plate registration
            PlateRegistration.objects.create(
                user=request.user,
                license_plate=license_plate,
                phone_number=phone_number,
                owner_name=owner_name or request.user.get_full_name(),
                plate_image=request.FILES.get('plate_image')
            )
            
            return redirect('manage_user_plates')
            
        elif action == 'delete':
            plate_id = request.POST.get('plate_id')
            try:
                plate = PlateRegistration.objects.get(id=plate_id, user=request.user)
                plate.delete()
                return redirect('manage_user_plates')
            except PlateRegistration.DoesNotExist:
                pass
                
        elif action == 'toggle':
            plate_id = request.POST.get('plate_id')
            try:
                plate = PlateRegistration.objects.get(id=plate_id, user=request.user)
                plate.is_active = not plate.is_active
                plate.save()
                return redirect('manage_user_plates')
            except PlateRegistration.DoesNotExist:
                pass
    
    context = {
        'profile': profile,
        'user_plates': user_plates,
    }
    return render(request, 'dashboard/manage_user_plates.html', context)


# Enhanced home view with role-based content
@login_required
def home(request):
    """Role-based home dashboard"""
    profile = get_or_create_profile(request.user)
    print("user is a "+str(profile.role))
    if profile.role == UserRole.CUSTOMER:
        # Redirect customers to their portal
        return redirect('customer_portal')
    
    # Admin/Operator dashboard
    recent_transactions = Transaction.objects.all()[:10]
    
    # Get some stats
    today = timezone.now().date()
    daily_stats = {
        'total_transactions': Transaction.objects.filter(timestamp__date=today).count(),
        'successful_transactions': Transaction.objects.filter(
            timestamp__date=today, status='COMPLETED'
        ).count(),
        'total_amount': Transaction.objects.filter(
            timestamp__date=today, status='COMPLETED'
        ).aggregate(Sum('toll_amount'))['toll_amount__sum'] or 0,
    }
    
    context = {
        'profile': profile,
        'recent_transactions': recent_transactions,
        'daily_stats': daily_stats,
    }
    return render(request, "dashboard/home.html", context)


# User Management Views (Admin only)
@admin_required
def manage_users(request):
    """Admin view to manage users - list, create, edit, delete"""
    from django.contrib.auth.models import User
    from django.contrib.auth.hashers import make_password
    
    flash = None
    error = None
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            password = request.POST.get('password', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()
            role = request.POST.get('role')
            initial_balance = request.POST.get('initial_balance', '0')
            
            try:
                if not username or not password:
                    error = 'Username and password are required'
                elif not phone_number:
                    error = 'Phone number is required for payment processing'
                elif User.objects.filter(username=username).exists():
                    error = 'Username already exists'
                elif role not in [choice[0] for choice in UserRole.choices]:
                    error = 'Invalid role selected'
                else:
                    # Create user
                    user = User.objects.create(
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        password=make_password(password)
                    )
                    
                    # Create user profile
                    profile = UserProfile.objects.create(
                        user=user,
                        role=role,
                        phone_number=phone_number,
                        account_balance=Decimal(initial_balance) if initial_balance else Decimal('0.00')
                    )
                    
                    flash = f'User {username} created successfully'
                    
            except Exception as e:
                error = f'Error creating user: {str(e)}'
                
        elif action == 'update':
            user_id = request.POST.get('user_id')
            try:
                user = User.objects.get(id=user_id)
                profile = get_or_create_profile(user)
                
                # Update user fields
                user.email = request.POST.get('email', '').strip()
                user.first_name = request.POST.get('first_name', '').strip()
                user.last_name = request.POST.get('last_name', '').strip()
                user.is_active = request.POST.get('is_active') == 'on'
                user.save()
                
                # Update profile
                role = request.POST.get('role')
                phone_number = request.POST.get('phone_number', '').strip()
                if role in [choice[0] for choice in UserRole.choices]:
                    profile.role = role
                if phone_number:
                    profile.phone_number = phone_number
                profile.save()
                
                flash = f'User {user.username} updated successfully'
                
            except User.DoesNotExist:
                error = 'User not found'
            except Exception as e:
                error = f'Error updating user: {str(e)}'
                
        elif action == 'delete':
            user_id = request.POST.get('user_id')
            try:
                user = User.objects.get(id=user_id)
                if user.id == request.user.id:
                    error = 'Cannot delete your own account'
                else:
                    username = user.username
                    user.delete()
                    flash = f'User {username} deleted successfully'
            except User.DoesNotExist:
                error = 'User not found'
            except Exception as e:
                error = f'Error deleting user: {str(e)}'
                
        elif action == 'reset_password':
            user_id = request.POST.get('user_id')
            new_password = request.POST.get('new_password', '').strip()
            try:
                if not new_password:
                    error = 'New password is required'
                else:
                    user = User.objects.get(id=user_id)
                    user.password = make_password(new_password)
                    user.save()
                    # Reset TOTP for security
                    profile = get_or_create_profile(user)
                    profile.totp_enabled = False
                    profile.totp_secret = None
                    profile.save()
                    flash = f'Password reset for {user.username}. TOTP has been disabled.'
            except User.DoesNotExist:
                error = 'User not found'
            except Exception as e:
                error = f'Error resetting password: {str(e)}'
    
    # Get all users with their profiles
    from django.contrib.auth.models import User
    users = User.objects.select_related('userprofile').all().order_by('username')
    
    # Handle search
    search_query = request.GET.get('q', '').strip()
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    context = {
        'users': users,
        'search_query': search_query,
        'user_roles': UserRole.choices,
        'flash': flash,
        'error': error,
    }
    return render(request, 'dashboard/manage_users.html', context)


@admin_required  
def user_detail(request, user_id):
    """Admin view to see detailed information about a user"""
    from django.contrib.auth.models import User
    
    try:
        user = User.objects.get(id=user_id)
        profile = get_or_create_profile(user)
        
        # Get user's plates
        user_plates = PlateRegistration.objects.filter(user=user)
        
        # Get user's transactions
        user_transactions = Transaction.objects.filter(user=user).order_by('-timestamp')[:20]
        
        # Get user's account transactions
        account_transactions = AccountTransaction.objects.filter(user=user).order_by('-timestamp')[:20]
        
        context = {
            'selected_user': user,
            'profile': profile,
            'user_plates': user_plates,
            'user_transactions': user_transactions,
            'account_transactions': account_transactions,
        }
        return render(request, 'dashboard/user_detail.html', context)
        
    except User.DoesNotExist:
        return redirect('manage_users')

@csrf_exempt
@require_http_methods(["POST"])
def check_payment_status(request):
    """Check Paynow payment status using poll URL"""
    from payments.ecocash_api import check_paynow_payment_status
    
    try:
        data = json.loads(request.body)
        poll_url = data.get('poll_url')
        
        if not poll_url:
            return JsonResponse({
                'success': False,
                'message': 'Poll URL required',
                'status': 'ERROR'
            })
        
        # Check payment status with Paynow
        payment_status = check_paynow_payment_status(poll_url)
        
        # If payment was successful, update user's account balance
        if payment_status.get('success') and payment_status.get('status') == 'Paid':
            # Find the pending transaction and update user balance
            amount = payment_status.get('amount', 0)
            paynow_ref = payment_status.get('paynow_reference', '')
            
            # Update user's account balance
            if hasattr(request.user, 'userprofile'):
                profile = request.user.userprofile
                profile.account_balance += amount
                profile.save()
                
                # Create account transaction record
                AccountTransaction.objects.create(
                    user=request.user,
                    transaction_type='DEPOSIT',
                    amount=amount,
                    description=f'Paynow payment - Ref: {paynow_ref}',
                    balance_before=profile.account_balance - amount,
                    balance_after=profile.account_balance,
                    reference_number=paynow_ref
                )
                
                payment_status['new_balance'] = float(profile.account_balance)
        
        return JsonResponse(payment_status)
        
    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Error checking payment status',
            'status': 'ERROR'
        })


@csrf_exempt
@require_http_methods(["POST"])
def paynow_callback(request):
    """
    Handle Paynow payment callback/webhook
    This endpoint is called by Paynow when payment status changes
    """
    try:
        # Parse Paynow callback data
        callback_data = {}
        if request.content_type == 'application/x-www-form-urlencoded':
            for key, value in request.POST.items():
                callback_data[key] = value
        else:
            # Handle raw POST data
            for line in request.body.decode('utf-8').split('&'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    callback_data[key] = value
        
        logger.info(f"Paynow callback received: {callback_data}")
        
        # Extract relevant data
        reference = callback_data.get('reference', '')
        status = callback_data.get('status', '').lower()
        amount = float(callback_data.get('amount', '0'))
        paynow_reference = callback_data.get('paynowreference', '')
        
        if status == 'paid' and amount > 0:
            # Find user by reference or phone number
            # The reference should contain user info or we can look up by audit log
            
            try:
                # Look up the funding attempt in audit logs
                audit_log = AuditLog.objects.filter(
                    action='FUNDING_INITIATED',
                    details__paynow_reference=paynow_reference
                ).first()
                
                if audit_log:
                    user = audit_log.user
                    profile = user.userprofile
                    
                    # Check if payment was already processed
                    existing_transaction = AccountTransaction.objects.filter(
                        user=user,
                        description__contains=f'Paynow - {paynow_reference}'
                    ).exists()
                    
                    if not existing_transaction:
                        # Add funds to user account
                        balance_before = profile.account_balance
                        profile.account_balance += Decimal(str(amount))
                        profile.save()
                        
                        # Create account transaction record
                        AccountTransaction.objects.create(
                            user=user,
                            transaction_type='CREDIT',
                            amount=Decimal(str(amount)),
                            description=f'Paynow payment - {paynow_reference}',
                            reference_number=reference,
                            balance_before=balance_before,
                            balance_after=profile.account_balance
                        )
                        
                        # Log successful payment
                        AuditLog.objects.create(
                            user=user,
                            action='FUNDING_COMPLETED',
                            details={
                                'amount': amount,
                                'paynow_reference': paynow_reference,
                                'reference': reference,
                                'new_balance': float(profile.account_balance)
                            },
                            ip_address=request.META.get('REMOTE_ADDR')
                        )
                        
                        logger.info(f"Payment processed: ${amount} added to user {user.id}, new balance: ${profile.account_balance}")
                    else:
                        logger.warning(f"Duplicate payment callback for reference {paynow_reference}")
                else:
                    logger.warning(f"No funding attempt found for paynow reference: {paynow_reference}")
                    
            except Exception as e:
                logger.error(f"Error processing payment callback: {e}")
                
        # Always return OK to Paynow (they expect this response)
        return JsonResponse({'status': 'OK'})
        
    except Exception as e:
        logger.error(f"Paynow callback error: {e}")
        return JsonResponse({'status': 'ERROR'})
