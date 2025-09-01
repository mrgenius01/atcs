from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import pyotp
import qrcode
import io
import base64


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    totp_secret = models.CharField(max_length=32, blank=True)
    totp_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def generate_totp_secret(self):
        """Generate a new TOTP secret for the user"""
        if not self.totp_secret:
            self.totp_secret = pyotp.random_base32()
            self.save()
        return self.totp_secret

    def get_totp_uri(self):
        """Get the TOTP URI for QR code generation"""
        if not self.totp_secret:
            self.generate_totp_secret()
        totp = pyotp.TOTP(self.totp_secret)
        return totp.provisioning_uri(
            name=self.user.username,
            issuer_name="Secure ATCS"
        )

    def get_qr_code(self):
        """Generate QR code as base64 image"""
        uri = self.get_totp_uri()
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()

    def verify_totp(self, token):
        """Verify TOTP token"""
        if not self.totp_secret:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(token, valid_window=2)


# Transaction model for storing toll transactions
class Transaction(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('ECOCASH', 'EcoCash'),
        ('ZIPIT', 'ZiPiT'),
        ('VISA', 'Visa Card'),
        ('MASTERCARD', 'Mastercard'),
        ('CASH', 'Cash'),
    ]
    
    transaction_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    license_plate = models.CharField(max_length=20)
    toll_amount = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=100, default='Main Toll Plaza')
    confidence = models.FloatField(help_text="OCR confidence level", default=0.5)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    blockchain_hash = models.CharField(max_length=64, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"Transaction {self.transaction_id} - {self.license_plate}"
    
    def save(self, *args, **kwargs):
        if self.status in ['COMPLETED', 'FAILED'] and not self.processed_at:
            self.processed_at = timezone.now()
        super().save(*args, **kwargs)


class ANPRResult(models.Model):
    """ANPR processing results model"""
    detected_plate = models.CharField(max_length=20, blank=True, null=True, help_text="Detected license plate number")
    confidence = models.FloatField(default=0.0, help_text="Detection confidence (0-1)")
    detection_method = models.CharField(max_length=50, default='opencv_real')
    processing_time = models.FloatField(default=0.0, help_text="Processing time in seconds")
    image_size = models.CharField(max_length=20, blank=True, null=True)
    detection_region = models.JSONField(blank=True, null=True, help_text="Bounding box coordinates")
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"ANPR: {self.detected_plate or 'No plate'} ({self.confidence:.1%})"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('TRANSACTION_CREATE', 'Transaction Created'),
        ('TRANSACTION_UPDATE', 'Transaction Updated'),
        ('PAYMENT_PROCESS', 'Payment Processed'),
        ('ANPR_DETECT', 'ANPR Detection'),
        ('SYSTEM_ERROR', 'System Error'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.JSONField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.action} - {self.user or 'Anonymous'} at {self.timestamp}"
