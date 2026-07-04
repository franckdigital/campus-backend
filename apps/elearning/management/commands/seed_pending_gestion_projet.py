"""
seed_pending_gestion_projet.py
──────────────────────────────
Crée 5 sujets en Gestion de Projet uploadés par l'admin/prof
(évaluation, exercice, 2 devoirs, 1 examen sécurisé).
Aucune soumission étudiant → les étudiants doivent traiter et soumettre.

Usage :
    python manage.py seed_pending_gestion_projet
    python manage.py seed_pending_gestion_projet --class-code BTS-M1
"""

import random
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils import timezone
from datetime import timedelta

from apps.elearning.management.commands.pdf_canvas_utils import (
    generate_exam_subject_pdf as _gen_subject,
)


# ─── Définition des 5 sujets ──────────────────────────────────────────────────

SUBJECTS_DATA = [
    # ── 1. Évaluation (Quiz TEXT) ─────────────────────────────────────────────
    {
        'type': 'quiz',
        'title': 'Évaluation — Fondamentaux de la Gestion de Projet',
        'description': 'Évaluation individuelle portant sur les concepts de base du management de projet.',
        'questions': [
            {
                'text': 'Définissez le triangle de contraintes en gestion de projet (Qualité – Coût – Délai) et expliquez comment un chef de projet doit arbitrer entre ces trois dimensions.',
                'qtype': 'TEXT',
                'points': 4,
            },
            {
                'text': 'Quelles sont les principales différences entre la méthode en cascade (Waterfall) et les méthodes agiles (Scrum) ? Dans quel contexte privilégieriez-vous chacune ?',
                'qtype': 'TEXT',
                'points': 4,
            },
            {
                'text': 'Décrivez le rôle du chef de projet et listez 5 compétences essentielles qu\'il doit posséder.',
                'qtype': 'TEXT',
                'points': 3,
            },
            {
                'text': 'Qu\'est-ce qu\'un diagramme de Gantt ? Quelles informations doit-il obligatoirement contenir ?',
                'qtype': 'TEXT',
                'points': 3,
            },
            {
                'text': 'Vrai ou Faux : Le scope creep (dérive des objectifs) est toujours bénéfique au projet car il apporte de nouvelles fonctionnalités. Justifiez votre réponse.',
                'qtype': 'TEXT',
                'points': 2,
            },
            {
                'text': 'Expliquez la méthode d\'analyse des risques AMDEC et donnez un exemple d\'application dans un projet informatique.',
                'qtype': 'TEXT',
                'points': 4,
            },
        ],
        'time_limit': 60,
        'max_score': 20,
        'pdf_title': 'Évaluation individuelle — Gestion de Projet',
        'pdf_intro': 'Répondez à chaque question de manière structurée. Justifiez vos réponses avec des exemples concrets issus du cours ou de votre expérience.',
    },
    # ── 2. Exercice (Quiz avec QCU + TEXT) ────────────────────────────────────
    {
        'type': 'quiz',
        'title': 'Exercice pratique — Planification et Gantt',
        'description': 'Exercice de planification de projet avec construction d\'un diagramme de Gantt.',
        'questions': [
            {
                'text': 'Un projet de développement d\'une application mobile a les tâches suivantes : (A) Cahier des charges 5j, (B) Design UI 8j après A, (C) Développement back-end 15j après A, (D) Développement front-end 12j après B, (E) Tests 6j après C et D, (F) Déploiement 2j après E. Calculez la durée totale du projet et identifiez le chemin critique.',
                'qtype': 'TEXT',
                'points': 6,
            },
            {
                'text': 'En gestion de projet, que signifie l\'acronyme WBS (Work Breakdown Structure) ?',
                'qtype': 'QCU',
                'points': 2,
                'choices': [
                    ('Structure de découpage du travail', True),
                    ('Tableau de bord hebdomadaire', False),
                    ('Système de suivi des bugs', False),
                    ('Plan de communication', False),
                ],
            },
            {
                'text': 'Parmi ces éléments, lesquels font partie du triangle des contraintes d\'un projet ?',
                'qtype': 'QCM',
                'points': 2,
                'choices': [
                    ('Coût', True),
                    ('Délai', True),
                    ('Qualité / Périmètre', True),
                    ('Couleur du logo', False),
                ],
            },
            {
                'text': 'La méthode PERT permet de calculer la durée optimale d\'un projet en identifiant le chemin critique.',
                'qtype': 'TRUEFALSE',
                'points': 1,
                'choices': [
                    ('Vrai', True),
                    ('Faux', False),
                ],
            },
            {
                'text': 'Votre projet de 6 mois dépasse de 20% son budget initial. Rédigez en 10 lignes le plan d\'action que vous proposeriez au comité de pilotage pour redresser la situation.',
                'qtype': 'TEXT',
                'points': 5,
            },
            {
                'text': 'Le nombre maximum de relations de dépendance entre 5 tâches dans un réseau PERT peut être au maximum de :',
                'qtype': 'NUMERIC',
                'points': 2,
                'numeric_answer': 10,
                'numeric_tolerance': 0,
            },
            {
                'text': 'Décrivez la cérémonie "Sprint Review" dans la méthode Scrum : qui y participe, quel est son objectif et quelle est sa durée recommandée ?',
                'qtype': 'TEXT',
                'points': 2,
            },
        ],
        'time_limit': 45,
        'max_score': 20,
        'pdf_title': 'Exercice — Planification et Diagramme de Gantt',
        'pdf_intro': 'Cet exercice porte sur la planification d\'un projet réel. Lisez attentivement chaque énoncé avant de répondre.',
    },
    # ── 3. Devoir 1 ───────────────────────────────────────────────────────────
    {
        'type': 'assignment',
        'title': 'Devoir de synthèse — Méthodes Agiles et Scrum',
        'description': 'Étude comparative des méthodes agiles Scrum, Kanban et SAFe dans le contexte de la transformation digitale des entreprises.',
        'instructions': (
            '1. Présentez les 3 méthodes agiles (Scrum, Kanban, SAFe) et leurs différences fondamentales.\n'
            '2. Analysez les avantages et inconvénients de chaque méthode.\n'
            '3. Proposez quelle méthode conviendrait le mieux pour une startup de 15 personnes et pour une grande entreprise (500+ personnes).\n'
            '4. Le rapport doit faire entre 8 et 12 pages, références bibliographiques incluses.\n'
            '5. Format : police Times New Roman 12, interligne 1.5, marges 2.5 cm.'
        ),
        'max_score': 20,
        'due_days': 14,
        'pdf_questions': [
            ('Partie 1 — Comparatif des méthodes agiles (6 pts)',
             'Présentez et comparez Scrum, Kanban et SAFe sur les dimensions : structure, cérémonies, artefacts, échelle, et complexité de mise en œuvre.'),
            ('Partie 2 — Avantages et limites (6 pts)',
             'Pour chaque méthode, identifiez 3 avantages et 3 limitations. Illustrez avec des exemples d\'entreprises ayant adopté ces méthodes.'),
            ('Partie 3 — Recommandation contextuelle (5 pts)',
             'En vous basant sur votre analyse, quelle méthode recommanderiez-vous pour : (a) une startup e-commerce de 12 personnes, (b) une banque de 2000 employés en transformation digitale ? Justifiez.'),
            ('Partie 4 — Plan de mise en œuvre (3 pts)',
             'Rédigez un plan de déploiement en 4 étapes pour l\'adoption de Scrum dans une équipe de 8 développeurs.'),
        ],
    },
    # ── 4. Devoir 2 ───────────────────────────────────────────────────────────
    {
        'type': 'assignment',
        'title': 'Cas pratique — Gestion des risques et plan de mitigation',
        'description': 'Analyse des risques d\'un projet de construction d\'un entrepôt logistique et élaboration d\'un plan de mitigation.',
        'instructions': (
            'Vous êtes chef de projet pour la construction d\'un entrepôt logistique de 5 000 m².\n'
            'Budget : 2 M€ · Délai : 18 mois · Livraison : mars 2026.\n\n'
            'Travail demandé :\n'
            '1. Identifiez au moins 10 risques potentiels du projet (techniques, financiers, humains, réglementaires).\n'
            '2. Construisez une matrice de risques (Probabilité × Impact).\n'
            '3. Pour les 5 risques les plus critiques, proposez un plan de mitigation détaillé.\n'
            '4. Rédigez un registre des risques au format tableau.\n'
            'Rendu : fichier PDF de 5 à 8 pages.'
        ),
        'max_score': 20,
        'due_days': 10,
        'pdf_questions': [
            ('Section A — Identification des risques (5 pts)',
             'Identifiez et catégorisez au minimum 10 risques en précisant pour chacun : description, catégorie (Technique / Financier / Humain / Réglementaire / Environnemental), probabilité (1-5) et impact (1-5).'),
            ('Section B — Matrice de criticité (5 pts)',
             'Construisez une matrice de risques 5×5 (Probabilité × Impact) en positionnant vos risques. Identifiez les zones rouge (critique), orange (élevé), jaune (modéré) et vert (faible).'),
            ('Section C — Plans de mitigation (7 pts)',
             'Pour les 5 risques les plus critiques (score ≥ 12), rédigez un plan de mitigation complet incluant : actions préventives, actions correctives, responsable, budget alloué, indicateur de suivi.'),
            ('Section D — Registre des risques (3 pts)',
             'Présentez l\'ensemble des risques sous forme de tableau (Registre des risques) avec colonnes : ID, Risque, Probabilité, Impact, Score, Statut, Responsable, Plan d\'action.'),
        ],
    },
    # ── 5. Examen sécurisé ────────────────────────────────────────────────────
    {
        'type': 'exam',
        'title': 'Examen partiel — Management et Pilotage de Projet',
        'description': 'Examen partiel portant sur les outils et méthodes de pilotage de projets complexes.',
        'exam_type': 'MID',
        'duration': 120,
        'max_score': 20,
        'pdf_questions': [
            ('Question 1 (4 pts)',
             'Un projet présente les données suivantes au 31ème jour : CBTP = 80 000 €, CBTE = 65 000 €, CRTE = 72 000 €. Calculez et interprétez : (a) l\'écart de coût (EC), (b) l\'écart de délai (ED), (c) l\'indice de performance coût (IPC), (d) l\'indice de performance délai (IPD). Que concluez-vous sur l\'avancement du projet ?'),
            ('Question 2 (5 pts)',
             'Vous gérez un projet de migration vers le cloud pour une PME (50 salariés, 8 mois, 400k€). Décrivez votre approche de gestion du changement en vous appuyant sur le modèle de Kotter en 8 étapes. Quels sont les 3 principaux risques humains auxquels vous vous attendez ?'),
            ('Question 3 (4 pts)',
             'Comparez le rôle du Scrum Master et du Product Owner dans la méthode Scrum. Donnez 3 situations où un conflit peut émerger entre ces deux rôles et expliquez comment les résoudre.'),
            ('Question 4 (4 pts)',
             'Un projet accuse un retard de 3 semaines sur 6 mois de planning. Le client est informé. Rédigez un plan de rattrapage en 5 actions concrètes chiffrées (coût, délai) pour récupérer ce retard sans dépasser le budget.'),
            ('Question 5 (3 pts)',
             'Définissez les concepts suivants et donnez un exemple pour chacun : (a) Vélocité en Scrum, (b) Chemin critique, (c) Jalons de projet (Milestones).'),
        ],
    },
]



def generate_subject_pdf(title, intro, questions_list, meta_info=None):
    """Délègue à pdf_canvas_utils (canvas-based, fiable sur tout serveur)."""
    return _gen_subject(title=title, questions_list=questions_list,
                        meta_info=meta_info, intro=intro)


class Command(BaseCommand):
    help = "Crée 5 sujets Gestion de Projet (éval, exercice, 2 devoirs, examen) sans soumissions étudiantes"

    def add_arguments(self, parser):
        parser.add_argument('--class-code', type=str, default='',
                            help='Code de la classe cible (ex : BTS-M1). Par défaut : première classe active.')

    def handle(self, *args, **options):
        from apps.elearning.models import Quiz, Question, Choice, Assignment, SecureExam
        from apps.academic.models import Class as ClassModel, Subject

        try:
            from apps.academic.models import TeacherProfile
        except ImportError:
            TeacherProfile = None

        # ── Trouver la classe ──────────────────────────────────────────────────
        class_code = options.get('class_code', '').strip()
        if class_code:
            cls = ClassModel.objects.filter(code__icontains=class_code, is_active=True).first()
        else:
            cls = ClassModel.objects.filter(is_active=True).first()

        if not cls:
            self.stdout.write(self.style.ERROR('Aucune classe active trouvée. Lancez d\'abord seed_elearning ou seed_classes.'))
            return

        self.stdout.write(f'  Classe cible : {cls.code} — {cls.name}')

        # ── Trouver ou créer le sujet Gestion de Projet ───────────────────────
        subj, created = Subject.objects.get_or_create(
            code='GP-001',
            defaults={
                'name': 'Gestion de Projet',
                'description': 'Management, planification et pilotage de projets.',
                'coefficient': 2,
                'hours_per_week': 3,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Matière créée : {subj.name}'))
        else:
            self.stdout.write(f'  → Matière existante : {subj.name}')

        # ── Trouver le prof ────────────────────────────────────────────────────
        teacher = None
        if TeacherProfile:
            teacher = TeacherProfile.objects.filter(is_active=True).first()

        # ── Créer les 5 sujets ────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n=== Création des 5 sujets Gestion de Projet ==='
        ))

        created_items = []

        for s_data in SUBJECTS_DATA:
            s_type = s_data['type']

            # ─ QUIZ (évaluation / exercice) ────────────────────────────────────
            if s_type == 'quiz':
                quiz = Quiz.objects.create(
                    title=s_data['title'],
                    description=s_data['description'],
                    class_obj=cls,
                    subject=subj,
                    time_limit_minutes=s_data.get('time_limit', 60),
                    pass_score_percent=50,
                    shuffle_questions=False,
                    is_published=True,
                )

                total_pts = 0
                for q_idx, q_data in enumerate(s_data['questions'], 1):
                    q = Question(
                        quiz=quiz,
                        question_type=q_data['qtype'],
                        text=q_data['text'],
                        points=q_data['points'],
                        order=q_idx,
                    )
                    if q_data['qtype'] == 'NUMERIC':
                        q.numeric_answer = q_data.get('numeric_answer', 0)
                        q.numeric_tolerance = q_data.get('numeric_tolerance', 0)
                    q.save()
                    total_pts += q_data['points']

                    if 'choices' in q_data:
                        for c_idx, (c_text, c_correct) in enumerate(q_data['choices'], 1):
                            Choice.objects.create(
                                question=q,
                                text=c_text,
                                is_correct=c_correct,
                                order=c_idx,
                            )

                # PDF sujet
                meta = {
                    'Matière': 'Gestion de Projet',
                    'Durée': f"{s_data.get('time_limit', 60)} min",
                    'Barème': f'{total_pts} pts',
                }
                q_list = [(f'Q{i+1} ({q["points"]} pt{"s" if q["points"] > 1 else ""})', q['text'])
                          for i, q in enumerate(s_data['questions'])]
                try:
                    pdf = generate_subject_pdf(
                        title=s_data.get('pdf_title', s_data['title']),
                        intro=s_data.get('pdf_intro', ''),
                        questions_list=q_list,
                        meta_info=meta,
                    )
                    quiz.subject_file.save(f'sujet_quiz_{quiz.id}.pdf', ContentFile(pdf), save=True)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'    ⚠ PDF impossible : {e}'))

                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ Quiz créé : {quiz.title[:60]} ({len(s_data["questions"])} questions)'
                ))
                created_items.append({'type': 'Quiz', 'id': str(quiz.id), 'title': quiz.title})

            # ─ ASSIGNMENT (devoir) ─────────────────────────────────────────────
            elif s_type == 'assignment':
                from django.utils import timezone
                due = timezone.now() + timedelta(days=s_data.get('due_days', 14))

                assign = Assignment.objects.create(
                    title=s_data['title'],
                    description=s_data['description'],
                    instructions=s_data.get('instructions', ''),
                    class_obj=cls,
                    subject=subj,
                    teacher=teacher,
                    due_date=due,
                    max_score=s_data.get('max_score', 20),
                    status='PUBLISHED',
                    published_at=timezone.now(),
                    allow_late_submission=True,
                    late_penalty_percent=5,
                )

                # PDF sujet devoir
                meta = {
                    'Matière': 'Gestion de Projet',
                    'Classe': cls.name,
                    'Rendu': due.strftime('%d/%m/%Y'),
                    'Barème': f'{assign.max_score} pts',
                }
                try:
                    pdf = generate_subject_pdf(
                        title=s_data['title'],
                        intro=s_data.get('instructions', ''),
                        questions_list=[(t, txt) for t, txt in s_data.get('pdf_questions', [])],
                        meta_info=meta,
                    )
                    assign.attachment.save(f'sujet_devoir_{assign.id}.pdf', ContentFile(pdf), save=True)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'    ⚠ PDF impossible : {e}'))

                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ Devoir créé : {assign.title[:60]} (rendu : {due.strftime("%d/%m")})'
                ))
                created_items.append({'type': 'Devoir', 'id': str(assign.id), 'title': assign.title})

            # ─ SECURE EXAM ─────────────────────────────────────────────────────
            elif s_type == 'exam':
                start = timezone.now() + timedelta(days=3)
                end   = start + timedelta(hours=s_data.get('duration', 120) // 60 + 2)

                exam = SecureExam.objects.create(
                    title=s_data['title'],
                    description=s_data.get('description', ''),
                    class_obj=cls,
                    subject=subj,
                    exam_type=s_data.get('exam_type', 'MID'),
                    duration_minutes=s_data.get('duration', 120),
                    start_date=start,
                    end_date=end,
                    max_score=s_data.get('max_score', 20),
                    pass_score_percent=50,
                    fullscreen_required=True,
                    block_copy_paste=True,
                    max_tab_switches=3,
                    is_published=True,
                )

                # PDF sujet examen
                meta = {
                    'Type': 'Partiel',
                    'Durée': f"{exam.duration_minutes} min",
                    'Date': start.strftime('%d/%m/%Y %H:%M'),
                    'Barème': f'{exam.max_score} pts',
                }
                try:
                    pdf = generate_subject_pdf(
                        title=s_data['title'],
                        intro=(
                            'Tout document est interdit. Répondez de manière structurée et argumentée. '
                            'Chaque point est noté sur le barème indiqué. '
                            'Les téléphones et tablettes doivent être rangés.'
                        ),
                        questions_list=[(t, txt) for t, txt in s_data.get('pdf_questions', [])],
                        meta_info=meta,
                    )
                    exam.subject_file.save(f'sujet_examen_{exam.id}.pdf', ContentFile(pdf), save=True)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'    ⚠ PDF impossible : {e}'))

                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ Examen créé : {exam.title[:60]}'
                ))
                created_items.append({'type': 'Examen', 'id': str(exam.id), 'title': exam.title})

        # ── Résumé ────────────────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Résumé ==='))
        for item in created_items:
            self.stdout.write(f'  [{item["type"]}] {item["title"][:70]}')
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ {len(created_items)} sujets créés — les étudiants peuvent maintenant les traiter et soumettre.\n'
            f'   Aucune soumission étudiante n\'a été créée → attente de travaux réels.\n'
            f'   Les profs peuvent corriger via /admin ou CorrectionHub.'
        ))
