from datetime import datetime
from .ecocash_api import simulate_charge
from blockchain.ledger import append_audit


def process_payment(license_plate: str, amount: float, transaction_id: str | None = None, phone_number: str | None = None) -> dict:
    """
    Process payment for a license plate, optionally using a registered phone number.
    Returns a result containing both legacy keys (status, audit_hash) and new keys (success, reference, payment_method).
    """
    try:
        # Generate account ID: prefer phone if provided
        if phone_number:
            account_id = f"eco-msisdn-{phone_number}"
        else:
            account_id = f"eco-{license_plate.replace(' ', '').replace('·', '').replace('-', '')}"
        
        # Attempt payment
        payment_status = simulate_charge(account_id, amount)
        
        # Create transaction record
        transaction_data = {
            'plate': license_plate,
            'timestamp': datetime.utcnow().isoformat(),
            'amount': amount,
            'payment_method': 'ECOCASH',
            'status': payment_status,
            'account_id': account_id,
            'transaction_id': transaction_id,
            'phone_number': phone_number,
        }
        
        # Log to blockchain
        audit_hash = append_audit(transaction_data)
        transaction_data['audit_hash'] = audit_hash
        
        if payment_status == 'SUCCESS':
            message = f"Payment of ${amount:.2f} processed successfully for {license_plate}"
        else:
            message = f"Payment failed for {license_plate}. Please try alternative payment method."
        
        return {
            # New fields
            'success': payment_status == 'SUCCESS',
            'message': message,
            'payment_method': 'ECOCASH',
            'reference': audit_hash[:20],
            'balance': None,
            'processing_time': 0,
            # Legacy fields (kept for backward compatibility)
            'status': payment_status,
            'transaction_data': transaction_data,
            'audit_hash': audit_hash,
        }
        
    except Exception as e:
        return {
            'success': False,
            'status': 'ERROR',
            'message': f"Payment processing error: {str(e)}",
            'transaction_data': None,
            'audit_hash': None,
            'payment_method': 'ECOCASH',
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
