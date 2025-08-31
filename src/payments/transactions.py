from datetime import datetime
from .ecocash_api import simulate_charge
from blockchain.ledger import append_audit


def process_payment(license_plate: str, amount: float) -> dict:
    """
    Process payment for a license plate
    Returns payment result with status and details
    """
    try:
        # Generate account ID from license plate
        account_id = f"eco-{license_plate.replace(' ', '').replace('·', '').replace('-', '')}"
        
        # Attempt payment
        payment_status = simulate_charge(account_id, amount)
        
        # Create transaction record
        transaction_data = {
            'plate': license_plate,
            'timestamp': datetime.utcnow().isoformat(),
            'amount': amount,
            'payment_method': 'EcoCash',
            'status': payment_status,
            'account_id': account_id
        }
        
        # Log to blockchain
        audit_hash = append_audit(transaction_data)
        transaction_data['audit_hash'] = audit_hash
        
        if payment_status == 'SUCCESS':
            message = f"Payment of ${amount:.2f} processed successfully for {license_plate}"
        else:
            message = f"Payment failed for {license_plate}. Please try alternative payment method."
        
        return {
            'status': payment_status,
            'message': message,
            'transaction_data': transaction_data,
            'audit_hash': audit_hash
        }
        
    except Exception as e:
        return {
            'status': 'ERROR',
            'message': f"Payment processing error: {str(e)}",
            'transaction_data': None,
            'audit_hash': None
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
