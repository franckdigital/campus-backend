from rest_framework import serializers
from .models import (
    FeeType, Invoice, InvoiceItem, PaymentMethod, Payment,
    CashRegister, CashSession, CashTransaction, BankAccount, Expense,
    FeeConfiguration, FeeInstallment
)


class FeeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeType
        fields = [
            'id', 'name', 'code', 'description', 'default_amount',
            'is_recurring', 'accounting_code', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class InvoiceItemSerializer(serializers.ModelSerializer):
    fee_type_name = serializers.CharField(source='fee_type.name', read_only=True)
    invoice = serializers.PrimaryKeyRelatedField(read_only=False, required=False, queryset=Invoice.objects.all())

    class Meta:
        model = InvoiceItem
        fields = [
            'id', 'invoice', 'fee_type', 'fee_type_name', 'description',
            'quantity', 'unit_price', 'total', 'is_active'
        ]
        read_only_fields = ['id', 'total']


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'name', 'code', 'description', 'is_online',
            'requires_verification', 'accounting_code', 'is_active'
        ]
        read_only_fields = ['id']


class PaymentSerializer(serializers.ModelSerializer):
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    student_name = serializers.CharField(source='invoice.student.user.full_name', read_only=True)
    received_by_name = serializers.CharField(source='received_by.full_name', read_only=True)
    proof_url = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id', 'payment_number', 'invoice', 'invoice_number', 'student_name',
            'payment_method', 'payment_method_name', 'amount', 'status',
            'payment_date', 'validated_at', 'reference', 'notes', 'proof', 'proof_url',
            'received_by', 'received_by_name', 'validated_by', 'is_active'
        ]
        read_only_fields = ['id', 'payment_number', 'payment_date', 'validated_at', 'proof_url']

    def get_proof_url(self, obj):
        if obj.proof:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.proof.url)
            return obj.proof.url
        return None


class InvoiceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    student_matricule = serializers.CharField(source='student.matricule', read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True)
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    items = InvoiceItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'student', 'student_name', 'student_matricule',
            'site', 'site_name', 'academic_year', 'academic_year_name',
            'issue_date', 'due_date', 'subtotal', 'discount', 'tax', 'total',
            'amount_paid', 'balance', 'status', 'notes', 'items', 'payments',
            'created_by', 'is_active', 'created_at'
        ]
        read_only_fields = [
            'id', 'invoice_number', 'subtotal', 'total', 'amount_paid',
            'balance', 'issue_date', 'created_at'
        ]


class InvoiceListSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    student_matricule = serializers.CharField(source='student.matricule', read_only=True)
    has_payment_proof = serializers.SerializerMethodField()
    last_payment_method = serializers.SerializerMethodField()
    fee_type_codes = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'student', 'student_name', 'student_matricule',
            'issue_date', 'due_date', 'total', 'amount_paid', 'balance', 'status',
            'has_payment_proof', 'last_payment_method', 'fee_type_codes'
        ]

    def get_has_payment_proof(self, obj):
        # Iterate the prefetched cache (obj.payments.all()) instead of .filter(),
        # which would issue a fresh query per invoice and defeat the ViewSet's
        # prefetch_related('payments').
        return any(p.proof for p in obj.payments.all())

    def get_last_payment_method(self, obj):
        success_payments = [p for p in obj.payments.all() if p.status == 'SUCCESS']
        if not success_payments:
            return None
        last_payment = max(success_payments, key=lambda p: p.payment_date)
        return last_payment.payment_method.name if last_payment.payment_method_id else None

    def get_fee_type_codes(self, obj):
        # Iterate the prefetched cache (obj.items.all()) instead of chaining
        # select_related/values_list, which would issue a fresh query per
        # invoice and defeat the ViewSet's prefetch_related('items').
        return [item.fee_type.code for item in obj.items.all()]


class InvoiceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'student', 'site', 'academic_year', 'due_date', 'discount', 'tax', 'notes']
        read_only_fields = ['id', 'invoice_number']


class CashRegisterSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)

    class Meta:
        model = CashRegister
        fields = [
            'id', 'name', 'code', 'site', 'site_name',
            'current_balance', 'is_open', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'current_balance', 'is_open', 'created_at']


class CashTransactionSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(source='recorded_by.full_name', read_only=True)

    class Meta:
        model = CashTransaction
        fields = [
            'id', 'session', 'payment', 'transaction_type', 'amount',
            'description', 'reference', 'recorded_by', 'recorded_by_name',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CashSessionSerializer(serializers.ModelSerializer):
    cash_register_name = serializers.CharField(source='cash_register.name', read_only=True)
    opened_by_name = serializers.CharField(source='opened_by.full_name', read_only=True)
    closed_by_name = serializers.CharField(source='closed_by.full_name', read_only=True)
    transactions = CashTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = CashSession
        fields = [
            'id', 'cash_register', 'cash_register_name',
            'opened_by', 'opened_by_name', 'closed_by', 'closed_by_name',
            'opening_balance', 'closing_balance', 'expected_balance', 'difference',
            'opened_at', 'closed_at', 'status', 'notes', 'transactions',
            'is_active', 'created_at'
        ]
        read_only_fields = [
            'id', 'opened_at', 'closed_at', 'closing_balance',
            'expected_balance', 'difference', 'created_at'
        ]


class CashSessionListSerializer(serializers.ModelSerializer):
    cash_register_name = serializers.CharField(source='cash_register.name', read_only=True)
    opened_by_name = serializers.CharField(source='opened_by.full_name', read_only=True)

    class Meta:
        model = CashSession
        fields = [
            'id', 'cash_register', 'cash_register_name',
            'opened_by_name', 'opening_balance', 'closing_balance',
            'opened_at', 'closed_at', 'status'
        ]


class BankAccountSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)

    class Meta:
        model = BankAccount
        fields = '__all__'
        read_only_fields = ['created_at']


class ExpenseSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    bank_account_name = serializers.CharField(source='bank_account.name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True)

    class Meta:
        model = Expense
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class CashPaymentSerializer(serializers.Serializer):
    invoice_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    cash_session_id = serializers.UUIDField()
    reference = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class FeeInstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeInstallment
        fields = [
            'id', 'fee_configuration', 'label', 'due_date', 'amount',
            'order', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_fee_configuration(self, value):
        if value.fee_category != 'SCOLARITE':
            raise serializers.ValidationError(
                "L'échéancier ne peut être configuré que sur un barème de scolarité, "
                "pas sur un barème d'inscription (payée intégralement à l'inscription)."
            )
        return value


class FeeConfigurationSerializer(serializers.ModelSerializer):
    # Model has a default (SCOLARITE) so a bare Django save() never fails
    # accidentally — but through the API this must always be an explicit
    # choice, never silently defaulted, since the two categories behave very
    # differently (échéancier eligibility, "paid in full" business rule).
    fee_category = serializers.ChoiceField(choices=FeeConfiguration.CATEGORY_CHOICES, required=True)
    site_name = serializers.SerializerMethodField()
    program_name = serializers.SerializerMethodField()
    level_name = serializers.SerializerMethodField()
    academic_year_name = serializers.SerializerMethodField()
    modality_name = serializers.SerializerMethodField()
    affectation_status_name = serializers.SerializerMethodField()
    fee_category_name = serializers.SerializerMethodField()
    installments = FeeInstallmentSerializer(many=True, read_only=True)

    def get_site_name(self, obj):
        return obj.site.name if obj.site_id and obj.site else None

    def get_program_name(self, obj):
        return obj.program.name if obj.program_id and obj.program else None

    def get_level_name(self, obj):
        return obj.level.name if obj.level_id and obj.level else None

    def get_academic_year_name(self, obj):
        return obj.academic_year.name if obj.academic_year_id and obj.academic_year else None

    def get_modality_name(self, obj):
        return obj.get_modality_display() if obj.modality else None

    def get_affectation_status_name(self, obj):
        return obj.get_affectation_status_display() if obj.affectation_status else None

    def get_fee_category_name(self, obj):
        return obj.get_fee_category_display()

    class Meta:
        model = FeeConfiguration
        fields = [
            'id', 'site', 'site_name', 'program', 'program_name',
            'level', 'level_name', 'academic_year', 'academic_year_name',
            'modality', 'modality_name', 'affectation_status', 'affectation_status_name',
            'fee_category', 'fee_category_name', 'amount', 'label', 'is_active',
            'installments',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
