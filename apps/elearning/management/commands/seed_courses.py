"""
seed_courses.py — Peuple les cours autonomes (Course, Section, Chapter, Lesson).

Usage:
    python manage.py seed_courses
    python manage.py seed_courses --clear   # supprime les cours existants d'abord

Pré-requis : avoir déjà exécuté `python manage.py seed_full` (Sites, Classes,
Matières, Utilisateurs doivent exister).
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

COURSES_DATA = [
    {
        'title': 'Introduction à la Programmation Python',
        'subtitle': 'Apprenez les bases de Python de zéro',
        'description': (
            'Ce cours complet vous guidera à travers les fondamentaux de Python : '
            'variables, boucles, fonctions, classes et bibliothèques essentielles. '
            'Idéal pour débutants souhaitant entrer dans le monde de la programmation.'
        ),
        'level': 'beginner',
        'language': 'Français',
        'status': 'published',
        'is_free': True,
        'certificate_enabled': True,
        'target_audience': 'Débutants en informatique, étudiants en sciences',
        'sections': [
            {
                'title': 'Fondamentaux de Python',
                'chapters': [
                    {
                        'title': 'Installation et configuration',
                        'lessons': [
                            ('Installer Python sur Windows/Mac/Linux', 'video', 480),
                            ('Configurer VS Code pour Python', 'video', 360),
                            ('Votre premier programme "Hello World"', 'text', 120),
                        ],
                    },
                    {
                        'title': 'Variables et types de données',
                        'lessons': [
                            ('Les types primitifs : int, float, str, bool', 'video', 600),
                            ('Les collections : list, tuple, dict, set', 'video', 720),
                            ('Exercice : Manipuler des variables', 'text', 180),
                        ],
                    },
                ],
            },
            {
                'title': 'Structures de contrôle',
                'chapters': [
                    {
                        'title': 'Conditions et boucles',
                        'lessons': [
                            ('if / elif / else', 'video', 540),
                            ('Boucle for et while', 'video', 600),
                            ('Compréhensions de liste', 'video', 420),
                        ],
                    },
                ],
            },
            {
                'title': 'Fonctions et modules',
                'chapters': [
                    {
                        'title': 'Définir et utiliser des fonctions',
                        'lessons': [
                            ('Définir une fonction avec def', 'video', 480),
                            ('Arguments positionnels et nommés', 'video', 420),
                            ('Fonctions lambda', 'video', 300),
                            ('Importer des modules', 'video', 360),
                        ],
                    },
                ],
            },
        ],
    },
    {
        'title': 'Développement Web avec Django',
        'subtitle': 'Créez des APIs REST robustes avec Django & DRF',
        'description': (
            'Maîtrisez le framework Django pour créer des applications web modernes. '
            'De la configuration initiale aux APIs RESTful avec Django REST Framework, '
            'en passant par l\'authentification JWT et la gestion des permissions.'
        ),
        'level': 'intermediate',
        'language': 'Français',
        'status': 'published',
        'is_free': False,
        'price': 15000,
        'certificate_enabled': True,
        'target_audience': 'Développeurs Python ayant des bases, étudiants en informatique',
        'sections': [
            {
                'title': 'Mise en place du projet',
                'chapters': [
                    {
                        'title': 'Installation et structure Django',
                        'lessons': [
                            ('Créer un projet Django', 'video', 540),
                            ('Architecture MTV : Models, Templates, Views', 'video', 600),
                            ('Configuration de la base de données', 'video', 480),
                        ],
                    },
                ],
            },
            {
                'title': 'Django REST Framework',
                'chapters': [
                    {
                        'title': 'Serializers et ViewSets',
                        'lessons': [
                            ('Créer des serializers', 'video', 720),
                            ('ViewSets et Routers', 'video', 660),
                            ('Permissions et authentification', 'video', 600),
                            ('Filtres, recherche et pagination', 'video', 540),
                        ],
                    },
                    {
                        'title': 'Authentification JWT',
                        'lessons': [
                            ('Configurer SimpleJWT', 'video', 480),
                            ('Refresh tokens et sécurité', 'video', 420),
                        ],
                    },
                ],
            },
            {
                'title': 'Déploiement',
                'chapters': [
                    {
                        'title': 'Mise en production',
                        'lessons': [
                            ('Préparer le projet pour la production', 'video', 600),
                            ('Déployer sur un VPS Linux', 'video', 900),
                            ('Configurer Nginx + Gunicorn', 'video', 720),
                        ],
                    },
                ],
            },
        ],
    },
    {
        'title': 'React.js — De Zéro à Expert',
        'subtitle': 'Construisez des interfaces modernes avec React',
        'description': (
            'Apprenez React de façon progressive : composants, hooks, état global, '
            'routing, et communication avec des APIs. Ce cours couvre React 18 avec '
            'les dernières bonnes pratiques et patterns modernes.'
        ),
        'level': 'intermediate',
        'language': 'Français',
        'status': 'published',
        'is_free': False,
        'price': 12000,
        'certificate_enabled': True,
        'target_audience': 'Développeurs JavaScript, étudiants en développement web',
        'sections': [
            {
                'title': 'Les bases de React',
                'chapters': [
                    {
                        'title': 'Composants et JSX',
                        'lessons': [
                            ('Qu\'est-ce que React ?', 'video', 360),
                            ('Créer votre premier composant', 'video', 540),
                            ('Props et communication entre composants', 'video', 600),
                            ('Listes et clés (key)', 'video', 420),
                        ],
                    },
                ],
            },
            {
                'title': 'Hooks et gestion d\'état',
                'chapters': [
                    {
                        'title': 'Les hooks essentiels',
                        'lessons': [
                            ('useState : gérer l\'état local', 'video', 540),
                            ('useEffect : effets de bord', 'video', 600),
                            ('useCallback et useMemo', 'video', 480),
                            ('useContext : état global simple', 'video', 420),
                        ],
                    },
                ],
            },
            {
                'title': 'Projet final',
                'chapters': [
                    {
                        'title': 'Construire une application complète',
                        'lessons': [
                            ('Conception de l\'architecture', 'text', 300),
                            ('Intégration avec une API REST', 'video', 720),
                            ('Routing avec React Router', 'video', 540),
                            ('Déploiement et optimisation', 'video', 600),
                        ],
                    },
                ],
            },
        ],
    },
    {
        'title': 'Algorithmique et Structures de Données',
        'subtitle': 'Les fondements de l\'informatique moderne',
        'description': (
            'Ce cours couvre les algorithmes et structures de données essentiels : '
            'tri, recherche, arbres, graphes, complexité algorithmique. '
            'Préparation aux entretiens techniques et aux concours informatiques.'
        ),
        'level': 'intermediate',
        'language': 'Français',
        'status': 'published',
        'is_free': True,
        'certificate_enabled': False,
        'target_audience': 'Étudiants en informatique, candidats aux entretiens tech',
        'sections': [
            {
                'title': 'Complexité algorithmique',
                'chapters': [
                    {
                        'title': 'Notation Big-O',
                        'lessons': [
                            ('Introduction à la complexité', 'video', 600),
                            ('O(1), O(log n), O(n), O(n²)', 'video', 720),
                            ('Analyse d\'algorithmes courants', 'video', 540),
                        ],
                    },
                ],
            },
            {
                'title': 'Algorithmes de tri',
                'chapters': [
                    {
                        'title': 'Algorithmes classiques',
                        'lessons': [
                            ('Tri par sélection et insertion', 'video', 540),
                            ('Tri fusion (Merge Sort)', 'video', 660),
                            ('Tri rapide (Quick Sort)', 'video', 600),
                            ('Exercices corrigés', 'pdf', 0),
                        ],
                    },
                ],
            },
            {
                'title': 'Structures de données',
                'chapters': [
                    {
                        'title': 'Listes et piles',
                        'lessons': [
                            ('Listes chaînées', 'video', 600),
                            ('Piles et files', 'video', 540),
                        ],
                    },
                    {
                        'title': 'Arbres et graphes',
                        'lessons': [
                            ('Arbres binaires de recherche', 'video', 720),
                            ('Parcours en largeur et profondeur', 'video', 660),
                            ('Algorithme de Dijkstra', 'video', 600),
                        ],
                    },
                ],
            },
        ],
    },
    {
        'title': 'Bases de Données et SQL',
        'subtitle': 'Maîtrisez la gestion des données relationnelles',
        'description': (
            'Du modèle entité-relation aux requêtes SQL avancées, ce cours couvre '
            'tout ce que vous devez savoir sur les bases de données relationnelles. '
            'Pratique avec PostgreSQL et MySQL.'
        ),
        'level': 'beginner',
        'language': 'Français',
        'status': 'published',
        'is_free': True,
        'certificate_enabled': False,
        'target_audience': 'Étudiants en informatique, développeurs débutants',
        'sections': [
            {
                'title': 'Modélisation',
                'chapters': [
                    {
                        'title': 'Modèle entité-relation',
                        'lessons': [
                            ('Entités, attributs et relations', 'video', 600),
                            ('Cardinalités et associations', 'video', 540),
                            ('Du MCD au MLD', 'video', 480),
                        ],
                    },
                ],
            },
            {
                'title': 'SQL Fondamentaux',
                'chapters': [
                    {
                        'title': 'Requêtes de base',
                        'lessons': [
                            ('SELECT, FROM, WHERE', 'video', 540),
                            ('JOIN : inner, left, right, full', 'video', 660),
                            ('GROUP BY, HAVING, ORDER BY', 'video', 540),
                            ('INSERT, UPDATE, DELETE', 'video', 480),
                        ],
                    },
                ],
            },
            {
                'title': 'SQL Avancé',
                'chapters': [
                    {
                        'title': 'Fonctions et sous-requêtes',
                        'lessons': [
                            ('Fonctions d\'agrégation', 'video', 480),
                            ('Sous-requêtes et CTE', 'video', 600),
                            ('Transactions et ACID', 'video', 420),
                            ('Index et optimisation', 'video', 540),
                        ],
                    },
                ],
            },
        ],
    },
]


class Command(BaseCommand):
    help = 'Peuple les cours autonomes avec sections, chapitres et leçons'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Supprime les cours existants avant de seeder')

    def handle(self, *args, **options):
        from apps.elearning.models import Course, CourseSection, CourseChapter, CourseLesson

        if options['clear']:
            count = Course.objects.count()
            Course.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'  {count} cours supprimés.'))

        # Chercher un instructeur (admin ou premier staff)
        instructor = (
            User.objects.filter(is_superuser=True).first()
            or User.objects.filter(is_staff=True).first()
            or User.objects.first()
        )
        if not instructor:
            self.stdout.write(self.style.ERROR('Aucun utilisateur trouvé. Créez un superuser d\'abord.'))
            return

        self.stdout.write(f'Instructeur : {instructor.email}')

        created_courses = 0
        created_sections = 0
        created_chapters = 0
        created_lessons = 0

        for course_data in COURSES_DATA:
            sections_data = course_data.pop('sections', [])
            course, created = Course.objects.get_or_create(
                title=course_data['title'],
                defaults={
                    **course_data,
                    'instructor': instructor,
                },
            )
            if created:
                created_courses += 1
                self.stdout.write(f'  ✓ Cours : {course.title}')
            else:
                self.stdout.write(f'  ~ Existe déjà : {course.title}')
                course_data['sections'] = sections_data  # restore for next iteration
                continue

            # Restore sections for iteration
            course_data['sections'] = sections_data

            for sec_order, sec_data in enumerate(sections_data):
                chapters_data = sec_data.pop('chapters', [])
                section = CourseSection.objects.create(
                    course=course,
                    title=sec_data['title'],
                    order=sec_order,
                )
                created_sections += 1

                for ch_order, ch_data in enumerate(chapters_data):
                    lessons_data = ch_data.pop('lessons', [])
                    chapter = CourseChapter.objects.create(
                        section=section,
                        title=ch_data['title'],
                        order=ch_order,
                    )
                    created_chapters += 1

                    for les_order, (les_title, les_type, les_dur) in enumerate(lessons_data):
                        CourseLesson.objects.create(
                            chapter=chapter,
                            title=les_title,
                            content_type=les_type,
                            duration_seconds=les_dur,
                            order=les_order,
                            is_preview_free=(les_order == 0),  # 1ère leçon toujours en aperçu
                        )
                        created_lessons += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Seed terminé : {created_courses} cours, {created_sections} sections, '
            f'{created_chapters} chapitres, {created_lessons} leçons créés.'
        ))
