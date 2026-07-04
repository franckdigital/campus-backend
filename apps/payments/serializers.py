from rest_framework import serializers
from .models import CinetPayConfig, CinetPayTransaction


class CinetPayConfigSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)

    class Meta:
        model = CinetPayConfig
        fields = [
            'id', 'site', 'site_name', 'api_key', 'site_id', 'secret_key',
            'notify_url', 'return_url', 'cancel_url', 'is_sandbox',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'api_key': {'write_only': True},
            'secret_key': {'write_only': True},
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


class CinetPayCallbackSerializer(serializers.Serializer):
    cpm_trans_id = serializers.CharField()
    cpm_site_id = serializers.CharField()
    cpm_trans_date = serializers.CharField()
    cpm_amount = serializers.CharField()
    cpm_currency = serializers.CharField()
    cpm_result = serializers.CharField()
    cpm_error_message = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.CharField(required=False, allow_blank=True)
    operator_id = serializers.CharField(required=False, allow_blank=True)
    signature = serializers.CharField(required=False, allow_blank=True)
