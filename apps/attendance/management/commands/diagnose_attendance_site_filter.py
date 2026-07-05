"""
Read-only diagnostic: reproduces exactly what the admin "Liste de présence"
site filter does (GET /attendance-records/?site=<uuid>) via the real
AttendanceRecordFilter class, and compares against a direct ORM count per
site, to find out why filtering by site doesn't narrow the results.

Usage:
    python manage.py diagnose_attendance_site_filter
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Diagnose why the attendance list's site filter shows all sites' records."

    def handle(self, *args, **options):
        from apps.core.models import Site
        from apps.attendance.models import AttendanceRecord
        from apps.attendance.filters import AttendanceRecordFilter

        sites = list(Site.objects.filter(is_active=True))
        self.stdout.write(self.style.MIGRATE_HEADING(f'\n=== Sites actifs ({len(sites)}) ===\n'))
        for s in sites:
            self.stdout.write(f'  id={s.id} code={s.code!r} name={s.name!r}')

        total = AttendanceRecord.objects.count()
        self.stdout.write(self.style.MIGRATE_HEADING(f'\n=== Total AttendanceRecord (toutes) = {total} ===\n'))

        for s in sites:
            direct_count = AttendanceRecord.objects.filter(
                attendance_session__session__class_obj__site_id=s.id
            ).count()

            # Replicate exactly what DRF/DjangoFilterBackend does for
            # GET /attendance-records/?site=<uuid>
            qs = AttendanceRecord.objects.all()
            f = AttendanceRecordFilter({'site': str(s.id)}, queryset=qs)
            is_valid = f.is_valid()
            filtered_count = f.qs.count() if is_valid else None

            self.stdout.write(
                f'  site={s.name!r} ({s.id}) | direct ORM count={direct_count} | '
                f'filterset valid={is_valid} | filterset count={filtered_count} | errors={f.errors if not is_valid else None}'
            )

        # Also show a sample of records with their resolved site, to catch
        # cases where class_obj/session/site relations are NULL (would make
        # them invisible to the site filter but still show up unfiltered).
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Échantillon de 10 enregistrements (site résolu) ===\n'))
        sample = AttendanceRecord.objects.select_related(
            'attendance_session__session__class_obj__site'
        ).order_by('-created_at')[:10]
        for r in sample:
            site_obj = None
            try:
                site_obj = r.attendance_session.session.class_obj.site
            except Exception as e:
                site_obj = f'ERREUR: {e}'
            self.stdout.write(f'  record={r.id} student={r.student_id} -> site={site_obj}')
