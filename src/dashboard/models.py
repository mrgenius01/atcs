from django.db import models
from django.contrib.auth.models import User, Group
from django.utils import timezone
from decimal import Decimal
import uuid
import pyotp
import qrcode
import io
import base64


# Role choices for user types
class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Administrator'
    OPERATOR = 'OPERATOR', 'Toll Operator'
    CUSTOMER = 'CUSTOMER', 'Customer'
    VIEWER = 'VIEWER', 'Read-Only Viewer'


def normalize_plate(plate: str) -> str:
    """Normalize license plate for consistent lookups (uppercase, no spaces/dots/dashes)."""
    if not plate:
        return ""
    return (
        plate.upper()
        .replace(" ", "")
        .replace("-", "")
        .replace("·", "")
    )


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CUSTOMER)
    account_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    totp_secret = models.CharField(max_length=32, blank=True)
    totp_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

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

    def can_access_admin(self):
        """Check if user can access admin features"""
        return self.role in [UserRole.ADMIN, UserRole.OPERATOR]

    def can_manage_transactions(self):
        """Check if user can manage transactions"""
        return self.role in [UserRole.ADMIN, UserRole.OPERATOR]

    def can_view_reports(self):
        """Check if user can view reports"""
        return self.role in [UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER]

    def add_funds(self, amount):
        """Add funds to user account"""
        if amount > 0:
            self.account_balance += Decimal(str(amount))
            self.save()
            return True
        return False

    def deduct_funds(self, amount):
        """Deduct funds from user account if sufficient balance"""
        amount_decimal = Decimal(str(amount))
        if self.account_balance >= amount_decimal:
            self.account_balance -= amount_decimal
            self.save()
            return True
        return False


# Account Transaction model for user fund management
class AccountTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit'),
        ('TOLL_PAYMENT', 'Toll Payment'),
        ('REFUND', 'Refund'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=200)
    balance_before = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    reference_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    related_toll_transaction = models.ForeignKey('Transaction', on_delete=models.SET_NULL, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.transaction_type} - ${self.amount} - {self.user.username}"


# Feedback and Notification models
class FeedbackThread(models.Model):
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]
    
    subject = models.CharField(max_length=200)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_feedback')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='assigned_feedback')
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-last_activity']
        
    def __str__(self):
        return f"{self.subject} ({self.severity})"


class FeedbackReply(models.Model):
    thread = models.ForeignKey(FeedbackThread, on_delete=models.CASCADE, related_name='replies')
    message = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        
    def __str__(self):
        return f"Reply to {self.thread.subject} by {self.author.username}"


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
        ('ACCOUNT_BALANCE', 'Account Balance'),
        ('ECOCASH', 'EcoCash'),
        ('ZIPIT', 'ZiPiT'),
        ('VISA', 'Visa Card'),
        ('MASTERCARD', 'Mastercard'),
        ('CASH', 'Cash'),
    ]
    
    transaction_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, help_text="User associated with transaction")
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
    image = models.ImageField(upload_to='transactions/', blank=True, null=True)
    plate_roi = models.ImageField(upload_to='transactions/roi/', blank=True, null=True)
    
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


class PlateRegistration(models.Model):
    """Maps a license plate to a user for payments."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text="Owner of this plate")
    license_plate = models.CharField(max_length=20, unique=True)
    normalized_plate = models.CharField(max_length=20, unique=True, db_index=True)
    phone_number = models.CharField(max_length=20)
    owner_name = models.CharField(max_length=100, blank=True, null=True)
    plate_image = models.ImageField(upload_to='plates/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.license_plate} -> {self.user.username} ({'active' if self.is_active else 'inactive'})"

    def save(self, *args, **kwargs):
        # Ensure normalized plate is always in sync and unique
        self.normalized_plate = normalize_plate(self.license_plate)
        super().save(*args, **kwargs)
