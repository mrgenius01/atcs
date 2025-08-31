from django.db import models
from django.contrib.auth.models import User
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
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('PENDING', 'Pending'),
    ]
    
    license_plate = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, default='EcoCash')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    gate_id = models.CharField(max_length=20, default='GATE-001')
    audit_hash = models.CharField(max_length=64, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.license_plate} - {self.status} - ${self.amount}"

    def save(self, *args, **kwargs):
        # Generate audit hash on save
        if not self.audit_hash:
            from blockchain.ledger import append_audit
            self.audit_hash = append_audit({
                'plate': self.license_plate,
                'amount': str(self.amount),
                'timestamp': self.timestamp.isoformat() if self.timestamp else '',
                'status': self.status
            })
        super().save(*args, **kwargs)


class ANPRResult(models.Model):
    """ANPR processing results model"""
    image_path = models.CharField(max_length=255, help_text="Path to processed image")
    detected_plate = models.CharField(max_length=20, blank=True, null=True, help_text="Detected license plate number")
    confidence = models.FloatField(default=0.0, help_text="Detection confidence (0-100)")
    processing_time = models.FloatField(default=0.0, help_text="Processing time in seconds")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"ANPR: {self.detected_plate or 'No plate'} ({self.confidence:.1f}%)"
