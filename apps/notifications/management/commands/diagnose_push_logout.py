"""
Read-only diagnostic: checks whether the DeviceToken.is_logged_in migration
has been applied, lists a user's DeviceToken rows (is_active/is_logged_in),
and does a real push_to_user() call to see exactly what happens — used to
debug "parent doesn't receive the notification at all when logged out".

Usage:
    python manage.py diagnose_push_logout --email adjoua.kouassi@escam-test.ci
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Diagnose why a logged-out user isn't receiving even the generic push notification."

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True, help='Email of the user (parent or student)')

    def handle(self, *args, **options):
        from django.apps import apps
        from django.db import connection

        email = options['email']

        # ── 1. Migration state ──────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[1] État de la migration DeviceToken.is_logged_in\n'))
        DeviceToken = apps.get_model('notifications', 'DeviceToken')
        column_names = [f.name for f in DeviceToken._meta.get_fields()]
        self.stdout.write(f"  Le modèle Django connaît le champ is_logged_in : {'is_logged_in' in column_names}")

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = %s", [DeviceToken._meta.db_table]
            )
            db_columns = [row[0] for row in cursor.fetchall()]
        has_column_in_db = 'is_logged_in' in db_columns
        if has_column_in_db:
            self.stdout.write(self.style.SUCCESS('  -> La colonne is_logged_in EXISTE en base. Migration appliquée.'))
        else:
            self.stdout.write(self.style.ERROR(
                '  -> La colonne is_logged_in N\'EXISTE PAS en base ! '
                'Lancez : python manage.py migrate notifications'
            ))
            self.stdout.write(self.style.WARNING('  (Le reste du diagnostic va probablement planter ci-dessous.)'))

        # ── 2. User + DeviceToken rows ───────────────────────────────────
        from apps.accounts.models import User
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError(f'Aucun utilisateur avec email={email!r}.')

        self.stdout.write(self.style.MIGRATE_HEADING(f'\n[2] DeviceToken pour {user.email} (id={user.id})\n'))
        tokens = DeviceToken.objects.filter(user=user)
        if not tokens.exists():
            self.stdout.write(self.style.ERROR('  Aucun DeviceToken trouvé pour cet utilisateur — jamais enregistré ?'))
        for t in tokens:
            self.stdout.write(
                f"    id={t.id} platform={t.platform} is_active={t.is_active} "
                f"is_logged_in={getattr(t, 'is_logged_in', '<colonne absente>')} "
                f"last_used={t.last_used} token={t.token[:40]}…"
            )

        # ── 3. Real push_to_user call ─────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[3] Appel réel de push_to_user()\n'))
        try:
            from apps.notifications.push import push_to_user, get_user_expo_tokens
            logged_in, logged_out = get_user_expo_tokens(user)
            self.stdout.write(f"  Tokens connectés (contenu complet) : {len(logged_in)}")
            self.stdout.write(f"  Tokens déconnectés (contenu générique) : {len(logged_out)}")

            success, failed = push_to_user(
                user, 'TEST diagnose_push_logout',
                'Ceci est un test de diagnostic — ignorez ce message.',
                data={'category': 'diagnostic_test'},
            )
            self.stdout.write(self.style.SUCCESS(f'  -> {success} envoi(s) réussi(s)') if success
                               else self.style.ERROR('  -> 0 envoi réussi'))
            for f in failed:
                self.stdout.write(self.style.ERROR(f'    Échec Expo: {f}'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'  EXCEPTION pendant push_to_user: {exc!r}'))
            import traceback
            self.stdout.write(traceback.format_exc())
