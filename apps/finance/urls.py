from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import (
    FeeTypeViewSet, PaymentMethodViewSet, InvoiceViewSet, PaymentViewSet,
    CashRegisterViewSet, CashSessionViewSet, CashTransactionViewSet,
    CashPaymentView, CashSessionOpenView, CashReportView,
    BankAccountViewSet, ExpenseViewSet, FeeConfigurationViewSet
)

router = DefaultRouter()
router.register(r'fee-types', FeeTypeViewSet, basename='fee-type')
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'cash-registers', CashRegisterViewSet, basename='cash-register')
router.register(r'cash-sessions', CashSessionViewSet, basename='cash-session')
router.register(r'cash-transactions', CashTransactionViewSet, basename='cash-transaction')
router.register(r'bank-accounts', BankAccountViewSet, basename='bank-account')
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'fee-configurations', FeeConfigurationViewSet, basename='fee-configuration')

urlpatterns = [
    path('payments/cash/', CashPaymentView.as_view(), name='cash-payment'),
    path('cash/sessions/open/', CashSessionOpenView.as_view(), name='cash-session-open'),
    path('cash/reports/daily/', CashReportView.as_view(), name='cash-report-daily'),
    path('', include(router.urls)),
]
