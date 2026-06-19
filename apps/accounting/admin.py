from django.contrib import admin
from .models import AccountingAccount, JournalEntry, JournalLine


@admin.register(AccountingAccount)
class AccountingAccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'account_type', 'site', 'parent', 'is_system', 'is_active']
    list_filter = ['account_type', 'site', 'is_system', 'is_active']
    search_fields = ['code', 'name']
    ordering = ['code']


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 1


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['entry_number', 'site', 'entry_date', 'description', 'status', 'is_balanced']
    list_filter = ['status', 'site', 'entry_date']
    search_fields = ['entry_number', 'description', 'reference']
    ordering = ['-entry_date', '-entry_number']
    inlines = [JournalLineInline]


@admin.register(JournalLine)
class JournalLineAdmin(admin.ModelAdmin):
    list_display = ['journal_entry', 'account', 'debit_amount', 'credit_amount']
    list_filter = ['account__account_type']
    search_fields = ['journal_entry__entry_number', 'account__code', 'description']
