from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.finance'
    verbose_name = 'Finance'
    
    def ready(self):
        import apps.finance.models  # noqa: F401
        import apps.finance.signals  # noqa: F401
