from rest_framework import serializers
from .models import CinetPayConfig, CinetPayTransaction


class CinetPayConfigSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)

    class Meta:
        model = CinetPayConfig
        fields = [
            'id', 'site', 'site_name', 'account_key', 'account_password',
            'notify_url', 'success_url', 'failed_url', 'is_sandbox',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'account_key': {'write_only': True},
            'account_password': {'write_only': True},
        }


class CinetPayTransactionSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    student_name = serializers.CharField(source='invoice.student.user.full_name', read_only=True)
    initiated_by_name = serializers.CharField(source='initiated_by.full_name', read_only=True)

    class Meta:
        model = CinetPayTransaction
        fields = [
            'id', 'transaction_id', 'invoice', 'invoice_number', 'student_name',
            'payment', 'amount', 'currency', 'cinetpay_transaction_id',
            'payment_url', 'payment_method', 'operator_id', 'status',
            'status_message', 'initiated_at', 'completed_at',
            'initiated_by', 'initiated_by_name', 'is_active'
        ]
        read_only_fields = [
            'id', 'transaction_id', 'cinetpay_transaction_id', 'payment_url',
            'payment_method', 'operator_id', 'status', 'status_message',
            'initiated_at', 'completed_at'
        ]


class CinetPayInitiateSerializer(serializers.Serializer):
    # Either invoice_id (pay down an existing invoice) or student_id (create
    # one on the fly) must be provided — validated in the view, since which
    # one is required depends on the other.
    invoice_id = serializers.UUIDField(required=False)
    student_id = serializers.UUIDField(required=False)
    fee_type_code = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)


