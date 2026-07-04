"""
seed_student_submissions_pdf.py
────────────────────────────────
Crée des soumissions PDF d'étudiants pour devoirs, examens et quiz,
+ corrections PDF du prof (corrected_file).
PDF générés via pdf_canvas_utils (canvas.Canvas — fiable sur tout serveur).

Usage :
    python manage.py seed_student_submissions_pdf
    python manage.py seed_student_submissions_pdf --clear
    python manage.py seed_student_submissions_pdf --type assignment
    python manage.py seed_student_submissions_pdf --type exam
"""

import random
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.elearning.management.commands.pdf_canvas_utils import (
    generate_student_submission_pdf as _gen_student,
    generate_correction_pdf as _gen_correction,
)


# ─── Contenu fictif des copies étudiantes ─────────────────────────────────────

STUDENT_ANSWERS = [
    {
        'title': 'Analyse du marché et stratégie commerciale',
        'content': [
            ('Introduction', "Dans ce travail, j'analyserai le marché de la grande distribution en France en appliquant les outils vus en cours : SWOT, PESTEL et les 5 forces de Porter."),
            ('Analyse SWOT', "Forces : notoriété de la marque, réseau de distribution étendu.\nFaiblesses : marges faibles, dépendance aux fournisseurs.\nOpportunités : croissance du e-commerce, demande bio en hausse.\nMenaces : concurrence des hard-discounts, inflation des matières premières."),
            ('Analyse PESTEL', "Politique : réglementations sur les emballages plastiques (loi AGEC).\nÉconomique : pouvoir d'achat en baisse → report vers les MDD.\nSocial : consommateurs plus exigeants sur la traçabilité.\nTechnologique : digitalisation des points de vente, self-checkout.\nEnvironnemental : bilan carbone, déchets alimentaires.\nLégal : loi EGAlim, négociations commerciales annuelles."),
            ('Recommandations', "Je préconise une stratégie de différenciation par la qualité et le local, avec un renforcement de l'offre en ligne (click-and-collect)."),
        ],
    },
    {
        'title': 'Cas pratique RH — Gestion des conflits en entreprise',
        'content': [
            ('Présentation du cas', "L'entreprise TechPME (150 salariés, secteur informatique) fait face à un conflit entre l'équipe commerciale et l'équipe technique."),
            ('Diagnostic du conflit', "Type de conflit : inter-groupes (commercial vs. technique).\nCauses profondes :\n1. Objectifs divergents (CA immédiat vs. qualité produit)\n2. Communication insuffisante entre les équipes\n3. Absence de référent transverse"),
            ('Plan d\'action proposé', "1. Médiation externe (3 séances)\n2. Atelier co-construction des objectifs partagés\n3. Mise en place d'un comité de pilotage mixte\n4. Révision du système d'évaluation et de rémunération variable\n5. Formation communication non-violente pour les managers"),
            ('Conclusion', "Ce conflit révèle un problème structurel d'organisation. La résolution durable passe par une refonte partielle de la culture managériale."),
        ],
    },
    {
        'title': 'Rapport — Leadership et styles de management',
        'content': [
            ('Introduction', "Ce rapport examine les quatre grands styles de leadership selon Hersey & Blanchard et analyse leur application dans le contexte de l'entreprise moderne."),
            ('Les 4 styles de management', "1. Directif (S1) : adapté aux collaborateurs débutants.\n2. Persuasif (S2) : le manager explique et motive.\n3. Participatif (S3) : le manager délègue la réflexion.\n4. Délégatif (S4) : autonomie totale."),
            ('Étude de cas : Amazon vs. Patagonia', "Amazon : management directif et par objectifs chiffrés (OKR). Forte pression de performance.\nPatagonia : management délégatif, culture de confiance, faible turnover."),
            ('Conclusion', "Il n'existe pas de style universellement supérieur. L'efficacité du leadership repose sur l'adéquation entre le style et la situation."),
        ],
    },
    {
        'title': 'Analyse financière — Compte de résultat et rentabilité',
        'content': [
            ('Présentation de l\'entreprise', "Entreprise analysée : Carrefour SA. Données issues du rapport annuel 2023."),
            ('Analyse du compte de résultat', "Chiffre d'affaires : 88,2 Md€ (+4,2% vs. 2022)\nRBE (EBITDA) : 3,8 Md€ — marge EBITDA : 4,3%\nRésultat net part du groupe : 612 M€"),
            ('Calcul des ratios', "Marge brute : 22,4%\nMarge opérationnelle : 1,6%\nROE : 8,2%\nROCE : 6,7%\nDette nette/EBITDA : 2,3x"),
            ('Conclusion et recommandations', "La rentabilité reste sous pression malgré la reprise post-Covid. La diversification vers les services devrait améliorer les marges à terme."),
        ],
    },
    {
        'title': 'Plan de recrutement et GPEC',
        'content': [
            ('Contexte', "La société LogiTrans (transport & logistique, 800 salariés) souhaite développer sa branche e-commerce. Elle doit recruter 45 personnes en 18 mois."),
            ('Analyse des besoins', "Postes prioritaires :\n- 12 gestionnaires de stock (BTS/Licence)\n- 8 développeurs full-stack (Bac+5)\n- 10 commerciaux terrain (BTS force de vente)"),
            ('Processus de recrutement proposé', "Phase 1 : Sourcing (jobboards, LinkedIn, cooptation)\nPhase 2 : Pré-sélection (CV + questionnaire)\nPhase 3 : Entretiens (RH + opérationnel)\nPhase 4 : Onboarding 30 jours"),
            ('Budget et ROI', "Coût total recrutement estimé : 285 000€\nROI attendu à 18 mois : CA e-commerce supplémentaire de 4,2 M€"),
        ],
    },
]

STUDENT_CORRECTIONS = [
    {
        'feedback': 'Excellent travail ! Analyse rigoureuse et bien structurée. Les recommandations sont pertinentes et argumentées.',
        'corrections': [
            ('Q1', "L'analyse SWOT est complète et cohérente avec les données du secteur."),
            ('Q2', "L'analyse PESTEL intègre bien la dimension légale (loi AGEC)."),
            ('Q3', "Les recommandations manquent de chiffrage. Prévoir des KPI mesurables."),
        ],
    },
    {
        'feedback': 'Bonne compréhension du cas. Le plan d\'action manque de réalisme budgétaire — chiffrez les actions.',
        'corrections': [
            ('Q1', "Diagnostic pertinent. Les causes profondes sont bien identifiées."),
            ('Q2', "Application correcte mais la nuance S3 aurait été appropriée."),
            ('Q3', "Plan d'action trop général. Manque de planification (qui fait quoi, quand)."),
        ],
    },
    {
        'feedback': 'Travail solide sur les styles de management. Développez davantage la partie leadership situationnel.',
        'corrections': [
            ('Q1', "Les 4 styles sont bien décrits. La référence à Hersey & Blanchard est correcte."),
            ('Q2', "Bonne analyse comparative mais manque de données chiffrées."),
            ('Q3', "L'exemple est valorisé. Bien ancré dans la réalité professionnelle."),
        ],
    },
    {
        'feedback': 'Analyse financière correcte. Les ratios sont bien calculés. Attention à l\'analyse sectorielle.',
        'corrections': [
            ('Ratios', "Calculs exacts. La marge opérationnelle est cohérente avec le secteur."),
            ('Comparaison', "Comparer avec Aldi n'est pas pertinent structurellement."),
            ('Conclusion', "Recommandations réalistes. La diversification services est bien identifiée."),
        ],
    },
    {
        'feedback': 'Très bon plan de recrutement. La GPEC est traitée avec sérieux. Le budget est réaliste.',
        'corrections': [
            ('Sourcing', "Mix de canaux pertinent. La cooptation est souvent sous-utilisée."),
            ('KPI', "Les KPI sont mesurables. Ajouter le coût par embauche (CPH) au tableau de bord."),
            ('GPEC', "Cartographie correcte. Manque la matrice compétences actuelles vs. cibles."),
        ],
    },
]


class Command(BaseCommand):
    help = 'Crée des copies PDF étudiantes + corrections PDF prof pour devoirs et examens'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                            help='Supprime les soumissions existantes avant de recréer')
        parser.add_argument('--type', choices=['assignment', 'exam', 'all'], default='all',
                            help='Type de travaux (défaut: all)')
        parser.add_argument('--max-students', type=int, default=8,
                            help='Nombre max d\'étudiants par devoir/exam (défaut: 8)')

    def handle(self, *args, **options):
        from apps.elearning.models import (
            Assignment, AssignmentSubmission, AssignmentCorrection,
            SecureExam, ExamSession,
        )
        from apps.students.models import Student

        target = options.get('type', 'all')
        max_stu = options.get('max_students', 8)

        self.stdout.write(self.style.MIGRATE_HEADING(f'=== Seed Soumissions PDF ({target}) ===\n'))

        students = list(Student.objects.select_related('user').all()[:30])
        if not students:
            self.stdout.write(self.style.ERROR('Aucun étudiant trouvé.'))
            return

        if options.get('clear'):
            if target in ('assignment', 'all'):
                n = AssignmentSubmission.objects.all().delete()[0]
                self.stdout.write(self.style.WARNING(f'  {n} soumissions supprimées'))
            if target in ('exam', 'all'):
                n = ExamSession.objects.all().delete()[0]
                self.stdout.write(self.style.WARNING(f'  {n} sessions examen supprimées'))

        if target in ('assignment', 'all'):
            self._seed_assignments(Assignment, AssignmentSubmission, AssignmentCorrection, students, max_stu)

        if target in ('exam', 'all'):
            self._seed_exams(SecureExam, ExamSession, students, max_stu)

        self.stdout.write(self.style.SUCCESS('\n✅ Soumissions PDF créées avec succès.'))

    # ── Devoirs ───────────────────────────────────────────────────────────────

    def _seed_assignments(self, Assignment, AssignmentSubmission, AssignmentCorrection, students, max_stu):
        self.stdout.write(self.style.MIGRATE_HEADING('\n— Devoirs —'))
        assignments = list(Assignment.objects.filter(status='PUBLISHED').select_related('class_obj', 'subject')[:10])
        if not assignments:
            self.stdout.write(self.style.WARNING('  Aucun devoir publié.'))
            return

        teacher_user_id = (
            Assignment.objects.filter(teacher__isnull=False)
            .values_list('teacher__user_id', flat=True)
            .first()
        )

        for assignment in assignments:
            sample = random.sample(students, min(max_stu, len(students)))
            n_sub = n_cor = 0

            for student in sample:
                if AssignmentSubmission.objects.filter(assignment=assignment, student=student).exists():
                    continue

                ans_data = random.choice(STUDENT_ANSWERS)
                student_name = (
                    f"{student.user.first_name} {student.user.last_name}".strip()
                    or f"Étudiant {student.matricule}"
                )

                # PDF copie étudiant
                sub_pdf = None
                try:
                    sub_pdf = ContentFile(_gen_student(
                        student_name=student_name,
                        assignment_title=assignment.title,
                        sections=ans_data['content'],
                    ))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'    ⚠ PDF copie : {e}'))

                sub = AssignmentSubmission(
                    assignment=assignment,
                    student=student,
                    content='\n\n'.join(f'{t}\n{b}' for t, b in ans_data['content'][:2]),
                    status='SUBMITTED',
                )
                if sub_pdf:
                    sub.file.save(f'copie_{student.matricule}_{assignment.id}.pdf', sub_pdf, save=False)
                sub.save()
                n_sub += 1

                # Correction pour ~70% des devoirs passés
                is_past = assignment.due_date < timezone.now()
                if is_past and random.random() < 0.70:
                    max_s = float(assignment.max_score)
                    score = round(random.uniform(max_s * 0.35, max_s), 1)
                    cor_data = random.choice(STUDENT_CORRECTIONS)

                    cor_pdf = None
                    try:
                        cor_pdf = ContentFile(_gen_correction(
                            student_name=student_name,
                            assignment_title=assignment.title,
                            score=score,
                            max_score=max_s,
                            feedback=cor_data['feedback'],
                            corrections=cor_data['corrections'],
                        ))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'    ⚠ PDF correction : {e}'))

                    cor = AssignmentCorrection(
                        submission=sub,
                        score=score,
                        feedback=cor_data['feedback'],
                        corrected_by_id=teacher_user_id,
                    )
                    if cor_pdf:
                        cor.corrected_file.save(
                            f'correction_{student.matricule}_{assignment.id}.pdf',
                            cor_pdf, save=False,
                        )
                    cor.save()
                    n_cor += 1

            self.stdout.write(self.style.SUCCESS(
                f'  ✓ {assignment.title[:55]} → {n_sub} copies, {n_cor} corrections'
            ))

    # ── Examens ───────────────────────────────────────────────────────────────

    def _seed_exams(self, SecureExam, ExamSession, students, max_stu):
        self.stdout.write(self.style.MIGRATE_HEADING('\n— Examens —'))
        exams = list(SecureExam.objects.filter(is_published=True).select_related('class_obj', 'subject')[:8])
        if not exams:
            self.stdout.write(self.style.WARNING('  Aucun examen publié.'))
            return

        teacher_user_id = None
        try:
            from apps.teachers.models import TeacherProfile
            t = TeacherProfile.objects.filter(is_active=True).first()
            teacher_user_id = t.user_id if t else None
        except Exception:
            pass

        for exam in exams:
            past = exam.end_date and exam.end_date < timezone.now()
            sample = random.sample(students, min(max_stu, len(students)))
            n_ses = n_cor = 0

            for student in sample:
                if ExamSession.objects.filter(exam=exam, student=student).exists():
                    continue

                student_name = (
                    f"{student.user.first_name} {student.user.last_name}".strip()
                    or f"Étudiant {student.matricule}"
                )

                score_val = feedback_val = None
                cor_pdf = None

                if past and random.random() < 0.75:
                    max_s = float(exam.max_score or 20)
                    score_val = round(random.uniform(max_s * 0.30, max_s), 1)
                    cor_data = random.choice(STUDENT_CORRECTIONS)
                    feedback_val = cor_data['feedback']
                    try:
                        cor_pdf = ContentFile(_gen_correction(
                            student_name=student_name,
                            assignment_title=exam.title,
                            score=score_val,
                            max_score=max_s,
                            feedback=feedback_val,
                            corrections=cor_data['corrections'],
                        ))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'    ⚠ PDF correction exam : {e}'))

                ses = ExamSession(
                    exam=exam,
                    student=student,
                    status='SUBMITTED' if past else 'STARTED',
                    submitted_at=exam.end_date if past else None,
                    score=score_val,
                    feedback=feedback_val or '',
                    corrected_by_id=teacher_user_id if score_val is not None else None,
                    corrected_at=timezone.now() if score_val is not None else None,
                )
                if cor_pdf:
                    ses.corrected_file.save(
                        f'exam_correction_{student.matricule}_{exam.id}.pdf',
                        cor_pdf, save=False,
                    )
                ses.save()
                n_ses += 1
                if score_val is not None:
                    n_cor += 1

            self.stdout.write(self.style.SUCCESS(
                f'  ✓ {exam.title[:55]} → {n_ses} sessions, {n_cor} corrigées'
            ))
