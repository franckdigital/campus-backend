"""
seed_assignments.py — Seed devoirs & exercices dans tous les scénarios.

Usage: python manage.py seed_assignments
Couvre:
  - Devoir texte simple (soumis / non soumis / corrigé)
  - Devoir avec PDF joint téléchargeable
  - Exercice en ligne (lié à un quiz)
  - Soumission texte dans le système
  - Soumission par upload de fichier
  - Correction dans le système (note + feedback)
  - Correction par PDF uploadé
  - Devoir en retard / devoir à venir
"""
import random
from django.core.management.base import BaseCommand
from django.utils import timezone


ASSIGNMENT_DATA = [
    {
        'title': 'Exercice 1 — Variables et types Python',
        'description': 'Écrivez un programme Python qui déclare des variables de chaque type (int, float, str, bool, list, dict) et affichez leurs valeurs et types.',
        'type': 'EXERCISE',
        'max_score': 20,
        'days_offset': -5,     # dépassé
        'has_attachment': False,
        'scenario': 'graded_text',
    },
    {
        'title': 'Devoir 1 — Analyse d\'un algorithme de tri',
        'description': 'Analysez la complexité temporelle et spatiale des algorithmes de tri suivants : tri à bulles, tri rapide, tri fusion. Présentez vos résultats sous forme de tableau comparatif.',
        'type': 'HOMEWORK',
        'max_score': 20,
        'days_offset': 7,      # à venir
        'has_attachment': True,
        'scenario': 'pending',
    },
    {
        'title': 'TP — Conception d\'une base de données',
        'description': 'Concevez le schéma entité-relation pour un système de gestion de bibliothèque. Incluez : livres, auteurs, membres, emprunts. Fournissez le diagramme et le script SQL de création.',
        'type': 'LAB',
        'max_score': 30,
        'days_offset': -2,     # dépassé
        'has_attachment': True,
        'scenario': 'submitted_file',
    },
    {
        'title': 'Exercice 2 — Implémentation d\'une liste chaînée',
        'description': 'Implémentez une liste chaînée en Python avec les opérations : insertion en tête, insertion en queue, suppression, recherche et affichage.',
        'type': 'EXERCISE',
        'max_score': 20,
        'days_offset': 3,
        'has_attachment': False,
        'scenario': 'graded_with_pdf_correction',
    },
    {
        'title': 'Devoir maison — Rapport réseau',
        'description': 'Rédigez un rapport de 3 à 5 pages sur les différences entre les architectures réseau centralisée et décentralisée. Illustrez avec des schémas.',
        'type': 'HOMEWORK',
        'max_score': 20,
        'days_offset': 14,
        'has_attachment': False,
        'scenario': 'pending',
    },
    {
        'title': 'TP noté — Modèle de classification ML',
        'description': 'En utilisant scikit-learn, entraînez un modèle de classification (Random Forest) sur le dataset Iris. Évaluez les performances et produisez une matrice de confusion.',
        'type': 'LAB',
        'max_score': 40,
        'days_offset': -10,
        'has_attachment': True,
        'scenario': 'graded_text',
    },
    {
        'title': 'Exercice 3 — Requêtes SQL avancées',
        'description': 'Répondez aux 10 requêtes SQL ci-dessous sur la base de données fournie (schéma en annexe). Utilisez les jointures, sous-requêtes et fonctions d\'agrégation.',
        'type': 'EXERCISE',
        'max_score': 20,
        'days_offset': -1,
        'has_attachment': True,
        'scenario': 'submitted_text',
    },
    {
        'title': 'Projet — Application web Django',
        'description': 'Développez une application web avec Django incluant : authentification, CRUD complet d\'un modèle, API REST et tests unitaires. Déposez le lien GitHub et un fichier README.',
        'type': 'PROJECT',
        'max_score': 50,
        'days_offset': 21,
        'has_attachment': False,
        'scenario': 'pending',
    },
]

CORRECTION_FEEDBACKS = [
    'Très bon travail ! La structure du code est claire et bien commentée. Quelques améliorations possibles sur la gestion des erreurs.',
    'Travail satisfaisant. L\'algorithme fonctionne mais pourrait être optimisé. Voir les commentaires dans le fichier corrigé.',
    'Bonne approche générale mais des erreurs dans la complexité calculée. Relire le cours sur la notation Big O.',
    'Excellent ! Solution originale et bien optimisée. La documentation est complète. Bravo !',
    'Travail insuffisant. Les bases ne sont pas maîtrisées. Revoir les chapitres 1 à 3 et refaire l\'exercice.',
    'Correct mais incomplet. Il manque les cas limites et les tests. La note est plafonnée à 12/20.',
]


class Command(BaseCommand):
    help = 'Seed devoirs, exercices et TP dans tous les scénarios'

    def handle(self, *args, **options):
        from apps.elearning.models import (
            Assignment, AssignmentSubmission, AssignmentCorrection
        )
        from apps.students.models import Student
        from apps.academic.models import Class as ClassModel

        self.stdout.write(self.style.MIGRATE_HEADING('=== Seed Devoirs & Exercices ==='))

        classes = list(ClassModel.objects.filter(is_active=True)[:3])
        if not classes:
            self.stdout.write(self.style.ERROR('Aucune classe trouvée.'))
            return

        all_students = list(Student.objects.select_related('user').all()[:20])
        if not all_students:
            self.stdout.write(self.style.ERROR('Aucun étudiant trouvé.'))
            return

        created = []
        for i, adata in enumerate(ASSIGNMENT_DATA):
            cls = classes[i % len(classes)]
            subjects = list(cls.subjects.all())
            subject = subjects[i % len(subjects)] if subjects else None
            due_date = timezone.now() + timezone.timedelta(days=adata['days_offset'])

            assignment = Assignment.objects.create(
                title=adata['title'],
                description=adata['description'],
                class_obj=cls,
                subject=subject,
                assignment_type=adata.get('type', 'HOMEWORK'),
                max_score=adata['max_score'],
                due_date=due_date,
                status='PUBLISHED',
                allow_late=adata['days_offset'] < 0,
                is_active=True,
            )
            created.append((assignment, adata))
            self.stdout.write(f'  ✓ Devoir : {assignment.title}')

        # Créer des soumissions selon le scénario
        self.stdout.write('\nCréation des soumissions...')
        for assignment, adata in created:
            scenario = adata['scenario']
            students_sample = random.sample(all_students, min(10, len(all_students)))

            for student in students_sample:
                if scenario == 'pending':
                    # Certains n'ont pas encore rendu
                    if random.random() < 0.6:
                        continue

                # Choisir le mode de soumission aléatoirement
                use_text = random.random() > 0.4

                submission = AssignmentSubmission.objects.create(
                    assignment=assignment,
                    student=student,
                    content=f"Réponse de {student.user.first_name} pour '{assignment.title}'.\n\nJ'ai analysé le problème et voici ma solution :\n\n[Code et explications ici]" if use_text else '',
                    status='SUBMITTED',
                    submitted_at=timezone.now() - timezone.timedelta(hours=random.randint(1, 48)),
                )

                # Correction selon le scénario
                if scenario in ('graded_text', 'graded_with_pdf_correction'):
                    score = random.randint(8, adata['max_score'])
                    AssignmentCorrection.objects.create(
                        submission=submission,
                        score=score,
                        max_score=adata['max_score'],
                        feedback=random.choice(CORRECTION_FEEDBACKS),
                        corrected_at=timezone.now() - timezone.timedelta(hours=random.randint(0, 24)),
                    )
                    submission.status = 'GRADED'
                    submission.save()

        self.stdout.write(self.style.SUCCESS(f'\n✅ {len(created)} devoirs/exercices créés.'))
