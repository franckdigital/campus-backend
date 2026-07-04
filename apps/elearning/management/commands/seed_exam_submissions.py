"""
seed_exam_submissions.py
─────────────────────────
1. Upload des sujets PDF pour chaque examen sécurisé (côté prof/admin).
2. Création de sessions d'examen soumises par les étudiants avec upload
   de leur copie PDF.
PDF générés via pdf_canvas_utils (canvas.Canvas — fiable sur tout serveur).
"""

import random
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils import timezone
from datetime import timedelta

from apps.elearning.management.commands.pdf_canvas_utils import (
    generate_exam_subject_pdf as _gen_subject,
    generate_student_submission_pdf as _gen_student,
    generate_correction_pdf as _gen_correction,
)


# ─── Sujets d'examen ─────────────────────────────────────────────────────────

EXAM_SUBJECTS = [
    {
        'title': 'Examen Final — Gestion Commerciale & Stratégie',
        'questions': [
            ('Q1 (4 pts)', 'Définissez la segmentation de marché et présentez ses 4 critères principaux.'),
            ('Q2 (6 pts)', 'Analysez la matrice SWOT d\'une PME agroalimentaire de votre choix.'),
            ('Q3 (5 pts)', 'Expliquez le modèle des 5 forces de Porter et son utilité stratégique.'),
            ('Q4 (3 pts)', 'Calculez le taux de marge brute sachant : CA = 500 000 € · Achats = 280 000 €.'),
            ('Q5 (2 pts)', 'Quels KPI utiliseriez-vous pour piloter une force de vente de 12 commerciaux ?'),
        ],
    },
    {
        'title': 'Examen — Gestion des Ressources Humaines',
        'questions': [
            ('Q1 (6 pts)', 'Décrivez le processus de recrutement en 6 étapes depuis la définition du besoin.'),
            ('Q2 (6 pts)', 'Qu\'est-ce que la GPEC ? Comment la mettre en place dans une entreprise de 200 salariés ?'),
            ('Q3 (3 pts)', 'Calculez le coût de recrutement d\'un cadre (annonce 1 200 €, cabinet 15% de 45 000 €, formation 800 €).'),
            ('Q4 (5 pts)', 'Distinguez contrat CDI et CDD : conditions, durée, renouvellement, rupture.'),
        ],
    },
    {
        'title': 'Partiel — Théories et Pratiques du Management',
        'questions': [
            ('Q1 (6 pts)', 'Comparez les styles de management de McGregor (Théorie X vs Y) et leurs implications pratiques.'),
            ('Q2 (6 pts)', 'Présentez le modèle de leadership situationnel de Hersey & Blanchard avec un exemple concret.'),
            ('Q3 (4 pts)', 'Qu\'est-ce que le management par objectifs (MBO) de Drucker ? Avantages et limites.'),
            ('Q4 (4 pts)', 'Décrivez le modèle de conduite du changement de Kotter en 8 étapes.'),
        ],
    },
]

# ─── Copies étudiantes ────────────────────────────────────────────────────────

STUDENT_COPIES = [
    {
        'score_pct': 0.82,
        'sections': [
            ('Réponse Q1', 'La segmentation de marché consiste à diviser un marché en groupes homogènes. Les 4 critères : géographique (pays, région), démographique (âge, sexe), psychographique (style de vie) et comportemental (fréquence d\'achat, fidélité).'),
            ('Réponse Q2', 'Pour une PME agroalimentaire régionale : Forces : savoir-faire artisanal, circuits courts. Faiblesses : capacité de production limitée. Opportunités : tendance bio. Menaces : grande distribution, coûts matières premières.'),
            ('Réponse Q3', 'Les 5 forces de Porter analysent l\'attractivité d\'un secteur : pouvoir des clients, fournisseurs, menace des substituts, menace des entrants, rivalité intrasectorielle.'),
            ('Réponse Q4', '(500 000 – 280 000) / 500 000 × 100 = 44 %. Ce taux mesure la rentabilité commerciale brute avant charges fixes.'),
            ('Réponse Q5', 'KPI : CA réalisé vs objectif, nombre de visites/semaine, taux de transformation, panier moyen, taux de fidélisation, coût d\'acquisition client.'),
        ],
    },
    {
        'score_pct': 0.65,
        'sections': [
            ('Réponse Q1', 'Le recrutement suit 6 étapes : 1) Définition du profil. 2) Choix des canaux. 3) Tri des candidatures. 4) Entretiens. 5) Vérification des références. 6) Onboarding.'),
            ('Réponse Q2', 'La GPEC anticipe les évolutions emplois/compétences sur 3 à 5 ans. Mise en place : diagnostic actuel, projection besoins, identification écarts, plan d\'action (formation, mobilité).'),
            ('Réponse Q3', 'Coût total = 1 200 + (45 000 × 15%) + 800 = 8 750 €.'),
            ('Réponse Q4', 'CDI : durée indéterminée, rupture par démission ou licenciement. CDD : limité à 18 mois, renouvelable 2 fois, prime de précarité 10%.'),
        ],
    },
    {
        'score_pct': 0.45,
        'sections': [
            ('Réponse Q1', 'McGregor décrit deux visions : Théorie X → l\'employé évite le travail, doit être contrôlé. Théorie Y → l\'employé cherche la responsabilité, est créatif.'),
            ('Réponse Q2', 'Hersey & Blanchard : 4 styles selon la maturité — Directif, Persuasif, Participatif, Délégatif.'),
            ('Réponse Q3', 'Le MBO fixe des objectifs mesurables. Avantages : motivation, clarté. Limites : rigidité, risque de bureaucratie.'),
            ('Réponse Q4', 'Kotter : 1-Urgence. 2-Coalition. 3-Vision. 4-Communication. 5-Obstacles. 6-Victoires rapides. 7-Consolidation. 8-Ancrage culturel.'),
        ],
    },
    {
        'score_pct': 0.90,
        'sections': [
            ('Réponse Q1', 'La segmentation : 4 critères — Géographique (zone), Démographique (âge, revenus), Psychographique (valeurs, lifestyle), Comportemental (fidélité, usage). Un bon segment est mesurable, accessible, différenciable et profitable.'),
            ('Réponse Q2', 'SWOT PME bio : Forces – produits authentiques, AB. Faiblesses – faible budget, saisonnalité. Opportunités – boom bio +9%/an. Menaces – entrée des GSS, aléas climatiques.'),
            ('Réponse Q3', 'Porter : Rivalité intrasectorielle, Pouvoir clients, Pouvoir fournisseurs, Nouveaux entrants, Substituts. Objectif : construire un avantage concurrentiel durable.'),
            ('Réponse Q4', '44%. Ce taux couvre les charges fixes et dégage du profit.'),
            ('Réponse Q5', 'CA par commercial, prospects/semaine, taux de conversion, NPS, closing, marge par vente. Tableau de bord hebdo + coaching mensuel.'),
        ],
    },
    {
        'score_pct': 0.30,
        'sections': [
            ('Réponse Q1', 'La segmentation c\'est diviser les clients par âge, lieu ou habitude.'),
            ('Réponse Q2', 'SWOT = forces, faiblesses, opportunités, menaces.'),
            ('Réponse Q3', 'Porter a créé un modèle pour analyser la concurrence avec 5 forces.'),
            ('Réponse Q4', '500 000 – 280 000 = 220 000 €.'),
        ],
    },
]

FEEDBACKS = [
    'Bonne maîtrise des concepts fondamentaux. Approfondissez les applications pratiques.',
    'Analyse pertinente. Manque de précision sur les calculs.',
    'Réponses trop courtes sur certaines questions théoriques.',
    'Excellent travail. Exemples bien choisis et raisonnement structuré.',
    'Effort visible mais les définitions manquent de rigueur académique.',
]


class Command(BaseCommand):
    help = "Upload sujets PDF pour examens sécurisés + copies étudiantes PDF soumises"

    def add_arguments(self, parser):
        parser.add_argument('--students', type=int, default=6,
                            help='Nombre max d\'étudiants par examen (défaut: 6)')
        parser.add_argument('--subjects-only', action='store_true',
                            help='Uploader seulement les sujets, sans copies étudiantes')

    def handle(self, *args, **options):
        from apps.elearning.models import SecureExam, ExamSession

        max_stu = options['students']
        subjects_only = options['subjects_only']

        try:
            from apps.students.models import Student
            students = list(Student.objects.select_related('user').all())
        except Exception:
            students = []

        teacher_user = None
        try:
            from apps.teachers.models import TeacherProfile
            t = TeacherProfile.objects.filter(is_active=True).first()
            teacher_user = t.user if t else None
        except Exception:
            pass

        exams = list(SecureExam.objects.filter(is_published=True).select_related('class_obj', 'subject')[:8])
        if not exams:
            self.stdout.write(self.style.WARNING('Aucun examen publié trouvé.'))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n=== Seed Exam Submissions — {len(exams)} examens ==='
        ))

        for exam in exams:
            subject_data = random.choice(EXAM_SUBJECTS)
            n_cop = 0

            # ── Sujet PDF (prof) ───────────────────────────────────────────────
            if not exam.subject_file:
                try:
                    meta = {
                        'Matière': getattr(exam.subject, 'name', ''),
                        'Classe': getattr(exam.class_obj, 'name', ''),
                        'Durée': f'{exam.duration_minutes} min',
                        'Barème': f'{exam.max_score or 20} pts',
                    }
                    pdf_bytes = _gen_subject(
                        title=subject_data['title'],
                        questions_list=subject_data['questions'],
                        meta_info=meta,
                        intro='Tout document est interdit. Répondez de manière structurée.',
                    )
                    exam.subject_file.save(f'sujet_{exam.id}.pdf', ContentFile(pdf_bytes), save=True)
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Sujet PDF : {exam.title[:50]}'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  ⚠ Sujet PDF impossible : {e}'))
            else:
                self.stdout.write(f'  → Sujet déjà présent : {exam.title[:50]}')

            if subjects_only or not students:
                continue

            # ── Copies étudiantes ──────────────────────────────────────────────
            sample = random.sample(students, min(max_stu, len(students)))
            past = exam.end_date and exam.end_date < timezone.now()

            for student in sample:
                if ExamSession.objects.filter(exam=exam, student=student).exists():
                    continue

                copy_data = random.choice(STUDENT_COPIES)
                score_pct = copy_data['score_pct']
                student_name = (
                    f"{student.user.first_name} {student.user.last_name}".strip()
                    or f"Étudiant {student.matricule}"
                )

                sub_pdf = None
                try:
                    sub_pdf = ContentFile(_gen_student(
                        student_name=student_name,
                        assignment_title=exam.title,
                        sections=copy_data['sections'],
                    ))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'    ⚠ PDF copie : {e}'))

                score_val = feedback_val = None
                cor_pdf = None
                if past:
                    max_s = float(exam.max_score or 20)
                    score_val = round(score_pct * max_s, 1)
                    feedback_val = random.choice(FEEDBACKS)
                    try:
                        cor_pdf = ContentFile(_gen_correction(
                            student_name=student_name,
                            assignment_title=exam.title,
                            score=score_val,
                            max_score=max_s,
                            feedback=feedback_val,
                            corrections=[('Appréciation', feedback_val)],
                        ))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'    ⚠ PDF correction : {e}'))

                ses = ExamSession(
                    exam=exam,
                    student=student,
                    status='SUBMITTED',
                    submitted_at=timezone.now() - timedelta(days=random.randint(1, 30)),
                    score=score_val,
                    feedback=feedback_val or '',
                    corrected_by=teacher_user if score_val is not None else None,
                    corrected_at=timezone.now() - timedelta(days=random.randint(0, 5)) if score_val is not None else None,
                )
                ses.save()

                if sub_pdf:
                    ses.submission_file.save(
                        f'copie_{student.matricule}_{exam.id}.pdf', sub_pdf, save=False,
                    )
                if cor_pdf:
                    ses.corrected_file.save(
                        f'correction_{student.matricule}_{exam.id}.pdf', cor_pdf, save=False,
                    )
                if sub_pdf or cor_pdf:
                    ses.save()
                n_cop += 1

            self.stdout.write(self.style.SUCCESS(
                f'  ✓ {exam.title[:55]} → {n_cop} copies étudiantes'
            ))

        self.stdout.write(self.style.SUCCESS('\n✅ Seed exam submissions terminé.'))
