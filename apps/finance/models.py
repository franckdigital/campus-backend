from django.db import models, transaction as db_transaction, IntegrityError
from django.conf import settings
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.core.models import BaseModel, Site, AcademicYear, SystemConfig
from apps.students.models import Student
import uuid


def get_min_enrollment_payment():
    """Admin-configurable minimum cumulative tuition payment (FCFA) required
    for a student to be considered 'inscrit' — stored via the generic
    SystemConfig key/value store (same mechanism as e.g. mobile_money_number)
    rather than a dedicated model field, so it can be edited from Settings
    with no migration. Defaults to 50 000 FCFA when unset."""
    from decimal import Decimal, InvalidOperation
    raw = SystemConfig.get_value('MIN_ENROLLMENT_PAYMENT', default='50000')
    try:
        return Decimal(str(raw))
    except (InvalidOperation, TypeError):
        return Decimal('50000')


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
        self.calculate_totals()
        if self.invoice_number:
            super().save(*args, **kwargs)
            return
        # generate_invoice_number() picks the next free number based on what
        # currently exists — if a concurrent request (or a retry after a
        # deletion changed the count) grabs the same number first, the
        # unique constraint on invoice_number raises IntegrityError. Retry a
        # few times with a freshly recomputed number rather than 500ing.
        from django.db import IntegrityError
        attempts = 0
        while True:
            self.invoice_number = self.generate_invoice_number()
            try:
                super().save(*args, **kwargs)
                return
            except IntegrityError:
                attempts += 1
                if attempts >= 5:
                    raise
                self.invoice_number = ''

    def generate_invoice_number(self):
        year = timezone.now().year
        site_code = self.site.code if self.site else 'XX'
        prefix = f"INV-{site_code}-{year}-"
        # Base the next number on the highest EXISTING suffix, not a row
        # count — count() collides with an already-issued higher number
        # once any invoice in this prefix has been deleted (e.g. via a
        # cleanup script), since the count drops but the gap it left isn't
        # actually free.
        last_number = Invoice.objects.filter(
            invoice_number__startswith=prefix
        ).order_by('-invoice_number').values_list('invoice_number', flat=True).first()
        if last_number:
            try:
                last_seq = int(last_number.rsplit('-', 1)[-1])
            except ValueError:
                last_seq = Invoice.objects.filter(invoice_number__startswith=prefix).count()
        else:
            last_seq = 0
        return f"{prefix}{last_seq + 1:05d}"

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
        
        if self.status == 'CANCELLED':
            return

        # An invoice is saved once before its items exist (see save() below,
        # and ensure_student_invoices()) — at that point total/balance are
        # both 0, which used to read as "nothing owed, fully paid" and get
        # stuck there: none of the branches below ever walked it back down
        # once real items brought the balance back up (amount_paid stays 0,
        # due_date usually isn't in the past yet). Requiring a positive
        # total to call something PAID closes that hole, and the final
        # elif explicitly resets a now-unjustified PAID/OVERDUE instead of
        # leaving it stale.
        if self.total > 0 and self.balance <= 0:
            self.status = 'PAID'
        elif self.amount_paid > 0:
            self.status = 'PARTIAL'
        elif self.due_date and self.due_date < timezone.now().date():
            self.status = 'OVERDUE'
        elif self.status in ('PAID', 'OVERDUE'):
            self.status = 'SENT'

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

    # Manual Mobile Money submission (student/parent self-service, pending
    # admin review) — the operator number the payer sent from, the number
    # that received it, and the date the payer declares the transfer
    # happened (distinct from payment_date, which is when the row was
    # created server-side).
    payer_phone = models.CharField(max_length=30, blank=True, verbose_name='Numéro du payeur')
    recipient_phone = models.CharField(max_length=30, blank=True, verbose_name='Numéro destinataire')
    declared_payment_date = models.DateField(null=True, blank=True, verbose_name='Date de paiement déclarée')
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_payments',
        verbose_name='Soumis par'
    )

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

        if self.payment_number:
            super().save(*args, **kwargs)
            return

        # generate_payment_number() counts existing rows then increments —
        # two near-simultaneous saves (e.g. a payment finalized twice in a
        # race, retried webhook) can read the same count before either
        # commits and collide on the unique constraint. Retry with a fresh
        # number a few times rather than letting the whole request 500.
        last_error = None
        for _ in range(5):
            self.payment_number = self.generate_payment_number()
            try:
                with db_transaction.atomic():
                    super().save(*args, **kwargs)
                return
            except IntegrityError as e:
                last_error = e
                self.payment_number = ''
        raise last_error

    def generate_payment_number(self):
        # Based on the highest existing sequence number, not a row count —
        # a count desyncs from reality the moment any row in the middle of
        # the sequence is deleted (e.g. a test-data cleanup), and then keeps
        # recomputing the same already-taken number forever, no matter how
        # many times save() retries.
        year = timezone.now().year
        prefix = f"PAY-{year}-"
        last_number = Payment.objects.filter(
            payment_number__startswith=prefix
        ).order_by('-payment_number').values_list('payment_number', flat=True).first()
        last_seq = 0
        if last_number:
            try:
                last_seq = int(last_number[len(prefix):])
            except ValueError:
                last_seq = Payment.objects.filter(payment_number__startswith=prefix).count()
        return f"{prefix}{last_seq + 1:06d}"

    def validate(self, user):
        if self.status == 'PENDING':
            self.status = 'SUCCESS'
            self.validated_at = timezone.now()
            self.validated_by = user
            self.save()
            # invoice.amount_paid sync + is_enrolled sync both happen in the
            # on_payment_save signal (apps.finance.signals) — don't duplicate here.
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


# Signal to auto-create enrollment when a student's first tuition invoice is created
@receiver(post_save, sender=Invoice)
def create_enrollment_on_first_tuition_invoice(sender, instance, created, **kwargs):
    """
    Automatically create enrollment when a student's scolarité invoice is
    created, but ONLY by reusing a class the student was already, genuinely
    enrolled in before (e.g. a prior academic year) — never by guessing.

    Frais d'inscription and frais de scolarité used to be two separate
    invoices/fee categories, and this signal used to key off the inscription
    one specifically. They're now merged into a single 'SCOLARITE' fee — this
    fires off that invoice instead. Historical INSCRIPTION-coded invoices
    (pre-merge) are intentionally NOT matched here: they can no longer be
    created going forward (see FeeConfigurationViewSet.perform_create /
    ensure_student_invoices), so keying off them would just silently never
    fire.

    This used to have a second fallback ("any active class at the site") for
    when the student had no prior enrollment at all — an unordered
    Class.objects.filter(...).first() with no relation whatsoever to what
    program/level the admin actually registered the student into. Since
    Class.Meta.ordering is ['level', 'name'] (an arbitrary tie-break, not a
    ranking of relevance), this consistently resolved to whichever class
    happened to sort first — in practice, an early-seeded BTS class — and
    silently created a real, ENROLLED+active Enrollment row for it. Every
    downstream barème/invoice resolution built on "the student's current
    enrollment" (get_for_enrollment, financial_summary, the échéancier) then
    correctly-but-wrongly priced the student off BTS's fees, even though the
    admin had chosen an entirely different programme at registration — a
    brand-new student whose own createEnrollment call happened to fail (or
    hadn't landed yet) got silently, invisibly re-enrolled into an unrelated
    programme the moment their first invoice was saved. Better to create no
    enrollment at all here (leaving the student visibly "N/A"/unenrolled,
    an honest state the admin will notice and fix via Parcours) than to
    invent a wrong one that looks legitimate.
    """
    # Only proceed if invoice has a student
    if not instance.student:
        return

    # Check if invoice contains a scolarité fee item
    has_tuition_fee = instance.items.filter(
        fee_type__code='SCOLARITE'
    ).exists()

    if not has_tuition_fee:
        return

    # Import here to avoid circular imports
    from apps.academic.models import Enrollment

    # Check if student already has an enrollment for this academic year
    existing_enrollment = Enrollment.objects.filter(
        student=instance.student,
        academic_year=instance.academic_year
    ).exists()

    if existing_enrollment:
        return  # Enrollment already exists, don't create duplicate

    # Only reuse a class the student was genuinely enrolled in before (e.g.
    # continuing from a prior academic year) — never guess one from scratch.
    latest_enrollment = instance.student.enrollments.select_related('class_obj').order_by('-created_at').first()
    class_obj = latest_enrollment.class_obj if latest_enrollment else None

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
        print(f"⚠️ No prior enrollment for student {instance.student.matricule} — leaving unenrolled (fix via Parcours) instead of guessing a class.")


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
    # Set instead of level/program when a barème should apply to every
    # filière's students at a given promotion year (e.g. "tous les Licence
    # 3"). Mutually exclusive with level in practice (enforced by the admin
    # form, not the DB) — a level-scoped row always wins over a cycle-scoped
    # one, see get_for_enrollment.
    cycle = models.ForeignKey(
        'academic.Cycle', on_delete=models.SET_NULL, related_name='fee_configurations',
        null=True, blank=True, verbose_name="Cycle"
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
    CATEGORY_CHOICES = [
        ('INSCRIPTION', 'Inscription (historique)'),
        ('SCOLARITE',   'Scolarité'),
    ]
    # Frais d'inscription and frais de scolarité used to be two separate,
    # permanent barème rows sharing the same site/programme/niveau/année/
    # modalité/affectation scope, distinguished by fee_category — inscription
    # was always paid in full, scolarité was payable via échéancier. They've
    # since been merged into a single concept: a barème is always SCOLARITE
    # now (enforced in FeeConfigurationViewSet.perform_create), and a student
    # is "inscrit" once they've paid a configurable minimum (see
    # get_min_enrollment_payment) toward that one scolarité total instead of
    # settling a separate inscription invoice. INSCRIPTION rows only remain
    # as deactivated historical records (see the finance data migration that
    # folded their amount into the matching SCOLARITE row) — kept for FK
    # integrity with old invoice items, never created going forward.
    fee_category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default='SCOLARITE', verbose_name="Catégorie"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Montant")
    label = models.CharField(max_length=200, blank=True, verbose_name="Libellé")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'fee_configurations'
        verbose_name = "Configuration des frais"
        verbose_name_plural = "Configurations des frais"
        ordering = ['site', 'program', 'level', 'fee_category']

    def __str__(self):
        parts = [self.get_fee_category_display(),
                 self.site.name if self.site else 'Tous sites',
                 self.program.name if self.program else 'Toutes filières',
                 self.level.name if self.level else (self.cycle.name if self.cycle else 'Tous niveaux'),
                 self.get_modality_display() if self.modality else 'Toutes modalités',
                 self.get_affectation_status_display() if self.affectation_status else 'Toutes affectations']
        return ' / '.join(parts)

    @classmethod
    def get_for_enrollment(cls, site, level, fee_category, academic_year=None, modality=None, affectation_status=None):
        """Return the best-matching fee config for a given site + level +
        modality + affectation status + fee_category (INSCRIPTION/SCOLARITE
        — always required, since the two are now separate barème rows).

        Level/program is the primary key a school actually thinks in terms
        of ("le barème de Licence 1 Gestion Commerciale") — modality and
        affectation are refinements on top of it, tried in every combination
        (both exact, modality-only relaxed, affectation-only relaxed, both
        relaxed) before level itself is ever given up on (falling back to a
        program-level, level=None row). Returns None — never a different
        program's or a site-wide/global row — once no barème exists at all
        for that level/program: a "site-wide" or "global" (program=None)
        fallback used to exist here, but it meant ANY program with no barème
        of its own silently inherited whatever unrelated program's row
        happened to be the only one with program=None/level=None in the DB
        (in practice, a stray leftover config from initial BTS setup/testing)
        — e.g. a brand-new Licence 1 enrollment with no barème configured yet
        silently priced off BTS's 150 000/500 000 instead of showing
        "Non configuré". Callers already handle a None return safely (falling
        back to the student's own registration_fee/tuition_fee, or 0) — that
        visible gap is the correct signal that this program/level still needs
        its own barème set up, not a wrong number.

        Without every one of the modality/affectation relaxation combinations
        above, a school that only entered ONE barème row per niveau (a single
        modality/affectation combo, since that's usually all they have at
        first) would leave any newly enrolled student whose modality or
        affectation doesn't happen to match that exact combo resolving to NO
        barème at all, even though the level/program clearly has one
        configured — that relaxation is safe because it never leaves the
        student's actual program.
        """
        qs = cls.objects.filter(is_active=True, fee_category=fee_category)

        def _first(**filters):
            # Meta.ordering (site/program/level/fee_category) never actually
            # disambiguates here — every one of those fields is already held
            # constant by the **filters for a given tier, so two rows tied on
            # all of them (e.g. a duplicate/leftover barème row for the same
            # site+level+modality+affectation) fall back to MySQL's
            # unspecified tie order. -created_at makes "most recently
            # configured wins" explicit instead of arbitrary.
            return qs.filter(**filters).order_by('-created_at').first()

        # ── Level-scoped tiers — tried with year then without, most exact
        # combo first, relaxing modality and/or affectation one at a time ──
        if level:
            level_filters = [
                dict(modality=modality, affectation_status=affectation_status),  # exact
                dict(affectation_status=affectation_status),                     # any modality
                dict(modality=modality),                                         # any affectation
                dict(),                                                          # any modality, any affectation
            ]
            for extra in level_filters:
                if academic_year:
                    cfg = _first(site=site, level=level, academic_year=academic_year, **extra)
                    if cfg:
                        return cfg
                cfg = _first(site=site, level=level, academic_year=None, **extra)
                if cfg:
                    return cfg

        # ── Program-scoped tiers (level=None rows) — same relaxation order,
        # used when no level-specific barème exists at all ──────────────────
        program_id = level.program_id if level else None
        if program_id:
            program_filters = [
                dict(modality=modality, affectation_status=affectation_status),
                dict(affectation_status=affectation_status),
                dict(modality=modality),
                dict(),
            ]
            for extra in program_filters:
                cfg = _first(site=site, program_id=program_id, level=None, **extra)
                if cfg:
                    return cfg

        # ── Cycle-scoped tiers (program=None, level=None rows) — a school
        # can configure a single "tous les Licence 3" barème instead of one
        # per filière; tried only once neither an exact level nor an exact
        # program barème exists, so a filière-specific override still wins.
        # Still never falls back to a truly unscoped (cycle=None) row — see
        # the "no site-wide/global fallback" rationale above, which applies
        # just as much across cycles as across programs.
        cycle = level.cycle if level and level.cycle else None
        if cycle:
            cycle_filters = [
                dict(modality=modality, affectation_status=affectation_status),
                dict(affectation_status=affectation_status),
                dict(modality=modality),
                dict(),
            ]
            for extra in cycle_filters:
                if academic_year:
                    cfg = _first(site=site, cycle=cycle, program=None, level=None, academic_year=academic_year, **extra)
                    if cfg:
                        return cfg
                cfg = _first(site=site, cycle=cycle, program=None, level=None, academic_year=None, **extra)
                if cfg:
                    return cfg

        # No barème configured for this level/program/cycle at all —
        # deliberately NOT falling back to a site-wide/global (program=None,
        # cycle=None) row here, see the docstring above. Callers treat None
        # as "not configured yet".
        return None


def recalculate_invoices_for_fee_config(fee_config, old_amount):
    """When a barème (FeeConfiguration) is edited, push the new amount onto
    already-issued but unpaid/partially-paid invoices for students matching
    that config's scope (site/modality/level-or-program). Already-PAID and
    CANCELLED invoices are never touched. A line item is only overwritten
    when its current unit_price still equals the OLD barème amount — if a
    staff member manually discounted/scholarshiped a specific student's item
    (via add-item), it no longer matches the old barème value and is left
    alone rather than silently clobbered.

    Only the invoice line items whose fee_type.code matches this config's
    fee_category (SCOLARITE or INSCRIPTION) are touched — inscription and
    scolarité are separate barème rows now, so a single recalculation call
    only ever needs to update one side.

    Returns the number of invoices actually updated.
    """
    from django.db import transaction

    if fee_config.amount == old_amount:
        return 0
    target_code = fee_config.fee_category  # 'SCOLARITE' or 'INSCRIPTION'

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
    elif fee_config.cycle:
        # Cycle-scoped barème (e.g. "tous les Licence 3") — without this
        # branch, editing its amount would fall through to the unscoped
        # site/modality/affectation filter above and silently recalculate
        # OTHER levels' unpaid invoices too (e.g. every student at the site).
        students = students.filter(
            enrollments__status='ENROLLED', enrollments__is_active=True,
            enrollments__class_obj__level__cycle=fee_config.cycle,
        )
    if fee_config.academic_year_id:
        students = students.filter(enrollments__academic_year_id=fee_config.academic_year_id)
    students = students.distinct()

    updated = 0
    # The auto-enrollment signal is a guaranteed no-op during a price
    # recalculation (the enrollment already exists) — disconnect it for the
    # duration to avoid 2 wasted queries per invoice save.
    post_save.disconnect(create_enrollment_on_first_tuition_invoice, sender=Invoice)
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
                    if code == target_code and item.unit_price == old_amount:
                        item.unit_price = fee_config.amount
                        item.save(update_fields=['unit_price', 'total'])
                        changed = True
                if changed:
                    invoice.refresh_from_db()
                    invoice.save()  # recompute totals/balance/status
                    updated += 1
    finally:
        post_save.connect(create_enrollment_on_first_tuition_invoice, sender=Invoice)

    return updated


class FeeInstallment(BaseModel):
    """One dated tranche of a SCOLARITE FeeConfiguration's total, e.g.
    "Octobre" / "Novembre" each with their own due_date and amount. A
    FeeConfiguration with no installments has the échéancier feature simply
    inactive for that site/filière/niveau (fully backward compatible —
    nothing changes for configs that don't opt in).

    Only ever attaches to a fee_category=SCOLARITE barème — inscription is
    always paid in full at inscription, never split into installments (see
    save()/clean() below)."""
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

    def save(self, *args, **kwargs):
        if self.fee_configuration.fee_category != 'SCOLARITE':
            raise ValueError(
                "L'échéancier ne peut être configuré que sur un barème de scolarité, "
                "pas sur un barème d'inscription (payée intégralement à l'inscription)."
            )
        super().save(*args, **kwargs)


def resolve_current_enrollment(student):
    """The single source of truth for "which Enrollment row is this
    student's CURRENT class" — status=ENROLLED, is_active=True, most recent
    by created_at. Returns (class_obj_id, academic_year_id) or None.

    Enrollment has no Meta.ordering and its id is a random uuid4 (not
    time-sortable) — an unordered `.first()` silently resolves to whichever
    row happens to sort lowest by UUID byte value, not the most recent one.
    Nothing in the enrollment flows (re-enrollment into a new
    programme/year, admin "inscrire" forms, invoice auto-creation) closes
    out a student's previous active Enrollment, so a re-enrolled student can
    easily have two ENROLLED+active rows at once (e.g. last year's BTS and
    this year's Licence 1) — resolving the wrong one silently prices their
    invoices off a stale programme's barème. Shared by
    ensure_student_invoices, _resolve_fee_config_for_student and
    financial_summary so they can never disagree with each other again."""
    return student.enrollments.filter(
        status='ENROLLED', is_active=True
    ).order_by('-created_at').values_list('class_obj_id', 'academic_year_id').first()


def _resolve_fee_config_for_student(student, academic_year=None):
    """Shared level-resolution used by both compute_tuition_schedule_status
    and get_student_installment_schedule, so they can never drift apart.

    Always resolves the SCOLARITE barème row — the échéancier de scolarité
    only ever applies to tuition, never to inscription (paid in full at
    inscription, no installment plan)."""
    level = None
    # Only auto-resolve the academic_year from the enrollment when the caller
    # didn't already pass one explicitly. Without this, get_for_enrollment's
    # most-specific tier (site+level+YEAR) is always skipped (academic_year
    # stays None), and its year-agnostic tier only matches barèmes with a
    # blank academic_year — a barème configured for a specific year (the
    # normal case, mirrors financial_summary's own resolution) then never
    # matches at all, silently making has_schedule=False for every student.
    resolved_academic_year = academic_year
    try:
        from apps.academic.models import Class as AcademicClass
        enrollment_row = resolve_current_enrollment(student)
        if enrollment_row:
            class_obj_id, academic_year_id = enrollment_row
            if class_obj_id:
                class_obj = AcademicClass.objects.select_related('level').get(pk=class_obj_id)
                level = class_obj.level
            if not resolved_academic_year and academic_year_id:
                from apps.core.models import AcademicYear
                resolved_academic_year = AcademicYear.objects.filter(pk=academic_year_id).first()
    except Exception:
        pass

    return FeeConfiguration.get_for_enrollment(
        student.site, level, 'SCOLARITE', resolved_academic_year,
        modality=student.modality, affectation_status=student.affectation_status
    )


def _tuition_amount_paid(student):
    """Sum of amount_paid across the student's tuition invoice(s) — SCOLARITE
    plus the now-legacy INSCRIPTION code. Inscription and scolarité used to
    be billed as two separate invoices; they're merged into one "frais de
    scolarité" concept now, and old inscription payments count toward the
    cumulative tuition total (and therefore toward the enrollment threshold
    and the échéancier) rather than being ignored. Only OTHER, unrelated
    invoice types (if any exist) are excluded. Shared by
    compute_tuition_schedule_status, get_student_installment_schedule and
    sync_enrollment_status so they can't drift apart again."""
    from django.db.models import Sum
    return Invoice.objects.filter(
        student=student, is_active=True, items__fee_type__code__in=['SCOLARITE', 'INSCRIPTION'],
    ).exclude(status='CANCELLED').distinct().aggregate(s=Sum('amount_paid'))['s'] or 0


def sync_enrollment_status(student):
    """Recompute and self-heal Student.is_enrolled from real invoice data —
    'inscrit' means having paid at least get_min_enrollment_payment() toward
    the cumulative tuition total, not settling a separate inscription
    invoice in full. Mirrors the self-healing pattern the old
    registration_fee_paid flag used (Payment save, financial_summary, the
    fee-gate permission) so none of those call sites can disagree. Returns
    the up-to-date boolean."""
    paid = _tuition_amount_paid(student)
    is_enrolled = paid >= get_min_enrollment_payment()
    if student.is_enrolled != is_enrolled:
        Student.objects.filter(pk=student.pk).update(is_enrolled=is_enrolled)
        student.is_enrolled = is_enrolled
    return is_enrolled


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

    cumulative_paid = _tuition_amount_paid(student)

    result['cumulative_due'] = cumulative_due
    result['cumulative_paid'] = cumulative_paid
    # The enrollment threshold must be met first — a brand-new student with
    # no installment due yet would otherwise trivially satisfy
    # `cumulative_paid >= cumulative_due` (0 >= 0), showing "à jour" for
    # someone who hasn't paid a single franc and isn't even inscrit.
    # Computed directly from cumulative_paid (not the cached Student.is_enrolled
    # flag) so this can never lag behind a payment that hasn't been synced
    # yet. echeance_override still wins unconditionally — an admin's explicit
    # exemption should never be second-guessed by the threshold check.
    result['is_up_to_date'] = bool(student.echeance_override) or (
        cumulative_paid >= get_min_enrollment_payment() and cumulative_paid >= cumulative_due
    )
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

    cumulative_paid = _tuition_amount_paid(student)
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


def ensure_student_invoices(student, created_by=None):
    """Create the student's scolarité invoice from whatever barème currently
    resolves for their site/enrollment/modality/affectation, if it doesn't
    already exist. Shared by:
      - StudentViewSet.prepare_invoices (explicit "Préparer mon dossier"
        action, student or admin triggered)
      - the post_save signals on Enrollment/Student (apps.finance.signals) —
        so moving a student onto a different barème (new class, or a
        site/modality/affectation change) automatically creates the invoice
        for their new scope, instead of leaving Scolarité blank until
        someone happens to click "Préparer mon dossier".

    Frais d'inscription and frais de scolarité used to be billed as two
    separate invoices here; they're merged into a single scolarité invoice
    now (see get_min_enrollment_payment / sync_enrollment_status for the new
    "inscrit" threshold rule).

    If the student already has an unpaid/unsettled invoice for a fee type,
    its item is re-priced to whatever barème resolves NOW (e.g. moved from
    one class/programme to another) — see _create_or_reprice below. Already
    PAID/CANCELLED invoices are never touched. This is a different trigger
    than recalculate_invoices_for_fee_config (which reconciles everyone under
    an unchanged scope when the barème's own amount is edited) — this one
    fires when the STUDENT's scope changes instead.

    Returns (created_count, invoices_queryset).
    """
    import logging
    from datetime import date, timedelta

    logger = logging.getLogger(__name__)

    current_year = AcademicYear.get_current()
    if not current_year:
        current_year = AcademicYear.objects.filter(is_active=True).order_by('-start_date').first()
    if not current_year:
        current_year = AcademicYear.objects.order_by('-start_date').first()
    if not current_year:
        return 0, Invoice.objects.none()

    site = student.site
    if not site:
        from apps.core.models import Site
        site = Site.objects.filter(is_active=True).first()
    if not site:
        return 0, Invoice.objects.none()

    enrollment_row = resolve_current_enrollment(student)
    level = None
    try:
        if enrollment_row and enrollment_row[0]:
            from apps.academic.models import Class as AcademicClass
            class_obj = AcademicClass.objects.select_related('level').get(pk=enrollment_row[0])
            level = class_obj.level
    except Exception as e:
        logger.warning('ensure_student_invoices: cannot resolve level: %s', e)

    tuition_config = FeeConfiguration.get_for_enrollment(
        site, level, 'SCOLARITE', current_year,
        modality=student.modality, affectation_status=student.affectation_status
    )
    tuition_amount = float(tuition_config.amount if tuition_config else (student.tuition_fee or 0))

    due_date = (current_year.end_date if getattr(current_year, 'end_date', None)
                else date.today() + timedelta(days=90))

    scolarite_ft, _ = FeeType.objects.get_or_create(
        code='SCOLARITE',
        defaults={'name': 'Frais de scolarité', 'is_recurring': True, 'default_amount': tuition_amount}
    )

    created = 0

    def _create_or_reprice(fee_type, amount, description):
        """Create the invoice if the student has none yet for this fee type.
        If one already exists but isn't settled (not PAID/CANCELLED), re-price
        its item to the amount that resolves NOW — otherwise a student moved
        onto a different barème (new class/site/modality/affectation) keeps
        showing the OLD program's invoiced total forever, since an invoice
        once created is never re-evaluated against the student's current
        scope. A PAID/CANCELLED invoice is never touched — already-settled
        money is never retroactively rewritten."""
        nonlocal created
        existing = Invoice.objects.filter(
            student=student, items__fee_type=fee_type, is_active=True
        ).exclude(status__in=['PAID', 'CANCELLED']).prefetch_related('items').first()

        if existing:
            item = existing.items.filter(fee_type=fee_type).first()
            if item and float(item.unit_price) != amount:
                old_price = item.unit_price
                item.unit_price = int(amount)
                item.save(update_fields=['unit_price', 'total'])
                existing.refresh_from_db()
                existing.save()  # recompute totals/balance/status
                logger.info(
                    'ensure_student_invoices: re-priced %s item on invoice %s for %s (%s -> %s FCFA, scope change)',
                    fee_type.code, existing.invoice_number, student.matricule, old_price, amount,
                )
            return

        inv = Invoice(student=student, site=site, academic_year=current_year,
                      due_date=due_date, created_by=created_by)
        inv.save()
        InvoiceItem.objects.create(
            invoice=inv, fee_type=fee_type, description=description,
            quantity=1, unit_price=int(amount)
        )
        inv.save()
        if inv.balance > 0 and inv.status == 'PAID':
            Invoice.objects.filter(pk=inv.pk).update(status='DRAFT')
            inv.status = 'DRAFT'
        created += 1
        logger.info('ensure_student_invoices: created %s invoice %s for %s', fee_type.code, inv.invoice_number, student.matricule)

    if tuition_amount > 0:
        _create_or_reprice(scolarite_ft, tuition_amount, f'Frais de scolarité — {current_year.name}')

    all_invoices = Invoice.objects.filter(
        student=student, is_active=True
    ).prefetch_related('items__fee_type', 'payments')
    return created, all_invoices
