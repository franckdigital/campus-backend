from rest_framework import serializers
from .models import AccountingAccount, JournalEntry, JournalLine


class AccountingAccountSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = AccountingAccount
        fields = [
            'id', 'code', 'name', 'account_type', 'parent', 'parent_name',
            'site', 'site_name', 'description', 'is_system', 'balance',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class JournalLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source='account.code', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)

    class Meta:
        model = JournalLine
        fields = [
            'id', 'journal_entry', 'account', 'account_code', 'account_name',
            'description', 'debit_amount', 'credit_amount', 'is_active'
        ]
        read_only_fields = ['id']


class JournalEntrySerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    posted_by_name = serializers.CharField(source='posted_by.full_name', read_only=True)
    lines = JournalLineSerializer(many=True, read_only=True)
    total_debit = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_credit = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_balanced = serializers.BooleanField(read_only=True)

    class Meta:
        model = JournalEntry
        fields = [
            'id', 'entry_number', 'site', 'site_name', 'entry_date',
            'description', 'reference', 'status', 'payment',
            'created_by', 'created_by_name', 'posted_by', 'posted_by_name',
            'posted_at', 'lines', 'total_debit', 'total_credit', 'is_balanced',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'entry_number', 'posted_by', 'posted_at',
            'created_at', 'updated_at'
        ]


class JournalEntryListSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)
    total_debit = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = JournalEntry
        fields = [
            'id', 'entry_number', 'site', 'site_name', 'entry_date',
            'description', 'status', 'total_debit'
        ]


class JournalEntryCreateSerializer(serializers.ModelSerializer):
    lines = JournalLineSerializer(many=True)

    class Meta:
        model = JournalEntry
        fields = ['site', 'entry_date', 'description', 'reference', 'lines']

    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        journal_entry = JournalEntry.objects.create(**validated_data)
        
        for line_data in lines_data:
            line_data.pop('journal_entry', None)
            JournalLine.objects.create(journal_entry=journal_entry, **line_data)
        
        return journal_entry

    def validate_lines(self, lines):
        if not lines:
            raise serializers.ValidationError('Au moins une ligne est requise')
        
        total_debit = sum(line.get('debit_amount', 0) for line in lines)
        total_credit = sum(line.get('credit_amount', 0) for line in lines)
        
        if total_debit != total_credit:
            raise serializers.ValidationError(
                f'L\'écriture n\'est pas équilibrée (Débit: {total_debit}, Crédit: {total_credit})'
            )
        
        return lines
