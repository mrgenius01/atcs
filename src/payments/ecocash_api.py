# Real Paynow API integration for Zimbabwe mobile payments using official SDK
from paynow import Paynow
import uuid
from typing import Dict, Optional
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def simulate_charge(account_id: str, amount: float) -> str:
    """Legacy function for backward compatibility"""
    return "SUCCESS"

def get_paynow_client():
    """Get configured Paynow client"""
    paynow_id = getattr(settings, 'PAYNOW_ID', '19347')
    paynow_key = getattr(settings, 'PAYNOW_KEY', '53f73fa2-89cb-4e3e-94cd-f0c6badd9f6a')
    
    paynow = Paynow(
        paynow_id,
        paynow_key,
        f'{settings.BASE_URL}/paynow/callback/',  # Result URL
        f'{settings.BASE_URL}/payment/return/'    # Return URL
    )
    
    return paynow

def generate_paynow_hash(values: Dict[str, str]) -> str:
    """Legacy hash function - now handled by SDK"""
    logger.warning("Using legacy hash function - consider updating to SDK methods")
    return "LEGACY_HASH"

def initiate_paynow_payment(phone_number: str, amount: float, method: str = 'ECOCASH', description: str = 'ATCS Toll Payment') -> dict:
    """
    Real Paynow API integration using official SDK
    """
    try:
        # Validate phone number format
        if not phone_number or not phone_number.startswith('07'):
            return {
                'success': False,
                'message': 'Invalid phone number format. Use format: 07xxxxxxxx',
                'error': 'INVALID_PHONE'
            }
        
        # Determine payment method based on phone number
        if phone_number.startswith('071'):
            payment_method = 'onemoney'
        elif phone_number.startswith('077') or phone_number.startswith('078'):
            payment_method = 'ecocash'
        else:
            return {
                'success': False,
                'message': 'Unsupported network. Only NetOne (071) and Econet (077/078) supported.',
                'error': 'UNSUPPORTED_NETWORK'
            }
        
        # Generate unique reference
        reference = f'ATCS{uuid.uuid4().hex[:8].upper()}'
        
        # Get Paynow client
        paynow = get_paynow_client()
        
        # Create payment
        payment = paynow.create_payment(reference, getattr(settings, 'PAYNOW_EMAIL', 'admin@atcs.com'))
        payment.add(description, amount)
        
        logger.info(f"Initiating Paynow payment for {phone_number}: ${amount}")
        
        # Send mobile payment request
        if payment_method == 'ecocash':
            response = paynow.send_mobile(payment, phone_number, "ecocash")
        elif payment_method == 'onemoney':
            response = paynow.send_mobile(payment, phone_number, "onemoney")
        else:
            return {
                'success': False,
                'message': 'Unsupported payment method',
                'error': 'UNSUPPORTED_METHOD'
            }
        
        logger.info(f"Paynow response status: {response.success}")
        
        # Check if request was successful
        if response.success:
            # Get available attributes based on SDK documentation
            poll_url = getattr(response, 'poll_url', '')
            instructions = getattr(response, 'instructions', f'Complete payment on your {payment_method} mobile app')
            
            return {
                'success': True,
                'message': f'{payment_method.title()} payment request sent to {phone_number}',
                'payment_reference': reference,
                'poll_url': poll_url,
                'browser_url': '',  # Mobile payments don't have redirect URLs
                'phone_number': phone_number,
                'amount': amount,
                'method': payment_method.upper(),
                'status': 'INITIATED',
                'instructions': instructions,
                'paynow_reference': ''  # Will be available after status check
            }
        else:
            error_msg = getattr(response, 'error', 'Unknown error')
            logger.error(f"Paynow payment failed: {error_msg}")
            return {
                'success': False,
                'message': f'Payment failed: {error_msg}',
                'error': error_msg,
                'payment_method': payment_method.upper()
            }
        
    except Exception as e:
        logger.error(f"Paynow payment error: {str(e)}")
        return {
            'success': False,
            'message': 'Payment service error. Please try again.',
            'error': str(e)
        }

def check_paynow_payment_status(poll_url: str) -> dict:
    """
    Check payment status using official Paynow SDK
    """
    try:
        # Get Paynow client
        paynow = get_paynow_client()
        
        # Check payment status
        status = paynow.check_transaction_status(poll_url)
        
        # Based on SDK documentation, status object should have .paid attribute
        if hasattr(status, 'paid') and status.paid:
            return {
                'success': True,
                'status': 'Paid',
                'amount': getattr(status, 'amount', 0),
                'reference': getattr(status, 'reference', ''),
                'paynow_reference': getattr(status, 'paynow_reference', '')
            }
        elif hasattr(status, 'status'):
            # Check the status string value
            status_value = status.status.lower() if hasattr(status.status, 'lower') else str(status.status).lower()
            
            if status_value == 'paid':
                return {
                    'success': True,
                    'status': 'Paid',
                    'amount': getattr(status, 'amount', 0),
                    'reference': getattr(status, 'reference', ''),
                    'paynow_reference': getattr(status, 'paynow_reference', '')
                }
            elif status_value in ['cancelled', 'failed']:
                return {
                    'success': False,
                    'status': 'Cancelled',
                    'reference': getattr(status, 'reference', '')
                }
            else:
                # Payment is still pending
                return {
                    'success': True,
                    'status': 'Created',  # Pending
                    'reference': getattr(status, 'reference', ''),
                    'paynow_reference': getattr(status, 'paynow_reference', '')
                }
        else:
            # Fallback - assume pending
            return {
                'success': True,
                'status': 'Created',  # Pending
                'reference': getattr(status, 'reference', ''),
                'paynow_reference': getattr(status, 'paynow_reference', '')
            }
        
    except Exception as e:
        logger.error(f"Error checking Paynow payment status: {str(e)}")
        return {
            'success': False,
            'status': 'Error',
            'error': str(e)
        }

def process_paynow_callback(request_data: dict) -> dict:
    """
    Process Paynow callback/webhook data using official SDK
    """
    try:
        paynow = get_paynow_client()
        
        # Verify the webhook data
        if paynow.is_valid_webhook(request_data):
            reference = request_data.get('reference', '')
            status = request_data.get('status', '')
            amount = request_data.get('amount', 0)
            paynow_reference = request_data.get('paynowreference', '')
            
            logger.info(f"Valid Paynow webhook received: {reference} - {status}")
            
            return {
                'success': True,
                'valid': True,
                'reference': reference,
                'status': status,
                'amount': float(amount) if amount else 0,
                'paynow_reference': paynow_reference
            }
        else:
            logger.warning("Invalid Paynow webhook received")
            return {
                'success': False,
                'valid': False,
                'error': 'Invalid webhook signature'
            }
            
    except Exception as e:
        logger.error(f"Error processing Paynow callback: {str(e)}")
        return {
            'success': False,
            'valid': False,
            'error': str(e)
        }
