"""
Management command to seed demo notifications for test users.
Usage:
    python manage.py seed_demo_notifications
"""
import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


DEMO_NOTIFICATIONS = [
    # For angealain@gmail.com (student/parent demo)
    {
        'email': 'angealain@gmail.com',
        'items': [
            {
                'notification_type': 'PAYMENT',
                'priority': 'HIGH',
                'title': 'Paiement recu',
                'message': 'Votre paiement de 600 000 F CFA a ete enregistre avec succes.',
                'is_read': False,
                'days_ago': 0,
            },
            {
                'notification_type': 'GRADE',
                'priority': 'NORMAL',
                'title': 'Nouvelles notes disponibles',
                'message': 'Vos notes du semestre 1 sont disponibles. Moyenne: 14.42/20.',
                'is_read': False,
                'days_ago': 1,
            },
            {
                'notification_type': 'ABSENCE',
                'priority': 'NORMAL',
                'title': 'Absence enregistree',
                'message': 'Une absence a ete enregistree en Mathematiques le cours du lundi.',
                'is_read': False,
                'days_ago': 2,
            },
            {
                'notification_type': 'SYSTEM',
                'priority': 'LOW',
                'title': 'Bienvenue sur la plateforme',
                'message': 'Votre espace etudiant est pret. Consultez vos cours, notes et finances.',
                'is_read': True,
                'days_ago': 10,
            },
            {
                'notification_type': 'REMINDER',
                'priority': 'NORMAL',
                'title': 'Rappel: Solde de scolarite',
                'message': 'Il vous reste 450 000 F CFA a regler avant la fin du mois.',
                'is_read': False,
                'days_ago': 3,
            },
        ]
    },
    # For jeandupont@campus.com (admin demo)
    {
        'email': 'jeandupont@campus.com',
        'items': [
            {
                'notification_type': 'PAYMENT',
                'priority': 'NORMAL',
                'title': 'Nouveau paiement recu',
                'message': 'Angeline Alain a effectue un paiement de 600 000 F CFA.',
                'is_read': False,
                'days_ago': 0,
            },
            {
                'notification_type': 'ALERT',
                'priority': 'HIGH',
                'title': '3 etudiants en retard de paiement',
                'message': 'Des relances automatiques ont ete envoyees. Verifiez le tableau de bord.',
                'is_read': False,
                'days_ago': 1,
            },
            {
                'notification_type': 'SYSTEM',
                'priority': 'LOW',
                'title': 'Rapport mensuel disponible',
                'message': 'Le rapport financier de mai 2026 est pret a etre consulte.',
                'is_read': True,
                'days_ago': 2,
            },
            {
                'notification_type': 'ATTENDANCE',
                'priority': 'NORMAL',
                'title': 'Recap absences du jour',
                'message': '5 etudiants absents enregistres aujourd\'hui toutes classes confondues.',
                'is_read': False,
                'days_ago': 0,
            },
        ]
    },
]


class Command(BaseCommand):
    help = 'Seed demo notifications for test users'

    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.notifications.models import Notification, NotificationLog

        with transaction.atomic():
            created_total = 0

            for entry in DEMO_NOTIFICATIONS:
                try:
                    user = User.objects.get(email=entry['email'])
                except User.DoesNotExist:
                    self.stdout.write(f"  User not found: {entry['email']}, skipping")
                    continue

                # Clear old demo notifications to avoid duplicates on re-run
                Notification.objects.filter(recipient=user).delete()
                self.stdout.write(f"  Cleared existing notifications for {entry['email']}")

                for item in entry['items']:
                    created_at = timezone.now() - datetime.timedelta(days=item['days_ago'], hours=2)
                    n = Notification.objects.create(
                        recipient=user,
                        notification_type=item['notification_type'],
                        priority=item['priority'],
                        title=item['title'],
                        message=item['message'],
                        is_read=item['is_read'],
                        read_at=created_at if item['is_read'] else None,
                        created_at=created_at,
                    )
                    NotificationLog.objects.create(
                        notification=n,
                        channel='IN_APP',
                        status='DELIVERED',
                    )
                    created_total += 1

                self.stdout.write(f"  Created {len(entry['items'])} notifications for {entry['email']}")

            self.stdout.write(f"Done: {created_total} notifications seeded.")
