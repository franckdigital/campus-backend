from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import (
    CinetPayConfigViewSet, CinetPayTransactionViewSet,
    CinetPayInitiateView, CinetPayCallbackView, CinetPayStatusView,
    CinetPaySandboxSuccessView, CinetPayDemoPayView,
    ManualMobileMoneySubmitView,
)

router = DefaultRouter()
router.register(r'cinetpay-configs', CinetPayConfigViewSet, basename='cinetpay-config')
router.register(r'cinetpay-transactions', CinetPayTransactionViewSet, basename='cinetpay-transaction')

urlpatterns = [
    path('payments/cinetpay/initiate/', CinetPayInitiateView.as_view(), name='cinetpay-initiate'),
    path('payments/cinetpay/callback/', CinetPayCallbackView.as_view(), name='cinetpay-callback'),
    path('payments/cinetpay/sandbox-success/', CinetPaySandboxSuccessView.as_view(), name='cinetpay-sandbox-success'),
    path('payments/cinetpay/demo-pay/',        CinetPayDemoPayView.as_view(),        name='cinetpay-demo-pay'),
    path('payments/cinetpay/<str:transaction_id>/status/', CinetPayStatusView.as_view(), name='cinetpay-status'),
    path('payments/mobile-money/submit/', ManualMobileMoneySubmitView.as_view(), name='manual-mobile-money-submit'),
    path('', include(router.urls)),
]
