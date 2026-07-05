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
                        self.invoice.items.filter(fee_type__code__iregex=r'inscri|reg').exists()
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
    """Barème des frais de scolarité et d'inscription par site / filière / niveau / année / modalité / affectation."""
    # Mirrors Student.MODALITY_CHOICES (apps.students.models) — duplicated
    # here rather than imported to avoid a cross-app import at module load
    # time; keep the two lists in sync if modalities ever change.
    MODALITY_CHOICES = [
        ('PRESENTIEL', 'Présentiel'),
        ('ELEARNING', 'E-learning'),
        ('HYBRIDE', 'Hybride'),
    ]
    # Mirrors Student.AFFECTATION_CHOICES — an "Affecté" student was assigned
    # to this school by the State's national post-bac orientation process
    # (often subsidized/reduced fees); "Non affecté" is a private-track
    # admission (full fees). Duplicated here for the same reason as above.
    AFFECTATION_CHOICES = [
        ('AFFECTE', 'Affecté (État)'),
        ('NON_AFFECTE', 'Non affecté (Privé)'),
    ]
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
    modality = models.CharField(
        max_length=20, choices=MODALITY_CHOICES, null=True, blank=True,
        verbose_name="Modalité",
        help_text="Laisser vide pour appliquer ce barème à toutes les modalités"
    )
    affectation_status = models.CharField(
        max_length=20, choices=AFFECTATION_CHOICES, null=True, blank=True,
        verbose_name="Affectation",
        help_text="Laisser vide pour appliquer ce barème aux étudiants affectés et non affectés"
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
                 self.level.name if self.level else 'Tous niveaux',
                 self.get_modality_display() if self.modality else 'Toutes modalités',
                 self.get_affectation_status_display() if self.affectation_status else 'Toutes affectations']
        return ' / '.join(parts)

    @classmethod
    def get_for_enrollment(cls, site, level, academic_year=None, modality=None, affectation_status=None):
        """Return the best-matching fee config for a given site + level +
        modality + affectation status.

        Modality and affectation are both matched strictly in the four most-
        specific tiers (an affected/state-assigned student's fee genuinely
        differs from a private-track one, same as présentiel/e-learning), then
        relaxed one at a time — affectation first, then modality — in the
        broader fallback tiers, mirroring how site/level/program already
        relax from most to least specific.
        """
        qs = cls.objects.filter(is_active=True)
        # Most specific: site + modality + affectation + level + year
        if academic_year:
            cfg = qs.filter(site=site, modality=modality, affectation_status=affectation_status,
                             level=level, academic_year=academic_year).first()
            if cfg:
                return cfg
        # site + modality + affectation + level (any year)
        cfg = qs.filter(site=site, modality=modality, affectation_status=affectation_status,
                         level=level, academic_year=None).first()
        if cfg:
            return cfg
        # site + modality + affectation + program
        if level and level.program_id:
            cfg = qs.filter(site=site, modality=modality, affectation_status=affectation_status,
                             program_id=level.program_id, level=None).first()
            if cfg:
                return cfg
        # site + modality + affectation only
        cfg = qs.filter(site=site, modality=modality, affectation_status=affectation_status,
                         level=None, program=None).first()
        if cfg:
            return cfg
        # site + modality only (any affectation)
        cfg = qs.filter(site=site, modality=modality, affectation_status=None, level=None, program=None).first()
        if cfg:
            return cfg
        # site only (any modality, any affectation)
        cfg = qs.filter(site=site, modality=None, affectation_status=None, level=None, program=None).first()
        if cfg:
            return cfg
        # global fallback (any modality, any affectation)
        return qs.filter(site=None, modality=None, affectation_status=None, level=None, program=None).first()


def recalculate_invoices_for_fee_config(fee_config, old_registration_fee, old_tuition_fee):
    """When a barème (FeeConfiguration) is edited, push the new amounts onto
    already-issued but unpaid/partially-paid invoices for students matching
    that config's scope (site/modality/level-or-program). Already-PAID and
    CANCELLED invoices are never touched. A line item is only overwritten
    when its current unit_price still equals the OLD barème amount — if a
    staff member manually discounted/scholarshiped a specific student's item
    (via add-item), it no longer matches the old barème value and is left
    alone rather than silently clobbered.

    Returns the number of invoices actually updated.
    """
    from django.db import transaction

    reg_changed = fee_config.registration_fee != old_registration_fee
    tuition_changed = fee_config.tuition_fee != old_tuition_fee
    if not reg_changed and not tuition_changed:
        return 0

    students = Student.objects.filter(is_active=True)
    if fee_config.site_id:
        students = students.filter(site_id=fee_config.site_id)
    if fee_config.modality:
        students = students.filter(modality=fee_config.modality)
    if fee_config.affectation_status:
        students = students.filter(affectation_status=fee_config.affectation_status)
    if fee_config.level_id:
        students = students.filter(
            enrollments__status='ENROLLED', enrollments__is_active=True,
            enrollments__class_obj__level_id=fee_config.level_id,
        )
    elif fee_config.program_id:
        students = students.filter(
            enrollments__status='ENROLLED', enrollments__is_active=True,
            enrollments__class_obj__level__program_id=fee_config.program_id,
        )
    if fee_config.academic_year_id:
        students = students.filter(enrollments__academic_year_id=fee_config.academic_year_id)
    students = students.distinct()

    updated = 0
    # The auto-enrollment signal is a guaranteed no-op during a price
    # recalculation (the enrollment already exists) — disconnect it for the
    # duration to avoid 2 wasted queries per invoice save.
    post_save.disconnect(create_enrollment_on_registration_invoice, sender=Invoice)
    try:
        with transaction.atomic():
            invoices = (
                Invoice.objects.filter(student__in=students, is_active=True)
                .exclude(status__in=['PAID', 'CANCELLED'])
                .prefetch_related('items__fee_type')
            )
            for invoice in invoices:
                changed = False
                for item in invoice.items.all():
                    code = (item.fee_type.code or '').upper() if item.fee_type_id else ''
                    if tuition_changed and code == 'SCOLARITE' and item.unit_price == old_tuition_fee:
                        item.unit_price = fee_config.tuition_fee
                        item.save(update_fields=['unit_price', 'total'])
                        changed = True
                    elif reg_changed and code == 'INSCRIPTION' and item.unit_price == old_registration_fee:
                        item.unit_price = fee_config.registration_fee
                        item.save(update_fields=['unit_price', 'total'])
                        changed = True
                if changed:
                    invoice.refresh_from_db()
                    invoice.save()  # recompute totals/balance/status
                    updated += 1
    finally:
        post_save.connect(create_enrollment_on_registration_invoice, sender=Invoice)

    return updated


class FeeInstallment(BaseModel):
    """One dated tranche of a FeeConfiguration's total (registration + tuition),
    e.g. "Inscription & réinscription" / "Octobre" / "Novembre" each with their
    own due_date and amount. A FeeConfiguration with no installments has the
    échéancier feature simply inactive for that site/filière/niveau (fully
    backward compatible — nothing changes for configs that don't opt in)."""
    fee_configuration = models.ForeignKey(
        FeeConfiguration, on_delete=models.CASCADE, related_name='installments',
        verbose_name="Barème"
    )
    label = models.CharField(max_length=100, verbose_name="Libellé")
    due_date = models.DateField(verbose_name="Date d'échéance",
        help_text="La tranche doit être soldée au plus tard 5 jours après cette date")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Montant")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")

    class Meta:
        db_table = 'fee_installments'
        verbose_name = "Échéance"
        verbose_name_plural = "Échéancier"
        ordering = ['order', 'due_date']

    def __str__(self):
        return f"{self.fee_configuration} — {self.label} ({self.amount} FCFA)"


def _resolve_fee_config_for_student(student, academic_year=None):
    """Shared level-resolution used by both compute_tuition_schedule_status
    and get_student_installment_schedule, so they can never drift apart."""
    level = None
    try:
        from apps.academic.models import Class as AcademicClass
        enrollment_row = student.enrollments.filter(
            status='ENROLLED', is_active=True
        ).order_by('-created_at').values_list('class_obj_id', flat=True).first()
        if enrollment_row:
            class_obj = AcademicClass.objects.select_related('level').get(pk=enrollment_row)
            level = class_obj.level
    except Exception:
        pass

    return FeeConfiguration.get_for_enrollment(
        student.site, level, academic_year,
        modality=student.modality, affectation_status=student.affectation_status
    )


def compute_tuition_schedule_status(student, academic_year=None):
    """Single source of truth for a student's échéancier compliance — called
    by the elearning permission gate, financial_summary, EnrollmentSerializer
    (teacher/admin roster badge) and the student dossier serializer, so they
    can never disagree with each other.

    Returns a dict: has_schedule, is_up_to_date, echeance_override,
    cumulative_due, cumulative_paid.
    """
    from datetime import timedelta
    from django.db.models import Sum
    from django.utils import timezone

    result = {
        'has_schedule': False,
        'is_up_to_date': True,
        'echeance_override': bool(student.echeance_override),
        'cumulative_due': 0,
        'cumulative_paid': 0,
    }

    fee_config = _resolve_fee_config_for_student(student, academic_year)
    if not fee_config:
        return result

    installments = fee_config.installments.all()
    if not installments.exists():
        return result

    result['has_schedule'] = True

    today = timezone.now().date()
    grace_cutoff = today - timedelta(days=5)
    cumulative_due = installments.filter(due_date__lte=grace_cutoff).aggregate(
        s=Sum('amount'))['s'] or 0

    cumulative_paid = Invoice.objects.filter(
        student=student, is_active=True
    ).exclude(status='CANCELLED').aggregate(s=Sum('amount_paid'))['s'] or 0

    result['cumulative_due'] = cumulative_due
    result['cumulative_paid'] = cumulative_paid
    result['is_up_to_date'] = bool(student.echeance_override) or cumulative_paid >= cumulative_due
    return result


def get_student_installment_schedule(student, academic_year=None):
    """Per-installment breakdown of a student's échéancier — powers the
    "Échéancier" table in the admin dossier's Paiements tab. Payments aren't
    tied to a specific tranche (they land against the invoice balance as a
    whole), so a given tranche's status is derived from whether the running
    cumulative amount paid covers everything due up to and including it —
    the same grace-period rule as compute_tuition_schedule_status, just
    walked one installment at a time instead of collapsed into one flag.

    Returns a dict: has_schedule, total, cumulative_paid, installments (list
    of {id, label, due_date, amount, cumulative_due, status}), where status
    is one of PAYE / PARTIEL / EN_RETARD / A_VENIR.
    """
    from datetime import timedelta
    from django.db.models import Sum
    from django.utils import timezone

    result = {'has_schedule': False, 'total': 0, 'cumulative_paid': 0, 'installments': []}

    fee_config = _resolve_fee_config_for_student(student, academic_year)
    if not fee_config:
        return result

    installments = list(fee_config.installments.all())
    if not installments:
        return result

    result['has_schedule'] = True

    today = timezone.now().date()
    grace_cutoff = today - timedelta(days=5)

    cumulative_paid = Invoice.objects.filter(
        student=student, is_active=True
    ).exclude(status='CANCELLED').aggregate(s=Sum('amount_paid'))['s'] or 0
    result['cumulative_paid'] = cumulative_paid

    running_due = 0
    rows = []
    for inst in installments:
        running_due += inst.amount
        is_overdue = inst.due_date <= grace_cutoff
        if cumulative_paid >= running_due:
            row_status = 'PAYE'
        elif cumulative_paid > running_due - inst.amount:
            row_status = 'EN_RETARD' if is_overdue else 'PARTIEL'
        else:
            row_status = 'EN_RETARD' if is_overdue else 'A_VENIR'
        rows.append({
            'id': str(inst.id),
            'label': inst.label,
            'due_date': inst.due_date,
            'amount': inst.amount,
            'cumulative_due': running_due,
            'status': row_status,
        })

    result['total'] = running_due
    result['installments'] = rows
    return result
