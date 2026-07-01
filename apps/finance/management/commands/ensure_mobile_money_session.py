"""
Management command: ensure_mobile_money_session

Ensures every active site has:
  - A "Caisse Mobile Money" CashRegister (is_active=True)
  - An open CashSession on that register

Run at server start (e.g. in Procfile / supervisor / systemd ExecStartPost)
or via cron to guarantee the register is always visible in the admin UI.

Usage:
    python manage.py ensure_mobile_money_session
    python manage.py ensure_mobile_money_session --site ITA2   # specific site code
"""

from decimal import Decimal
import logging

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Ensure Mobile Money cash register and open session exist for all sites'

    def add_arguments(self, parser):
        parser.add_argument(
            '--site',
            type=str,
            default=None,
            help='Site code (optional). If omitted, runs for all active sites.',
        )

    def handle(self, *args, **options):
        from apps.finance.models import CashRegister, CashSession
        from apps.sites.models import Site

        User = get_user_model()
        system_user = (
            User.objects.filter(is_superuser=True, is_active=True).first()
            or User.objects.filter(is_staff=True, is_active=True).first()
        )
        if not system_user:
            self.stderr.write('No admin user found — aborting.')
            return

        site_qs = Site.objects.filter(is_active=True)
        if options['site']:
            site_qs = site_qs.filter(code=options['site'])

        for site in site_qs:
            register, created = CashRegister.objects.get_or_create(
                site=site,
                code='MOBILE_MONEY',
                defaults={
                    'name': 'Caisse Mobile Money',
                    'is_active': True,
                    'current_balance': Decimal('0'),
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f'[{site.code}] Created Mobile Money register'
                ))
            else:
                if not register.is_active:
                    register.is_active = True
                    register.save(update_fields=['is_active'])
                    self.stdout.write(self.style.WARNING(
                        f'[{site.code}] Re-activated Mobile Money register'
                    ))

            # Ensure an open session exists
            open_session = CashSession.objects.filter(
                cash_register=register,
                status='OPEN',
                is_active=True,
            ).first()

            if open_session:
                self.stdout.write(
                    f'[{site.code}] Session already open: {open_session.id}'
                )
            else:
                session = CashSession.objects.create(
                    cash_register=register,
                    opened_by=system_user,
                    opening_balance=register.current_balance,
                    notes='Session permanente — Mobile Money',
                )
                register.is_open = True
                register.save(update_fields=['is_open'])
                self.stdout.write(self.style.SUCCESS(
                    f'[{site.code}] Opened new session {session.id} '
                    f'(balance={register.current_balance} FCFA)'
                ))

        self.stdout.write(self.style.SUCCESS('Done.'))
