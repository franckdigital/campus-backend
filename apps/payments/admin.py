from django.contrib import admin
from .models import CinetPayConfig, CinetPayTransaction


@admin.register(CinetPayConfig)
class CinetPayConfigAdmin(admin.ModelAdmin):
    list_display = ['site', 'site_id', 'is_sandbox', 'is_active']
    list_filter = ['is_sandbox', 'is_active']
    search_fields = ['site__name']


@admin.register(CinetPayTransaction)
class CinetPayTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'invoice', 'amount', 'currency', 'status', 'initiated_at', 'completed_at']
    list_filter = ['status', 'currency', 'initiated_at']
    search_fields = ['transaction_id', 'invoice__invoice_number', 'cinetpay_transaction_id']
    ordering = ['-initiated_at']
    readonly_fields = ['transaction_id', 'callback_data']
