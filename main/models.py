from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.conf import settings
import uuid


# ─── Custom User ──────────────────────────────────────────────────────────────

class CustomUser(AbstractUser):
    COUNTRY_CHOICES = [
        ('NG', 'Nigeria'),
        ('GH', 'Ghana'),
        ('GB', 'United Kingdom'),
        ('US', 'United States'),
    ]
    country           = models.CharField(max_length=2, choices=COUNTRY_CHOICES, blank=True)
    phone_number      = models.CharField(max_length=20, blank=True)
    is_email_verified = models.BooleanField(default=False)
    is_vendor         = models.BooleanField(default=False)   # exchange vendor flag
    avatar            = models.ImageField(upload_to='avatars/', blank=True, null=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    
    # Override groups and user_permissions to avoid reverse accessor clashes
    groups = models.ManyToManyField(
        Group,
        related_name='customuser_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def __str__(self):
        return f"{self.username} ({self.country})"


# ─── Institution ──────────────────────────────────────────────────────────────

class Institution(models.Model):
    CATEGORY_CHOICES = [
        ('school',   'School / University'),
        ('hospital', 'Hospital / Clinic'),
        ('business', 'Business'),
        ('charity',  'Charity / NGO'),
    ]
    COUNTRY_CHOICES = [
        ('NG', 'Nigeria'),
        ('GH', 'Ghana'),
        ('GB', 'United Kingdom'),
        ('US', 'United States'),
    ]

    name         = models.CharField(max_length=255)
    category     = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    country      = models.CharField(max_length=2, choices=COUNTRY_CHOICES)
    address      = models.TextField(blank=True)
    account_name = models.CharField(max_length=255)          # who receives the money
    bank_name    = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    is_verified  = models.BooleanField(default=False)
    logo         = models.ImageField(upload_to='institutions/', blank=True, null=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_country_display()})"


# ─── Exchange Vendor ──────────────────────────────────────────────────────────

class ExchangeVendor(models.Model):
    user         = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    business_name = models.CharField(max_length=255)
    location     = models.CharField(max_length=255)
    is_verified  = models.BooleanField(default=False)
    description  = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.business_name


class VendorRate(models.Model):
    """Live rates posted by a vendor."""
    CURRENCY_PAIRS = [
        ('GBP_NGN', 'GBP → NGN'),
        ('USD_NGN', 'USD → NGN'),
        ('GBP_GHS', 'GBP → GHS'),
        ('USD_GHS', 'USD → GHS'),
    ]
    vendor       = models.ForeignKey(ExchangeVendor, on_delete=models.CASCADE, related_name='rates')
    currency_pair = models.CharField(max_length=10, choices=CURRENCY_PAIRS)
    rate         = models.DecimalField(max_digits=12, decimal_places=4)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('vendor', 'currency_pair')

    def __str__(self):
        return f"{self.vendor.business_name} — {self.currency_pair} @ {self.rate}"


# ─── Transaction ──────────────────────────────────────────────────────────────

class Transaction(models.Model):

    # Currency choices
    CURRENCY_CHOICES = [
        ('GBP', 'British Pound'),
        ('USD', 'US Dollar'),
        ('NGN', 'Nigerian Naira'),
        ('GHS', 'Ghanaian Cedi'),
    ]

    # Fee type (Fee Optimization Engine)
    FEE_TYPE_CHOICES = [
        ('sender',    'Sender pays full fee'),
        ('recipient', 'Deduct fee from recipient amount'),
        ('split',     'Split fee between both parties'),
    ]

    # Status
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('processing','Processing'),
        ('completed', 'Completed'),
        ('failed',    'Failed'),
        ('refunded',  'Refunded'),
    ]

    # Recipient type
    RECIPIENT_TYPE = [
        ('person',      'Individual'),
        ('institution', 'Institution'),
    ]

    # Core fields
    reference        = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    sender           = models.ForeignKey(
                           settings.AUTH_USER_MODEL,
                           on_delete=models.SET_NULL,
                           null=True,
                           related_name='sent_transactions'
                       )

    # Recipient — either a person or an institution
    recipient_type   = models.CharField(max_length=15, choices=RECIPIENT_TYPE, default='person')
    recipient_name   = models.CharField(max_length=255)          # for person recipients
    recipient_email  = models.EmailField(blank=True)
    recipient_account = models.CharField(max_length=50, blank=True)
    recipient_bank   = models.CharField(max_length=255, blank=True)
    institution      = models.ForeignKey(
                           Institution,
                           on_delete=models.SET_NULL,
                           null=True, blank=True,
                           related_name='transactions'
                       )

    # Amount & currency
    send_amount      = models.DecimalField(max_digits=14, decimal_places=2)
    send_currency    = models.CharField(max_length=3, choices=CURRENCY_CHOICES)
    receive_amount   = models.DecimalField(max_digits=14, decimal_places=2)
    receive_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES)
    exchange_rate    = models.DecimalField(max_digits=12, decimal_places=4)

    # Fee Optimization Engine
    fee_type         = models.CharField(max_length=15, choices=FEE_TYPE_CHOICES, default='sender')
    fee_amount       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sender_fee       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    recipient_fee    = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Fair Fee Shield
    shield_applied   = models.BooleanField(default=False)  # True if rate was volatile
    rate_at_confirm  = models.DecimalField(max_digits=12, decimal_places=4, null=True)  # locked rate

    # Status & meta
    status           = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    purpose          = models.CharField(max_length=255, blank=True)   # e.g. "School fees", "Medical"
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"TXN-{str(self.reference)[:8].upper()} | {self.send_currency} → {self.receive_currency} | {self.status}"


# ─── Notification ─────────────────────────────────────────────────────────────

class Notification(models.Model):
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message     = models.TextField()
    is_read     = models.BooleanField(default=False)
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notif → {self.user.username}"