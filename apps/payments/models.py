from django.db import models
from django.conf import settings
from apps.core.models import BaseModel, Site
from apps.finance.models import Invoice, Payment, PaymentMethod
import uuid


class CinetPayConfig(BaseModel):
    """CinetPay configuration per site."""
    site = models.OneToOneField(
        Site,
        on_delete=models.CASCADE,
        related_name='cinetpay_config'
    )
    api_key = models.CharField(max_length=255)
    cinetpay_site_id = models.CharField(max_length=100)
    secret_key = models.CharField(max_length=255)
    notify_url = models.URLField()
    return_url = models.URLField(blank=True)
    cancel_url = models.URLField(blank=True)
    is_sandbox = models.BooleanField(default=True)

    class Meta:
        db_table = 'cinetpay_configs'
        verbose_name = 'Configuration CinetPay'
        verbose_name_plural = 'Configurations CinetPay'

    def __str__(self):
        return f"CinetPay - {self.site.name}"


class CinetPayTransaction(BaseModel):
    """CinetPay transaction record."""
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('SUCCESS', 'Réussi'),
        ('FAILED', 'Échoué'),
        ('CANCELLED', 'Annulé'),
    ]

    transaction_id = models.CharField(max_length=100, unique=True)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='cinetpay_transactions'
    )
    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cinetpay_transaction'
    )
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='XOF')
    
    cinetpay_transaction_id = models.CharField(max_length=100, blank=True)
    payment_url = models.URLField(blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    operator_id = models.CharField(max_length=100, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    status_message = models.TextField(blank=True)
    
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    callback_data = models.JSONField(default=dict, blank=True)
    
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='initiated_cinetpay_transactions'
    )

    class Meta:
        db_table = 'cinetpay_transactions'
        verbose_name = 'Transaction CinetPay'
        verbose_name_plural = 'Transactions CinetPay'
        ordering = ['-initiated_at']

    def __str__(self):
        return f"{self.transaction_id} - {self.amount} {self.currency}"

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
        super().save(*args, **kwargs)

    def generate_transaction_id(self):
        return f"CPT-{uuid.uuid4().hex[:12].upper()}"
