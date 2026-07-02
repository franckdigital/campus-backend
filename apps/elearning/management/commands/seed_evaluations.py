"""
seed_evaluations.py — Seed complet d'évaluations (Quiz) de tous types sur les cours.

Usage: python manage.py seed_evaluations
Couvre: QCU, QCM, VRAI/FAUX, TEXT, NUMERIC — avec tentatives étudiants, scores, passages réussis/échoués
"""
import random
from django.core.management.base import BaseCommand
from django.utils import timezone

QUIZ_DATA = [
    {
        'title': 'Évaluation — Introduction à Python',
        'description': 'Testez vos connaissances sur les bases de Python.',
        'questions_count': 10, 'duration': 20, 'passing': 60,
        'questions': [
            {'type': 'MCQ',       'text': 'Quel opérateur est utilisé pour l\'exponentiation en Python ?', 'choices': ['**', '^', '^^', 'pow'], 'correct': [0]},
            {'type': 'MCQ',       'text': 'Quelle instruction permet de sortir d\'une boucle ?', 'choices': ['break', 'exit', 'stop', 'end'], 'correct': [0]},
            {'type': 'MULTI',     'text': 'Lesquels sont des types de données en Python ?', 'choices': ['int', 'float', 'str', 'char'], 'correct': [0, 1, 2]},
            {'type': 'TRUEFALSE', 'text': 'Python est un langage compilé.', 'correct': False},
            {'type': 'TRUEFALSE', 'text': 'Les listes Python sont mutables.', 'correct': True},
            {'type': 'MCQ',       'text': 'Quelle fonction affiche du texte en Python ?', 'choices': ['print()', 'echo()', 'write()', 'display()'], 'correct': [0]},
            {'type': 'TEXT',      'text': 'Donnez la syntaxe d\'une fonction en Python.', 'sample_answer': 'def nom_fonction(params): ...'},
            {'type': 'NUMERIC',   'text': 'Combien de types primitifs principaux y a-t-il en Python ?', 'answer': 4},
            {'type': 'MCQ',       'text': 'Quel est l\'indice du premier élément d\'une liste ?', 'choices': ['0', '1', '-1', 'None'], 'correct': [0]},
            {'type': 'MULTI',     'text': 'Lesquelles sont des structures de contrôle ?', 'choices': ['if', 'for', 'while', 'print'], 'correct': [0, 1, 2]},
        ]
    },
    {
        'title': 'Évaluation — Algorithmes et Structures de données',
        'description': 'Évaluation sur les algorithmes de tri et de recherche.',
        'questions_count': 8, 'duration': 25, 'passing': 50,
        'questions': [
            {'type': 'MCQ',       'text': 'Quelle est la complexité du tri à bulles dans le pire cas ?', 'choices': ['O(n²)', 'O(n log n)', 'O(n)', 'O(1)'], 'correct': [0]},
            {'type': 'MCQ',       'text': 'Quel algorithme de tri utilise la stratégie "diviser pour régner" ?', 'choices': ['Tri fusion', 'Tri à bulles', 'Tri sélection', 'Tri insertion'], 'correct': [0]},
            {'type': 'TRUEFALSE', 'text': 'La recherche binaire nécessite un tableau trié.', 'correct': True},
            {'type': 'MULTI',     'text': 'Lesquels sont des algorithmes de tri en O(n log n) ?', 'choices': ['Tri fusion', 'Tri rapide', 'Tri à bulles', 'Tri par tas'], 'correct': [0, 1, 3]},
            {'type': 'NUMERIC',   'text': 'Combien de comparaisons au maximum pour une recherche binaire sur 1024 éléments ?', 'answer': 10},
            {'type': 'TEXT',      'text': 'Expliquez le principe d\'une pile (stack).', 'sample_answer': 'LIFO - Last In First Out'},
            {'type': 'MCQ',       'text': 'Quelle structure de données utilise FIFO ?', 'choices': ['File (Queue)', 'Pile (Stack)', 'Arbre', 'Graphe'], 'correct': [0]},
            {'type': 'TRUEFALSE', 'text': 'Un arbre binaire peut avoir plus de 2 enfants par nœud.', 'correct': False},
        ]
    },
    {
        'title': 'Évaluation finale — Base de données SQL',
        'description': 'Évaluation complète sur SQL et les bases de données relationnelles.',
        'questions_count': 12, 'duration': 30, 'passing': 70,
        'questions': [
            {'type': 'MCQ',   'text': 'Quelle commande SQL crée une table ?', 'choices': ['CREATE TABLE', 'MAKE TABLE', 'NEW TABLE', 'BUILD TABLE'], 'correct': [0]},
            {'type': 'MCQ',   'text': 'Quelle clause filtre les résultats d\'une requête SELECT ?', 'choices': ['WHERE', 'FILTER', 'HAVING', 'LIMIT'], 'correct': [0]},
            {'type': 'MULTI', 'text': 'Lesquels sont des types de jointures SQL ?', 'choices': ['INNER JOIN', 'LEFT JOIN', 'CROSS JOIN', 'DIAGONAL JOIN'], 'correct': [0, 1, 2]},
            {'type': 'TRUEFALSE', 'text': 'PRIMARY KEY peut contenir des valeurs NULL.', 'correct': False},
            {'type': 'TRUEFALSE', 'text': 'Une clé étrangère référence la clé primaire d\'une autre table.', 'correct': True},
            {'type': 'MCQ',   'text': 'Quelle fonction SQL compte les lignes ?', 'choices': ['COUNT()', 'SUM()', 'TOTAL()', 'NB()'], 'correct': [0]},
            {'type': 'TEXT',  'text': 'Écrivez une requête pour sélectionner tous les étudiants.', 'sample_answer': 'SELECT * FROM etudiants;'},
            {'type': 'MCQ',   'text': 'Quelle commande supprime des lignes ?', 'choices': ['DELETE', 'REMOVE', 'DROP', 'ERASE'], 'correct': [0]},
            {'type': 'MULTI', 'text': 'Lesquelles sont des fonctions d\'agrégation ?', 'choices': ['AVG()', 'MAX()', 'MIN()', 'CONCAT()'], 'correct': [0, 1, 2]},
            {'type': 'NUMERIC','text': 'Combien de formes normales principales existent ?', 'answer': 3},
            {'type': 'MCQ',   'text': 'Quelle commande modifie la structure d\'une table ?', 'choices': ['ALTER TABLE', 'MODIFY TABLE', 'CHANGE TABLE', 'UPDATE TABLE'], 'correct': [0]},
            {'type': 'TRUEFALSE', 'text': 'GROUP BY est utilisé avant WHERE dans une requête.', 'correct': False},
        ]
    },
    {
        'title': 'Quiz rapide — Réseaux informatiques',
        'description': 'Vérification rapide des bases des réseaux.',
        'questions_count': 6, 'duration': 10, 'passing': 50,
        'questions': [
            {'type': 'MCQ',       'text': 'Sur quelle couche OSI fonctionne IP ?', 'choices': ['Couche 3 - Réseau', 'Couche 4 - Transport', 'Couche 2 - Liaison', 'Couche 1 - Physique'], 'correct': [0]},
            {'type': 'MCQ',       'text': 'Quel protocole traduit les noms de domaine en IP ?', 'choices': ['DNS', 'DHCP', 'HTTP', 'FTP'], 'correct': [0]},
            {'type': 'TRUEFALSE', 'text': 'TCP garantit la livraison des paquets.', 'correct': True},
            {'type': 'TRUEFALSE', 'text': 'UDP est plus fiable que TCP.', 'correct': False},
            {'type': 'NUMERIC',   'text': 'Combien de bits dans une adresse IPv4 ?', 'answer': 32},
            {'type': 'MULTI',     'text': 'Lesquels sont des protocoles de la couche application ?', 'choices': ['HTTP', 'FTP', 'SMTP', 'ARP'], 'correct': [0, 1, 2]},
        ]
    },
    {
        'title': 'Évaluation — Intelligence Artificielle',
        'description': 'Évaluation sur les concepts fondamentaux de l\'IA et du machine learning.',
        'questions_count': 10, 'duration': 20, 'passing': 60,
        'questions': [
            {'type': 'MCQ',       'text': 'Quel algorithme est utilisé pour la classification supervisée ?', 'choices': ['SVM', 'K-means', 'DBSCAN', 'PCA'], 'correct': [0]},
            {'type': 'MCQ',       'text': 'Qu\'est-ce que l\'overfitting ?', 'choices': ['Sur-apprentissage', 'Sous-apprentissage', 'Apprentissage optimal', 'Régularisation'], 'correct': [0]},
            {'type': 'TRUEFALSE', 'text': 'Le machine learning est un sous-domaine de l\'intelligence artificielle.', 'correct': True},
            {'type': 'MULTI',     'text': 'Lesquels sont des algorithmes de clustering ?', 'choices': ['K-means', 'DBSCAN', 'Random Forest', 'K-medoids'], 'correct': [0, 1, 3]},
            {'type': 'MCQ',       'text': 'Quelle métrique est utilisée pour évaluer un modèle de régression ?', 'choices': ['MSE', 'Accuracy', 'F1-score', 'AUC-ROC'], 'correct': [0]},
            {'type': 'TRUEFALSE', 'text': 'Un réseau de neurones profond nécessite toujours des GPU.', 'correct': False},
            {'type': 'TEXT',      'text': 'Expliquez la différence entre apprentissage supervisé et non supervisé.', 'sample_answer': 'Supervisé = données étiquetées, Non supervisé = pas d\'étiquettes'},
            {'type': 'NUMERIC',   'text': 'Combien de paramètres doit-on choisir pour K-means ?', 'answer': 1},
            {'type': 'MCQ',       'text': 'Quelle technique réduit la dimensionnalité ?', 'choices': ['PCA', 'SVM', 'KNN', 'Naive Bayes'], 'correct': [0]},
            {'type': 'MULTI',     'text': 'Lesquels sont des hyperparamètres d\'un réseau de neurones ?', 'choices': ['Learning rate', 'Nombre de couches', 'Batch size', 'Poids synaptiques'], 'correct': [0, 1, 2]},
        ]
    },
]


class Command(BaseCommand):
    help = 'Seed évaluations (quiz) de tous types avec tentatives étudiants'

    def handle(self, *args, **options):
        from apps.elearning.models import Quiz, Question, Choice, QuizAttempt, AttemptAnswer
        from apps.students.models import Student
        from apps.academic.models import Class as ClassModel

        self.stdout.write(self.style.MIGRATE_HEADING('=== Seed Évaluations ==='))

        classes = list(ClassModel.objects.filter(is_active=True)[:3])
        if not classes:
            self.stdout.write(self.style.ERROR('Aucune classe trouvée. Exécutez d\'abord seed_full.'))
            return

        all_students = list(Student.objects.select_related('user').all()[:20])
        created_quizzes = []

        for i, qdata in enumerate(QUIZ_DATA):
            cls = classes[i % len(classes)]
            subjects = list(cls.subjects.all())
            subject = subjects[i % len(subjects)] if subjects else None

            quiz = Quiz.objects.create(
                title=qdata['title'],
                description=qdata['description'],
                class_obj=cls,
                subject=subject,
                duration_minutes=qdata['duration'],
                passing_score=qdata['passing'],
                total_points=100,
                shuffle_questions=True,
                shuffle_choices=False,
                is_published=True,
                is_active=True,
            )

            questions_created = []
            for j, q in enumerate(qdata['questions']):
                qtype = q['type']
                if qtype == 'TRUEFALSE':
                    question = Question.objects.create(
                        quiz=quiz, order=j + 1,
                        question_type='TRUEFALSE',
                        text=q['text'],
                        points=10,
                        true_false_answer=q['correct'],
                    )
                elif qtype == 'TEXT':
                    question = Question.objects.create(
                        quiz=quiz, order=j + 1,
                        question_type='TEXT',
                        text=q['text'],
                        points=10,
                        sample_answer=q.get('sample_answer', ''),
                    )
                elif qtype == 'NUMERIC':
                    question = Question.objects.create(
                        quiz=quiz, order=j + 1,
                        question_type='NUMERIC',
                        text=q['text'],
                        points=10,
                        numeric_answer=q['answer'],
                        numeric_tolerance=0.5,
                    )
                else:
                    is_multi = qtype == 'MULTI'
                    question = Question.objects.create(
                        quiz=quiz, order=j + 1,
                        question_type='MCQ',
                        text=q['text'],
                        points=10,
                        allow_multiple=is_multi,
                    )
                    for k, choice_text in enumerate(q.get('choices', [])):
                        Choice.objects.create(
                            question=question,
                            text=choice_text,
                            is_correct=(k in q.get('correct', [])),
                            order=k,
                        )
                questions_created.append(question)

            created_quizzes.append((quiz, questions_created))
            self.stdout.write(f'  ✓ Quiz créé : {quiz.title} ({len(questions_created)} questions)')

        # Simuler des tentatives d'étudiants
        self.stdout.write('\nSimulation des tentatives étudiants...')
        for quiz, questions in created_quizzes:
            students_sample = random.sample(all_students, min(8, len(all_students)))
            for student in students_sample:
                score = random.randint(20, 100)
                status = 'COMPLETED'
                attempt = QuizAttempt.objects.create(
                    quiz=quiz,
                    student=student,
                    status=status,
                    score=score,
                    max_score=100,
                    started_at=timezone.now() - timezone.timedelta(hours=random.randint(1, 72)),
                    completed_at=timezone.now() - timezone.timedelta(hours=random.randint(0, 1)),
                )
                # Réponses simulées
                for q in questions[:5]:
                    if q.question_type in ('MCQ',):
                        correct_choice = q.choices.filter(is_correct=True).first()
                        wrong_choice = q.choices.filter(is_correct=False).first()
                        chosen = correct_choice if random.random() > 0.4 else wrong_choice
                        if chosen:
                            AttemptAnswer.objects.create(
                                attempt=attempt, question=q,
                                selected_choices=[str(chosen.id)],
                                is_correct=(chosen == correct_choice),
                                points_earned=q.points if chosen == correct_choice else 0,
                            )

        self.stdout.write(self.style.SUCCESS(f'\n✅ {len(created_quizzes)} évaluations créées avec tentatives.'))
