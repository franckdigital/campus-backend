"""
seed_quiz_attempts.py
─────────────────────
Crée des tentatives de quiz réalistes pour les étudiants.
Les réponses QCU/QCM/TRUEFALSE sont auto-notées.
Les réponses TEXT restent en attente de correction manuelle du prof.
Toutes les réponses texte sont dans les domaines :
gestion commerciale, ressources humaines, management.
"""

import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta


# ─── Réponses texte libre (domaines commerce/RH/management) ──────────────────

BUSINESS_TEXT_RESPONSES = [
    "La segmentation du marché permet d'identifier des groupes homogènes de consommateurs "
    "partageant les mêmes besoins. On distingue la segmentation géographique, "
    "démographique, psychographique et comportementale. Cette démarche est essentielle "
    "pour adapter l'offre et maximiser la valeur client.",

    "Le modèle PESTEL analyse les facteurs macro-environnementaux : Politique, Économique, "
    "Social, Technologique, Environnemental et Légal. Il permet d'identifier les opportunités "
    "et menaces pesant sur l'entreprise et de cadrer la réflexion stratégique.",

    "La gestion prévisionnelle des emplois et compétences (GPEC) anticipe les besoins "
    "en ressources humaines à moyen terme. Elle croise les compétences disponibles avec "
    "celles requises par la stratégie de l'entreprise, puis planifie les actions de "
    "formation, recrutement ou mobilité interne.",

    "La méthode SPIN Selling (Situation, Problème, Implication, Need-Payoff) structure "
    "l'entretien de vente autour de questions ouvertes pour révéler les besoins implicites "
    "du client. Elle favorise une vente consultative plutôt que transactionnelle.",

    "Le balanced scorecard (BSC) de Kaplan & Norton décline la stratégie d'entreprise "
    "en objectifs mesurables selon quatre axes : financier, client, processus internes, "
    "et apprentissage/développement. Chaque axe comporte des indicateurs clés de performance.",

    "Le taux de turnover se calcule comme suit : (Départs + Arrivées) / 2 ÷ Effectif moyen × 100. "
    "Un taux élevé traduit des problèmes de rétention et engendre des coûts de recrutement "
    "et formation importants. Les leviers d'action incluent l'amélioration de l'onboarding "
    "et la politique de rémunération.",

    "La négociation BATNA (Best Alternative To a Negotiated Agreement) désigne la meilleure "
    "option disponible si les négociations échouent. Connaître son BATNA donne du pouvoir "
    "en négociation : on accepte un accord uniquement s'il est meilleur que cette alternative.",

    "La matrice BCG (Boston Consulting Group) classe les unités stratégiques selon leur "
    "part de marché relative et la croissance du marché : Étoile, Vache à lait, Dilemme, "
    "Poids mort. Elle guide les décisions d'allocation de ressources entre les activités.",

    "Le recrutement par cooptation consiste à solliciter les collaborateurs pour recommander "
    "des candidats de leur réseau. Avantages : coût réduit, intégration facilitée, meilleure "
    "adéquation culturelle. Inconvénient : risque d'homogénéité des profils et de favoritisme.",

    "L'entretien annuel d'évaluation (EAE) est un outil de management qui permet de faire "
    "le bilan des réalisations, fixer les objectifs de l'année suivante et identifier les "
    "besoins en formation. Il doit être préparé par les deux parties pour être constructif.",

    "La chaîne de valeur de Porter décompose l'entreprise en activités primaires "
    "(logistique, production, commercialisation, services) et de soutien (infrastructure, RH, "
    "R&D, achats). L'analyse permet d'identifier où l'entreprise crée de la valeur et où "
    "elle peut réduire ses coûts.",

    "Le leadership situationnel de Hersey & Blanchard adapte le style de management "
    "au niveau de maturité du collaborateur. Quatre styles : Directif (faible maturité), "
    "Persuasif, Participatif, Délégatif (forte maturité). Le manager ajuste son comportement "
    "selon les compétences et la motivation de chacun.",
]


class Command(BaseCommand):
    help = "Crée des tentatives de quiz pour les étudiants (QCU/QCM auto-notés, TEXT en attente)"

    def add_arguments(self, parser):
        parser.add_argument('--students', type=int, default=8,
                            help='Nombre max d\'étudiants par quiz (défaut: 8)')
        parser.add_argument('--clear', action='store_true',
                            help='Supprimer les tentatives existantes avant de recréer')

    def handle(self, *args, **options):
        from apps.elearning.models import Quiz, Question, Choice, QuizAttempt, AttemptAnswer
        from apps.students.models import Student

        max_stu = options['students']

        if options['clear']:
            n = QuizAttempt.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f'  {n} tentatives supprimées.'))

        students = list(Student.objects.select_related('user').all())
        if not students:
            self.stdout.write(self.style.ERROR('Aucun étudiant trouvé.'))
            return

        quizzes = list(
            Quiz.objects.filter(is_published=True)
            .prefetch_related('questions__choices')
            .order_by('-created_at')[:15]
        )
        if not quizzes:
            self.stdout.write(self.style.ERROR('Aucun quiz publié trouvé. Lancez d\'abord seed_subjects_pdf.'))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n=== Seed Quiz Attempts — {len(quizzes)} quiz · {len(students)} étudiants ==='
        ))

        total_attempts = 0
        total_answers = 0

        for quiz in quizzes:
            questions = list(quiz.questions.all().prefetch_related('choices').order_by('order'))
            if not questions:
                self.stdout.write(self.style.WARNING(f'  ⚠ {quiz.title[:50]} : aucune question, ignoré.'))
                continue

            sample = random.sample(students, min(max_stu, len(students)))
            n_att = 0

            for student in sample:
                if QuizAttempt.objects.filter(quiz=quiz, student=student).exists():
                    continue

                # Date aléatoire dans les 60 derniers jours
                submitted_at = timezone.now() - timedelta(days=random.randint(1, 60),
                                                          hours=random.randint(0, 23))

                attempt = QuizAttempt(
                    quiz=quiz,
                    student=student,
                    submitted_at=submitted_at,
                )
                attempt.save()

                for q in questions:
                    self._create_answer(attempt, q)
                    total_answers += 1

                attempt.finalize()
                n_att += 1
                total_attempts += 1

            self.stdout.write(self.style.SUCCESS(
                f'  ✓ {quiz.title[:60]} → {n_att} tentatives'
            ))

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ {total_attempts} tentatives créées · {total_answers} réponses'
        ))

    def _create_answer(self, attempt, question):
        from apps.elearning.models import AttemptAnswer

        answer = AttemptAnswer(attempt=attempt, question=question)
        answer.save()

        q_type = question.question_type
        choices = list(question.choices.all())
        correct_choices = [c for c in choices if c.is_correct]
        wrong_choices = [c for c in choices if not c.is_correct]

        # 70 % de bonne réponse pour les types auto-notés
        is_right = random.random() < 0.70

        if q_type == 'QCU':
            if is_right and correct_choices:
                answer.selected_choices.set([random.choice(correct_choices)])
            elif wrong_choices:
                answer.selected_choices.set([random.choice(wrong_choices)])
            elif choices:
                answer.selected_choices.set([random.choice(choices)])

        elif q_type == 'QCM':
            if is_right and correct_choices:
                answer.selected_choices.set(correct_choices)
            else:
                # Sélection partielle ou mauvaise
                pool = wrong_choices or choices
                n = min(2, len(pool))
                answer.selected_choices.set(random.sample(pool, n))

        elif q_type == 'TRUEFALSE':
            if is_right and correct_choices:
                answer.selected_choices.set([correct_choices[0]])
            elif wrong_choices:
                answer.selected_choices.set([wrong_choices[0]])
            elif choices:
                answer.selected_choices.set([random.choice(choices)])

        elif q_type == 'TEXT':
            answer.text_response = random.choice(BUSINESS_TEXT_RESPONSES)
            answer.save()
            # TEXT sans text_answer de référence → is_correct = None (attente correction manuelle)
            if question.text_answer:
                answer.grade()
            # Sinon on laisse is_correct=None, points_earned=0
            answer.save()
            return  # On ne rappelle pas grade() ci-dessous

        elif q_type == 'NUMERIC':
            if question.numeric_answer is not None:
                base = float(question.numeric_answer)
                tolerance = float(question.numeric_tolerance or 0)
                if is_right:
                    val = base + random.uniform(-tolerance, tolerance)
                else:
                    val = base * random.uniform(1.2, 2.5)
                answer.numeric_response = Decimal(str(round(val, 4)))

        answer.save()
        answer.grade()
        answer.save()
