"""
fix_blank_pdfs.py
──────────────────
Diagnostique et régénère les PDFs vides ou manquants pour :
  - AssignmentSubmission.file (copies étudiantes)
  - AssignmentCorrection.corrected_file (corrections prof)
  - ExamSession.submission_file (copies examen)
  - ExamSession.corrected_file (corrections examen)
  - SecureExam.subject_file (sujets examen)
  - Assignment.attachment (sujets devoir — si généré par seed)

Usage :
    python manage.py fix_blank_pdfs --dry-run   # affiche sans corriger
    python manage.py fix_blank_pdfs             # corrige les PDFs vides
"""

import os
import random
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile

from apps.elearning.management.commands.pdf_canvas_utils import (
    generate_student_submission_pdf as _gen_student,
    generate_correction_pdf as _gen_correction,
    generate_exam_subject_pdf as _gen_subject,
)

# Contenu générique pour régénérer les PDFs manquants
_FALLBACK_SECTIONS = [
    ('Réponse', 'Document régénéré automatiquement suite à un problème de génération PDF.'),
]
_FALLBACK_CORRECTIONS = [
    ('Note', 'Correction régénérée automatiquement.'),
]


def _file_size(field):
    """Retourne la taille du fichier en bytes, ou 0 si manquant/inaccessible."""
    if not field or not field.name:
        return 0
    try:
        return field.size
    except (FileNotFoundError, OSError, ValueError):
        return 0


class Command(BaseCommand):
    help = 'Diagnostique et régénère les PDFs vides/manquants (submissions, corrections, sujets)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Affiche les fichiers problématiques sans corriger')
        parser.add_argument('--min-size', type=int, default=200,
                            help='Taille minimale valide en bytes (défaut: 200)')

    def handle(self, *args, **options):
        dry = options['dry_run']
        min_size = options['min_size']
        mode = 'DIAGNOSTIC SEUL' if dry else 'CORRECTION'

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n=== Fix Blank PDFs — {mode} (taille min: {min_size}B) ===\n'
        ))

        total_bad = 0
        total_fixed = 0

        # ── 1. Copies étudiantes (AssignmentSubmission) ────────────────────────
        from apps.elearning.models import AssignmentSubmission, AssignmentCorrection
        self.stdout.write(self.style.MIGRATE_HEADING('\n— Copies étudiantes (devoirs) —'))

        subs = AssignmentSubmission.objects.select_related('student__user', 'assignment').all()
        for sub in subs:
            sz = _file_size(sub.file)
            if sz >= min_size:
                continue
            total_bad += 1
            self.stdout.write(self.style.WARNING(
                f'  ⚠ {sub.student.matricule} / {sub.assignment.title[:40]} → {sz}B'
            ))
            if dry:
                continue
            try:
                name = sub.student.user.get_full_name() or sub.student.matricule
                pdf = ContentFile(_gen_student(
                    student_name=name,
                    assignment_title=sub.assignment.title,
                    sections=_FALLBACK_SECTIONS,
                ))
                sub.file.save(f'copie_{sub.student.matricule}_{sub.assignment.id}.pdf',
                              pdf, save=True)
                total_fixed += 1
                self.stdout.write(self.style.SUCCESS(
                    f'    ✓ Régénéré ({sub.file.size}B)'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'    ✗ Échec: {e}'))

        # ── 2. Corrections devoirs (AssignmentCorrection) ──────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n— Corrections devoirs —'))
        cors = AssignmentCorrection.objects.select_related(
            'submission__student__user', 'submission__assignment'
        ).all()
        for cor in cors:
            sz = _file_size(cor.corrected_file)
            if sz >= min_size:
                continue
            total_bad += 1
            sub = cor.submission
            self.stdout.write(self.style.WARNING(
                f'  ⚠ Correction {sub.student.matricule} / {sub.assignment.title[:40]} → {sz}B'
            ))
            if dry:
                continue
            try:
                name = sub.student.user.get_full_name() or sub.student.matricule
                max_s = float(sub.assignment.max_score or 20)
                score = float(cor.score or max_s * 0.6)
                pdf = ContentFile(_gen_correction(
                    student_name=name,
                    assignment_title=sub.assignment.title,
                    score=score,
                    max_score=max_s,
                    feedback=cor.feedback or 'Correction régénérée.',
                    corrections=_FALLBACK_CORRECTIONS,
                ))
                cor.corrected_file.save(
                    f'correction_{sub.student.matricule}_{sub.assignment.id}.pdf',
                    pdf, save=True
                )
                total_fixed += 1
                self.stdout.write(self.style.SUCCESS(
                    f'    ✓ Régénéré ({cor.corrected_file.size}B)'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'    ✗ Échec: {e}'))

        # ── 3. Copies examen (ExamSession.submission_file) ─────────────────────
        from apps.elearning.models import ExamSession, SecureExam
        self.stdout.write(self.style.MIGRATE_HEADING('\n— Copies examen (soumission étudiant) —'))

        sessions = ExamSession.objects.select_related('student__user', 'exam').all()
        for ses in sessions:
            sz = _file_size(ses.submission_file)
            if sz >= min_size:
                continue
            total_bad += 1
            self.stdout.write(self.style.WARNING(
                f'  ⚠ {ses.student.matricule} / {ses.exam.title[:40]} → {sz}B'
            ))
            if dry:
                continue
            try:
                name = ses.student.user.get_full_name() or ses.student.matricule
                pdf = ContentFile(_gen_student(
                    student_name=name,
                    assignment_title=ses.exam.title,
                    sections=_FALLBACK_SECTIONS,
                ))
                ses.submission_file.save(
                    f'copie_{ses.student.matricule}_{ses.exam.id}.pdf',
                    pdf, save=True
                )
                total_fixed += 1
                self.stdout.write(self.style.SUCCESS(
                    f'    ✓ Régénéré ({ses.submission_file.size}B)'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'    ✗ Échec: {e}'))

        # ── 4. Corrections examen (ExamSession.corrected_file) ─────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n— Corrections examen —'))
        for ses in ExamSession.objects.select_related('student__user', 'exam').filter(score__isnull=False):
            sz = _file_size(ses.corrected_file)
            if sz >= min_size:
                continue
            total_bad += 1
            self.stdout.write(self.style.WARNING(
                f'  ⚠ Correction examen {ses.student.matricule} / {ses.exam.title[:40]} → {sz}B'
            ))
            if dry:
                continue
            try:
                name = ses.student.user.get_full_name() or ses.student.matricule
                max_s = float(ses.exam.max_score or 20)
                score = float(ses.score or max_s * 0.6)
                pdf = ContentFile(_gen_correction(
                    student_name=name,
                    assignment_title=ses.exam.title,
                    score=score,
                    max_score=max_s,
                    feedback=ses.feedback or 'Correction régénérée.',
                    corrections=_FALLBACK_CORRECTIONS,
                ))
                ses.corrected_file.save(
                    f'exam_correction_{ses.student.matricule}_{ses.exam.id}.pdf',
                    pdf, save=True
                )
                total_fixed += 1
                self.stdout.write(self.style.SUCCESS(
                    f'    ✓ Régénéré ({ses.corrected_file.size}B)'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'    ✗ Échec: {e}'))

        # ── 5. Sujets examen (SecureExam.subject_file) ─────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n— Sujets examen —'))
        for exam in SecureExam.objects.all():
            sz = _file_size(exam.subject_file)
            if sz >= min_size:
                continue
            total_bad += 1
            self.stdout.write(self.style.WARNING(
                f'  ⚠ Sujet {exam.title[:50]} → {sz}B'
            ))
            if dry:
                continue
            try:
                meta = {
                    'Matière': getattr(exam.subject, 'name', ''),
                    'Durée': f'{exam.duration_minutes} min',
                    'Barème': f'{exam.max_score or 20} pts',
                }
                pdf = ContentFile(_gen_subject(
                    title=exam.title,
                    questions_list=[('Instructions', 'Voir le sujet distribué en salle.')],
                    meta_info=meta,
                    intro='Sujet régénéré automatiquement.',
                ))
                exam.subject_file.save(f'sujet_{exam.id}.pdf', pdf, save=True)
                total_fixed += 1
                self.stdout.write(self.style.SUCCESS(
                    f'    ✓ Régénéré ({exam.subject_file.size}B)'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'    ✗ Échec: {e}'))

        # ── Résumé ────────────────────────────────────────────────────────────
        self.stdout.write('')
        if dry:
            self.stdout.write(self.style.WARNING(
                f'📋 {total_bad} fichier(s) vide(s)/manquant(s) détecté(s). '
                f'Relancez sans --dry-run pour corriger.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'✅ {total_fixed}/{total_bad} PDFs régénérés avec succès.'
            ))
