from datetime import datetime
from decimal import Decimal
from django.db import transaction
from .ecocash_api import simulate_charge
from blockchain.ledger import append_audit


def process_payment(license_plate: str, amount: float, transaction_id: str | None = None, phone_number: str | None = None) -> dict:
    """
    Process payment for a license plate using the user's account balance.
    If balance is insufficient, return details for Paynow funding.
    """
    try:
        from dashboard.models import PlateRegistration, UserProfile, AccountTransaction
        from django.utils import timezone
        
        # Find plate registration and associated user
        plate_reg = PlateRegistration.objects.filter(
            normalized_plate=license_plate.replace(' ', '').replace('·', '').replace('-', ''),
            is_active=True
        ).first()
        
        if not plate_reg:
            return {
                'success': False,
                'message': f"Plate {license_plate} is not registered in the system",
                'payment_method': 'ACCOUNT_BALANCE',
                'reference': None,
                'balance': None,
                'processing_time': 0,
                'status': 'ERROR',
                'transaction_data': None,
                'audit_hash': None,
            }
        
        user = plate_reg.user
        user_profile = user.userprofile
        current_balance = user_profile.account_balance
        toll_amount = Decimal(str(amount))
        
        # Check if user has sufficient balance
        if current_balance >= toll_amount:
            # Process payment with account balance
            with transaction.atomic():
                # Deduct from account balance
                user_profile.account_balance -= toll_amount
                user_profile.save()
                
                # Record transaction
                AccountTransaction.objects.create(
                    user=user,
                    transaction_type='DEBIT',
                    amount=toll_amount,
                    description=f'Toll payment for plate {license_plate}',
                    reference=transaction_id or f'TOLL_{timezone.now().strftime("%Y%m%d%H%M%S")}',
                    timestamp=timezone.now()
                )
            
            # Create transaction record
            transaction_data = {
                'plate': license_plate,
                'timestamp': datetime.utcnow().isoformat(),
                'amount': float(toll_amount),
                'payment_method': 'ACCOUNT_BALANCE',
                'status': 'SUCCESS',
                'user_id': user.id,
                'transaction_id': transaction_id,
                'phone_number': user_profile.phone_number,
                'balance_after': float(user_profile.account_balance)
            }
            
            # Log to blockchain
            audit_hash = append_audit(transaction_data)
            transaction_data['audit_hash'] = audit_hash
            
            return {
                'success': True,
                'message': f"Payment of ${amount:.2f} processed successfully for {license_plate}. Remaining balance: ${user_profile.account_balance:.2f}",
                'payment_method': 'ACCOUNT_BALANCE',
                'reference': audit_hash[:20],
                'balance': float(user_profile.account_balance),
                'processing_time': 0,
                'status': 'SUCCESS',
                'transaction_data': transaction_data,
                'audit_hash': audit_hash,
            }
        else:
            # Insufficient balance - allow negative balance and prompt for funding
            new_balance = current_balance - toll_amount
            
            with transaction.atomic():
                # Allow negative balance
                user_profile.account_balance = new_balance
                user_profile.save()
                
                # Record transaction
                AccountTransaction.objects.create(
                    user=user,
                    transaction_type='DEBIT',
                    amount=toll_amount,
                    description=f'Toll payment for plate {license_plate} (Insufficient balance)',
                    reference=transaction_id or f'TOLL_{timezone.now().strftime("%Y%m%d%H%M%S")}',
                    timestamp=timezone.now()
                )
            
            # Determine mobile money provider based on phone number
            phone = user_profile.phone_number or phone_number
            payment_provider = 'ECOCASH'  # Default
            if phone and phone.startswith('071'):  # NetOne numbers
                payment_provider = 'ONEMONEY'
            elif phone and phone.startswith('077'):  # Econet numbers  
                payment_provider = 'ECOCASH'
            
            # Create transaction record
            transaction_data = {
                'plate': license_plate,
                'timestamp': datetime.utcnow().isoformat(),
                'amount': float(toll_amount),
                'payment_method': 'ACCOUNT_BALANCE',
                'status': 'SUCCESS',  # Transaction still processed, but requires funding
                'user_id': user.id,
                'transaction_id': transaction_id,
                'phone_number': phone,
                'balance_after': float(new_balance),
                'requires_funding': True,
                'funding_amount': abs(float(new_balance)) if new_balance < 0 else 10.00,  # Minimum $10 top-up
                'payment_provider': payment_provider
            }
            
            # Log to blockchain
            audit_hash = append_audit(transaction_data)
            transaction_data['audit_hash'] = audit_hash
            
            return {
                'success': True,
                'message': f"Payment processed. Account balance is now ${new_balance:.2f}. Please fund your account.",
                'payment_method': 'ACCOUNT_BALANCE',
                'reference': audit_hash[:20],
                'balance': float(new_balance),
                'processing_time': 0,
                'status': 'SUCCESS',
                'transaction_data': transaction_data,
                'audit_hash': audit_hash,
                'requires_funding': True,
                'funding_amount': abs(float(new_balance)) if new_balance < 0 else 10.00,
                'phone_number': phone,
                'payment_provider': payment_provider,
            }
            
    except Exception as e:
        return {
            'success': False,
            'status': 'ERROR',
            'message': f"Payment processing error: {str(e)}",
            'transaction_data': None,
            'audit_hash': None,
            'payment_method': 'ACCOUNT_BALANCE',
            'reference': None,
            'balance': None,
            'processing_time': 0,
        }


def simulate_transaction_log(n: int = 3):
    """Generate simulated transaction log for demo purposes"""
    out = []
    for i in range(n):
        plate = f"AB·712{i:02d}CD"
        amt = 2.00
        result = process_payment(plate, amt)
        
        out.append({
            "plate": plate,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "amount": amt,
            "payment_method": "EcoCash",
            "status": result['status'],
            "audit_hash": result.get('audit_hash', '')
        })
    return out
