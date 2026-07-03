"""
seed_classrooms_july3.py — Classes virtuelles du 3 juillet 2026 de 00h00 à 18h00.

Usage: python manage.py seed_classrooms_july3

Génère des créneaux à intervalles variables :
  - Tranche 00h–06h : intervalle 15 min (24 sessions)
  - Tranche 06h–12h : intervalle 10 min (36 sessions)
  - Tranche 12h–18h : intervalle  5 min (72 sessions)

Chaque classe virtuelle génère automatiquement ses segments de réunion (max 55 min).
"""
import uuid
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

SUBJECTS_TITLES = [
    'Introduction à Python', 'Algorithmique avancée', 'Base de données SQL',
    'Réseaux informatiques', 'Intelligence Artificielle', 'Développement Web',
    'Sécurité informatique', 'Systèmes d\'exploitation', 'Génie logiciel',
    'Mathématiques discrètes', 'Architecture des ordinateurs', 'Programmation orientée objet',
]

PROVIDERS = ['JITSI', 'MEET', 'JITSI', 'JITSI', 'MEET']  # Jitsi majoritaire


class Command(BaseCommand):
    help = 'Génère les classes virtuelles du 3 juillet 2026 (00h–18h) à intervalles variables'

    def handle(self, *args, **options):
        from apps.elearning.models import VirtualClassroom, MeetingSegment
        from apps.academic.models import Class as ClassModel
        from django.contrib.auth import get_user_model
        User = get_user_model()

        self.stdout.write(self.style.MIGRATE_HEADING('=== Seed Classes Virtuelles — 3 juillet 2026 ==='))

        from apps.academic.models import Subject
        classes = list(ClassModel.objects.filter(is_active=True)[:5])
        if not classes:
            self.stdout.write(self.style.ERROR('Aucune classe trouvée. Exécutez seed_full d\'abord.'))
            return

        all_subjects = list(Subject.objects.filter(is_active=True)[:12])
        admin_user = User.objects.filter(is_staff=True).first()
        if not admin_user:
            self.stdout.write(self.style.ERROR('Aucun admin trouvé.'))
            return

        # Référence : 3 juillet 2026 00h00 UTC
        base_date = datetime(2026, 7, 3, 0, 0, 0)
        if timezone.is_aware(timezone.now()):
            import pytz
            base_date = timezone.make_aware(base_date, pytz.UTC)

        # Définir les tranches horaires
        tranches = [
            # (heure_debut, heure_fin, intervalle_minutes, duree_minutes)
            (0,   6,  15, 60),    # 00h–06h : 1 session/15 min, durée 60 min
            (6,  12,  10, 45),    # 06h–12h : 1 session/10 min, durée 45 min
            (12, 18,   5, 30),    # 12h–18h : 1 session/ 5 min, durée 30 min
        ]

        total_created = 0
        total_segments = 0
        subject_idx = 0

        for (h_start, h_end, interval, duration) in tranches:
            t = base_date + timedelta(hours=h_start)
            end_limit = base_date + timedelta(hours=h_end)
            self.stdout.write(f'\n  Tranche {h_start:02d}h–{h_end:02d}h (intervalle {interval} min, durée {duration} min) :')

            while t < end_limit:
                cls = classes[total_created % len(classes)]
                subjects = [cst.subject for cst in cls.subject_teachers.select_related('subject').all()] or all_subjects
                subject = subjects[total_created % len(subjects)] if subjects else None
                provider = PROVIDERS[total_created % len(PROVIDERS)]
                title_subj = SUBJECTS_TITLES[subject_idx % len(SUBJECTS_TITLES)]
                subject_idx += 1

                room_name = f"campus-{uuid.uuid4().hex[:8]}"
                join_url = f"https://meet.jit.si/{room_name}" if provider == 'JITSI' else ''

                classroom = VirtualClassroom.objects.create(
                    title=f"Cours {title_subj} — {t.strftime('%Hh%M')}",
                    provider=provider,
                    class_obj=cls,
                    subject=subject,
                    start_time=t,
                    duration_minutes=duration,
                    jitsi_room_name=room_name if provider == 'JITSI' else '',
                    join_url=join_url,
                    enable_recording=True,
                    enable_chat=True,
                    enable_whiteboard=True,
                    enable_polls=True,
                    enable_hand_raise=True,
                    created_by=admin_user,
                    is_active=True,
                )

                # Générer les segments automatiquement (max 55 min par segment)
                seg_max = 55
                import math
                n_segs = math.ceil(duration / seg_max)
                for seq in range(1, n_segs + 1):
                    seg_start = t + timedelta(minutes=(seq - 1) * seg_max)
                    seg_dur = min(seg_max, duration - (seq - 1) * seg_max)
                    seg_end = seg_start + timedelta(minutes=seg_dur)

                    seg_url = f"https://meet.jit.si/{room_name}-seg{seq}" if provider == 'JITSI' else join_url

                    # Déterminer le statut selon l'heure actuelle
                    now = timezone.now()
                    if seg_end < now:
                        seg_status = 'TERMINEE'
                    elif seg_start <= now <= seg_end:
                        seg_status = 'EN_COURS'
                    elif seq > 1 and seg_start > now:
                        seg_status = 'PLANIFIEE'
                    else:
                        seg_status = 'PLANIFIEE'

                    MeetingSegment.objects.create(
                        virtual_class=classroom,
                        sequence=seq,
                        meeting_url=seg_url,
                        start_time=seg_start,
                        end_time=seg_end,
                        status=seg_status,
                        is_active=True,
                    )
                    total_segments += 1

                total_created += 1
                t += timedelta(minutes=interval)

            self.stdout.write(f'    → {(h_end - h_start) * 60 // interval} classes créées')

        # Résumé par tranche
        live_count = VirtualClassroom.objects.filter(
            start_time__date=base_date.date(),
            is_active=True,
        ).count()

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ {total_created} classes virtuelles créées pour le 3 juillet 2026'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'   {total_segments} segments de réunion générés'
        ))
        self.stdout.write(f'\n   Répartition :')
        self.stdout.write(f'   - 00h–06h : {6*60//15} classes (15 min)')
        self.stdout.write(f'   - 06h–12h : {6*60//10} classes (10 min)')
        self.stdout.write(f'   - 12h–18h : {6*60//5} classes ( 5 min)')
        self.stdout.write(f'   Total     : {6*60//15 + 6*60//10 + 6*60//5} classes')
