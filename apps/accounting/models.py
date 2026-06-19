from django.db import models
from django.conf import settings
from apps.core.models import BaseModel, Site
from apps.finance.models import Payment
import uuid


class AccountingAccount(BaseModel):
    """Chart of accounts."""
    ACCOUNT_TYPE_CHOICES = [
        ('ASSET', 'Actif'),
        ('LIABILITY', 'Passif'),
        ('EQUITY', 'Capitaux propres'),
        ('REVENUE', 'Produit'),
        ('EXPENSE', 'Charge'),
    ]

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children'
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='accounting_accounts'
    )
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)

    class Meta:
        db_table = 'accounting_accounts'
        verbose_name = 'Compte comptable'
        verbose_name_plural = 'Comptes comptables'
        unique_together = ['code', 'site']
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def balance(self):
        debits = self.debit_lines.filter(is_active=True).aggregate(
            total=models.Sum('debit_amount')
        )['total'] or 0
        credits = self.credit_lines.filter(is_active=True).aggregate(
            total=models.Sum('credit_amount')
        )['total'] or 0

        if self.account_type in ['ASSET', 'EXPENSE']:
            return debits - credits
        return credits - debits


class JournalEntry(BaseModel):
    """Journal entry for accounting."""
    STATUS_CHOICES = [
        ('DRAFT', 'Brouillon'),
        ('POSTED', 'Validé'),
        ('CANCELLED', 'Annulé'),
    ]

    entry_number = models.CharField(max_length=50, unique=True)
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name='journal_entries'
    )
    entry_date = models.DateField()
    description = models.TextField()
    reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='journal_entries'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_journal_entries'
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posted_journal_entries'
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'journal_entries'
        verbose_name = 'Écriture comptable'
        verbose_name_plural = 'Écritures comptables'
        ordering = ['-entry_date', '-entry_number']

    def __str__(self):
        return f"{self.entry_number} - {self.entry_date}"

    def save(self, *args, **kwargs):
        if not self.entry_number:
            self.entry_number = self.generate_entry_number()
        super().save(*args, **kwargs)

    def generate_entry_number(self):
        from django.utils import timezone
        year = timezone.now().year
        month = timezone.now().month
        site_code = self.site.code if self.site else 'XX'
        count = JournalEntry.objects.filter(
            entry_number__startswith=f"JE-{site_code}-{year}{month:02d}"
        ).count() + 1
        return f"JE-{site_code}-{year}{month:02d}-{count:04d}"

    @property
    def total_debit(self):
        return self.lines.filter(is_active=True).aggregate(
            total=models.Sum('debit_amount')
        )['total'] or 0

    @property
    def total_credit(self):
        return self.lines.filter(is_active=True).aggregate(
            total=models.Sum('credit_amount')
        )['total'] or 0

    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit

    def post(self, user):
        from django.utils import timezone
        if self.is_balanced and self.status == 'DRAFT':
            self.status = 'POSTED'
            self.posted_by = user
            self.posted_at = timezone.now()
            self.save()
            return True
        return False


class JournalLine(BaseModel):
    """Individual line in a journal entry."""
    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name='lines'
    )
    account = models.ForeignKey(
        AccountingAccount,
        on_delete=models.PROTECT,
        related_name='journal_lines'
    )
    debit_account = models.ForeignKey(
        AccountingAccount,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='debit_lines'
    )
    credit_account = models.ForeignKey(
        AccountingAccount,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='credit_lines'
    )
    description = models.CharField(max_length=255, blank=True)
    debit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = 'journal_lines'
        verbose_name = 'Ligne d\'écriture'
        verbose_name_plural = 'Lignes d\'écriture'

    def __str__(self):
        return f"{self.journal_entry.entry_number} - {self.account.code}"

    @property
    def amount(self):
        return self.debit_amount or self.credit_amount

    def save(self, *args, **kwargs):
        if self.debit_amount > 0:
            self.debit_account = self.account
            self.credit_account = None
        elif self.credit_amount > 0:
            self.credit_account = self.account
            self.debit_account = None
        super().save(*args, **kwargs)
