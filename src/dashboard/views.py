from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Transaction, ANPRResult, AuditLog, PlateRegistration, normalize_plate, FeedbackThread, FeedbackReply
from django.db import models
from security.auth import verify_totp, get_qr_code, get_or_create_profile
from payments.transactions import process_payment
from anpr.detector import detect_and_recognize_plate
from anpr.gemini_recognizer import recognize_plate_with_gemini


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


@login_required
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
                    obj, created = PlateRegistration.objects.update_or_create(
                        normalized_plate=normalize_plate(plate),
                        defaults={
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

    regs = PlateRegistration.objects.all().order_by('-updated_at')[:200]
    return render(request, 'dashboard/registrations.html', {
        'registrations': regs,
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
            plate_number=plate_number,
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
            plate_number=tx.license_plate,
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



