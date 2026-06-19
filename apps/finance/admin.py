from django.contrib import admin
from .models import (
    FeeType, Invoice, InvoiceItem, PaymentMethod, Payment,
    CashRegister, CashSession, CashTransaction
)


@admin.register(FeeType)
class FeeTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'default_amount', 'is_recurring', 'is_active']
    list_filter = ['is_recurring', 'is_active']
    search_fields = ['name', 'code']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'student', 'site', 'total', 'amount_paid', 'balance', 'status', 'due_date']
    list_filter = ['status', 'site', 'academic_year']
    search_fields = ['invoice_number', 'student__matricule', 'student__user__first_name']
    ordering = ['-issue_date']


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'fee_type', 'description', 'quantity', 'unit_price', 'total']
    list_filter = ['fee_type']
    search_fields = ['invoice__invoice_number', 'description']


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_online', 'requires_verification', 'is_active']
    list_filter = ['is_online', 'is_active']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_number', 'invoice', 'payment_method', 'amount', 'status', 'payment_date']
    list_filter = ['status', 'payment_method', 'payment_date']
    search_fields = ['payment_number', 'invoice__invoice_number', 'reference']
    ordering = ['-payment_date']


@admin.register(CashRegister)
class CashRegisterAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'site', 'current_balance', 'is_open', 'is_active']
    list_filter = ['site', 'is_open', 'is_active']


@admin.register(CashSession)
class CashSessionAdmin(admin.ModelAdmin):
    list_display = ['cash_register', 'opened_by', 'opening_balance', 'closing_balance', 'status', 'opened_at']
    list_filter = ['status', 'cash_register', 'opened_at']
    ordering = ['-opened_at']


@admin.register(CashTransaction)
class CashTransactionAdmin(admin.ModelAdmin):
    list_display = ['session', 'transaction_type', 'amount', 'description', 'recorded_by', 'created_at']
    list_filter = ['transaction_type', 'session']
    search_fields = ['description', 'reference']
    ordering = ['-created_at']
