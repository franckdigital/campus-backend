from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.core.models import BaseModel, Site, AcademicYear
from apps.students.models import Student
import uuid


class FeeType(BaseModel):
    """Type of fee (tuition, registration, etc.)."""
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    default_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_recurring = models.BooleanField(default=False)
    accounting_code = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'fee_types'
        verbose_name = 'Type de frais'
        verbose_name_plural = 'Types de frais'
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Invoice(BaseModel):
    """Invoice for student fees."""
    STATUS_CHOICES = [
        ('DRAFT', 'Brouillon'),
        ('SENT', 'Envoyée'),
        ('PARTIAL', 'Partiellement payée'),
        ('PAID', 'Payée'),
        ('OVERDUE', 'En retard'),
        ('CANCELLED', 'Annulée'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True)
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name='invoices'
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name='invoices'
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name='invoices'
    )
    
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_invoices'
    )

    class Meta:
        db_table = 'invoices'
        verbose_name = 'Facture'
        verbose_name_plural = 'Factures'
        ordering = ['-issue_date', '-invoice_number']

    def __str__(self):
        return f"{self.invoice_number} - {self.student.matricule}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        self.calculate_totals()
        super().save(*args, **kwargs)

    def generate_invoice_number(self):
        year = timezone.now().year
        site_code = self.site.code if self.site else 'XX'
        count = Invoice.objects.filter(
            invoice_number__startswith=f"INV-{site_code}-{year}"
        ).count() + 1
        return f"INV-{site_code}-{year}-{count:05d}"

    def calculate_totals(self):
        from decimal import Decimal, ROUND_HALF_UP
        self.subtotal = sum(item.total for item in self.items.all())
        self.total = self.subtotal - self.discount + self.tax
        self.balance = self.total - self.amount_paid
        
        # Round all amounts to integers (FCFA doesn't use decimals)
        self.subtotal = Decimal(str(self.subtotal)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        self.total = Decimal(str(self.total)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        self.balance = Decimal(str(self.balance)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        self.amount_paid = Decimal(str(self.amount_paid)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        
        if self.balance <= 0:
            self.status = 'PAID'
        elif self.amount_paid > 0:
            self.status = 'PARTIAL'
        elif self.due_date and self.due_date < timezone.now().date() and self.status not in ['PAID', 'CANCELLED']:
            self.status = 'OVERDUE'

    def add_payment(self, amount):
        from decimal import Decimal, ROUND_HALF_UP
        amount = Decimal(str(amount)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        self.amount_paid += amount
        self.calculate_totals()
        self.save()


class InvoiceItem(BaseModel):
    """Individual item on an invoice."""
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items'
    )
    fee_type = models.ForeignKey(
        FeeType,
        on_delete=models.PROTECT,
        related_name='invoice_items'
    )
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'invoice_items'
        verbose_name = 'Ligne de facture'
        verbose_name_plural = 'Lignes de facture'

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.description}"

    def save(self, *args, **kwargs):
        from decimal import Decimal, ROUND_HALF_UP
        # Round amounts to integers (FCFA doesn't use decimals)
        if self.unit_price:
            self.unit_price = Decimal(str(self.unit_price)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        self.total = self.quantity * self.unit_price
        self.total = Decimal(str(self.total)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        super().save(*args, **kwargs)


class PaymentMethod(BaseModel):
    """Payment method configuration."""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_online = models.BooleanField(default=False)
    requires_verification = models.BooleanField(default=False)
    accounting_code = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'payment_methods'
        verbose_name = 'Moyen de paiement'
        verbose_name_plural = 'Moyens de paiement'
        ordering = ['name']

    def __str__(self):
        return self.name


class Payment(BaseModel):
    """Payment record."""
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('SUCCESS', 'Réussi'),
        ('FAILED', 'Échoué'),
        ('CANCELLED', 'Annulé'),
        ('REFUNDED', 'Remboursé'),
    ]

    payment_number = models.CharField(max_length=50, unique=True)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    payment_date = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    proof = models.FileField(upload_to='payment_proofs/', blank=True, null=True, verbose_name='Preuve de paiement')
    
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='received_payments'
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validated_payments'
    )

    class Meta:
        db_table = 'payments'
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'
        ordering = ['-payment_date']

    def __str__(self):
        return f"{self.payment_number} - {self.amount}"

    def save(self, *args, **kwargs):
        # Round amount to nearest integer (FCFA doesn't use decimals)
        if self.amount:
            from decimal import Decimal, ROUND_HALF_UP
            self.amount = Decimal(str(self.amount)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        if not self.payment_number:
            self.payment_number = self.generate_payment_number()
        super().save(*args, **kwargs)

    def generate_payment_number(self):
        year = timezone.now().year
        count = Payment.objects.filter(
            payment_number__startswith=f"PAY-{year}"
        ).count() + 1
        return f"PAY-{year}-{count:06d}"

    def validate(self, user):
        if self.status == 'PENDING':
            self.status = 'SUCCESS'
            self.validated_at = timezone.now()
            self.validated_by = user
            self.save()
            # invoice.amount_paid is kept in sync by the on_payment_save signal
            # (recomputed as the sum of all SUCCESS payments) — don't add here too.
            # Auto-flag registration_fee_paid when a registration invoice is fully paid
            try:
                self.invoice.refresh_from_db()
                if self.invoice.status == 'PAID':
                    is_reg = (
                        self.invoice.items.filter(fee_type__code__icontains='REGISTRATION').exists()
                        or 'inscription' in (self.invoice.notes or '').lower()
                    )
                    if is_reg:
                        student = self.invoice.student
                        if not student.registration_fee_paid:
                            student.registration_fee_paid = True
                            student.save(update_fields=['registration_fee_paid'])
            except Exception:
                pass
            return True
        return False


class CashRegister(BaseModel):
    """Cash register for a site."""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='cash_registers'
    )
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_open = models.BooleanField(default=False)

    class Meta:
        db_table = 'cash_registers'
        verbose_name = 'Caisse'
        verbose_name_plural = 'Caisses'
        unique_together = ['code', 'site']

    def __str__(self):
        return f"{self.site.code} - {self.name}"


class CashSession(BaseModel):
    """Cash session for daily operations."""
    STATUS_CHOICES = [
        ('OPEN', 'Ouverte'),
        ('CLOSED', 'Fermée'),
    ]

    cash_register = models.ForeignKey(
        CashRegister,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='opened_cash_sessions'
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_cash_sessions'
    )
    
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    expected_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    difference = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'cash_sessions'
        verbose_name = 'Session de caisse'
        verbose_name_plural = 'Sessions de caisse'
        ordering = ['-opened_at']

    def __str__(self):
        return f"{self.cash_register.name} - {self.opened_at.date()}"

    def close(self, user, closing_balance, notes=''):
        from decimal import Decimal
        
        total_cash_in = self.transactions.filter(
            transaction_type='IN', is_active=True
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        
        total_cash_out = self.transactions.filter(
            transaction_type='OUT', is_active=True
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        
        self.expected_balance = self.opening_balance + total_cash_in - total_cash_out
        self.closing_balance = closing_balance
        self.difference = closing_balance - self.expected_balance
        self.closed_by = user
        self.closed_at = timezone.now()
        self.status = 'CLOSED'
        self.notes = notes
        self.save()
        
        self.cash_register.current_balance = closing_balance
        self.cash_register.is_open = False
        self.cash_register.save()


class CashTransaction(BaseModel):
    """Individual cash transaction."""
    TRANSACTION_TYPE_CHOICES = [
        ('IN', 'Entrée'),
        ('OUT', 'Sortie'),
    ]

    session = models.ForeignKey(
        CashSession,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cash_transactions'
    )
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    reference = models.CharField(max_length=100, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_transactions'
    )

    class Meta:
        db_table = 'cash_transactions'
        verbose_name = 'Transaction de caisse'
        verbose_name_plural = 'Transactions de caisse'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.description}"


class BankAccount(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('CHECKING', 'Compte courant'),
        ('SAVINGS', 'Compte épargne'),
        ('PAYROLL', 'Compte salaires'),
        ('INVESTMENT', 'Investissement'),
    ]
    site = models.ForeignKey('core.Site', on_delete=models.CASCADE, related_name='bank_accounts', null=True, blank=True)
    name = models.CharField(max_length=200)
    bank_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=100)
    iban = models.CharField(max_length=50, blank=True)
    swift = models.CharField(max_length=20, blank=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default='CHECKING')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='FCFA')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.bank_name}"


class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('SALARY', 'Salaires'),
        ('INFRASTRUCTURE', 'Infrastructure'),
        ('SUPPLIES', 'Fournitures'),
        ('UTILITIES', 'Services (eau/élec)'),
        ('MAINTENANCE', 'Entretien'),
        ('MARKETING', 'Marketing'),
        ('TRANSPORT', 'Transport'),
        ('OTHER', 'Autre'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('APPROVED', 'Approuvé'),
        ('PAID', 'Payé'),
        ('CANCELLED', 'Annulé'),
    ]
    site = models.ForeignKey('core.Site', on_delete=models.CASCADE, related_name='expenses', null=True, blank=True)
    label = models.CharField(max_length=300)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='OTHER')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()
    description = models.TextField(blank=True)
    payment_method = models.ForeignKey('PaymentMethod', on_delete=models.SET_NULL, null=True, blank=True)
    bank_account = models.ForeignKey('BankAccount', on_delete=models.SET_NULL, null=True, blank=True)
    receipt_file = models.FileField(upload_to='expenses/receipts/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_expenses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.label} - {self.amount} FCFA"


# Signal to auto-create enrollment when registration fee invoice is created
@receiver(post_save, sender=Invoice)
def create_enrollment_on_registration_invoice(sender, instance, created, **kwargs):
    """
    Automatically create enrollment when registration fee invoice is created.
    This allows academic path to display immediately, regardless of payment status.
    """
    # Only proceed if invoice has a student
    if not instance.student:
        return
    
    # Check if invoice contains registration fee (frais d'inscription)
    has_registration_fee = instance.items.filter(
        fee_type__code__icontains='inscription'
    ).exists()
    
    if not has_registration_fee:
        return
    
    # Import here to avoid circular imports
    from apps.academic.models import Enrollment, Class
    
    # Check if student already has an enrollment for this academic year
    existing_enrollment = Enrollment.objects.filter(
        student=instance.student,
        academic_year=instance.academic_year
    ).exists()
    
    if existing_enrollment:
        return  # Enrollment already exists, don't create duplicate
    
    # Try to find a class for the student
    # Option 1: Get from latest enrollment
    latest_enrollment = instance.student.enrollments.select_related('class_obj').order_by('-created_at').first()
    
    if latest_enrollment:
        # Use the same class from previous enrollment
        class_obj = latest_enrollment.class_obj
    else:
        # Option 2: Get any active class from the same site
        class_obj = Class.objects.filter(
            site=instance.site,
            academic_year=instance.academic_year,
            is_active=True
        ).first()
    
    # Create enrollment if we found a class
    if class_obj:
        Enrollment.objects.create(
            student=instance.student,
            class_obj=class_obj,
            academic_year=instance.academic_year,
            status='ENROLLED',
            is_active=True
        )
        print(f"✅ Enrollment auto-created for student {instance.student.matricule} in class {class_obj.name}")
    else:
        print(f"⚠️ No class found for student {instance.student.matricule} - enrollment not created")


class FeeConfiguration(BaseModel):
    """Barème des frais de scolarité et d'inscription par site / filière / niveau / année."""
    site = models.ForeignKey(
        Site, on_delete=models.CASCADE, related_name='fee_configurations',
        null=True, blank=True, verbose_name="Site"
    )
    program = models.ForeignKey(
        'academic.Program', on_delete=models.CASCADE, related_name='fee_configurations',
        null=True, blank=True, verbose_name="Filière"
    )
    level = models.ForeignKey(
        'academic.Level', on_delete=models.CASCADE, related_name='fee_configurations',
        null=True, blank=True, verbose_name="Niveau"
    )
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name='fee_configurations',
        null=True, blank=True, verbose_name="Année académique"
    )
    registration_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Frais d'inscription")
    tuition_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Frais de scolarité")
    label = models.CharField(max_length=200, blank=True, verbose_name="Libellé")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'fee_configurations'
        verbose_name = "Configuration des frais"
        verbose_name_plural = "Configurations des frais"
        ordering = ['site', 'program', 'level']

    def __str__(self):
        parts = [self.site.name if self.site else 'Tous sites',
                 self.program.name if self.program else 'Toutes filières',
                 self.level.name if self.level else 'Tous niveaux']
        return ' / '.join(parts)

    @classmethod
    def get_for_enrollment(cls, site, level, academic_year=None):
        """Return the best-matching fee config for a given site + level."""
        qs = cls.objects.filter(is_active=True)
        # Most specific: site + level + year
        if academic_year:
            cfg = qs.filter(site=site, level=level, academic_year=academic_year).first()
            if cfg:
                return cfg
        # site + level (any year)
        cfg = qs.filter(site=site, level=level, academic_year=None).first()
        if cfg:
            return cfg
        # site + program
        if level and level.program_id:
            cfg = qs.filter(site=site, program_id=level.program_id, level=None).first()
            if cfg:
                return cfg
        # site only
        cfg = qs.filter(site=site, level=None, program=None).first()
        if cfg:
            return cfg
        # global fallback
        return qs.filter(site=None, level=None, program=None).first()
