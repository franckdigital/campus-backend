from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import (
    AccountingAccountViewSet, JournalEntryViewSet, JournalLineViewSet,
    AccountingExportView, TrialBalanceView,
    RevenueReportView, UnpaidReportView, InitOHADAView,
)

router = DefaultRouter()
router.register(r'accounting/accounts', AccountingAccountViewSet, basename='accounting-account')
router.register(r'accounting/journal-entries', JournalEntryViewSet, basename='journal-entry')
router.register(r'accounting/journal-lines', JournalLineViewSet, basename='journal-line')

urlpatterns = [
    path('accounting/exports/excel/', AccountingExportView.as_view(), name='accounting-export'),
    path('accounting/trial-balance/', TrialBalanceView.as_view(), name='trial-balance'),
    path('accounting/reports/revenue/', RevenueReportView.as_view(), name='accounting-revenue-report'),
    path('accounting/reports/unpaid/', UnpaidReportView.as_view(), name='accounting-unpaid-report'),
    path('accounting/init-ohada/', InitOHADAView.as_view(), name='init-ohada'),
    path('', include(router.urls)),
]
