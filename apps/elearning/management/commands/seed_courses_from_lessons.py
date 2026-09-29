"""
seed_courses_from_lessons.py — Génère le catalogue "Cours" (Course / CourseSection /
CourseChapter / CourseLesson — la page "Gérer mes cours" / "Catalogue de formations")
à PARTIR des Chapter/Lesson déjà présents en base (le parcours pédagogique classique,
lié à Class+Subject — page "Leçons & Parcours").

Contrairement à seed_courses.py (contenu générique codé en dur type MOOC Python), ce
script est un miroir : il convertit chaque couple (Classe, Matière) qui a des
Chapter/Lesson en un Course autonome correspondant, avec la même hiérarchie de
contenu (une Section "Programme" -> les Chapter deviennent des CourseChapter -> les
Lesson deviennent des CourseLesson).

Usage:
    python manage.py seed_courses_from_lessons [--clear]
"""
from django.core.management.base import BaseCommand

LEVEL_MAP = {'L1': 'beginner', 'L2': 'intermediate', 'L3': 'advanced'}


class Command(BaseCommand):
    help = "Génère le catalogue Course/Section/Chapter/Lesson à partir des Chapter/Lesson existants"

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Supprime les Course existants avant de générer')

    def handle(self, *args, **options):
        from apps.elearning.models import (
            Chapter, Lesson, Course, CourseSection, CourseChapter, CourseLesson,
        )

        if options['clear']:
            n = Course.objects.count()
            Course.objects.all().delete()  # cascade -> sections/chapters/lessons
            print(f'  Supprime {n} Course existants (cascade sections/chapitres/lecons)')

        # Un Course par couple (class_obj, subject) qui a au moins une Lesson
        pairs = (
            Lesson.objects.filter(is_active=True)
            .values_list('class_obj_id', 'subject_id')
            .distinct()
        )

        created_courses = 0
        created_sections = 0
        created_chapters = 0
        created_lessons = 0
        skipped = 0

        for class_id, subject_id in pairs:
            lessons_qs = (
                Lesson.objects.filter(class_obj_id=class_id, subject_id=subject_id, is_active=True)
                .select_related('class_obj', 'subject', 'teacher__user', 'chapter')
                .order_by('chapter__order', 'order')
            )
            if not lessons_qs.exists():
                continue

            first = lessons_qs.first()
            class_obj = first.class_obj
            subject = first.subject
            site = class_obj.site
            instructor = first.teacher.user if first.teacher_id else None
            level_code = class_obj.level.code if class_obj.level_id else None
            course_level = LEVEL_MAP.get(level_code, 'all_levels')

            title = f'{subject.name} — {class_obj.name}'

            course, created = Course.objects.get_or_create(
                site=site, title=title,
                defaults=dict(
                    instructor=instructor,
                    subtitle=f'{subject.name} pour {class_obj.name}',
                    description=(
                        f"Cours complet de {subject.name} destiné aux étudiants de {class_obj.name}. "
                        f"Contenu structuré en chapitres et leçons couvrant le programme officiel de la matière."
                    ),
                    level=course_level, language='Français', status='published',
                    price=0, is_free=True, certificate_enabled=(level_code == 'L3'),
                    target_audience=f'Étudiants inscrits en {class_obj.name}',
                    requirements=['Assiduité aux séances', 'Accès à un ordinateur ou smartphone'],
                    what_you_will_learn=[
                        f'Maîtriser les fondamentaux de {subject.name}',
                        'Réaliser les exercices et évaluations associés',
                    ],
                ),
            )
            if not created:
                skipped += 1
                continue
            created_courses += 1

            section = CourseSection.objects.create(course=course, title='Programme', order=1)
            created_sections += 1

            # Chapitres explicites (Chapter) rattachés a ce couple classe/matiere
            chapters = Chapter.objects.filter(
                class_obj_id=class_id, subject_id=subject_id, is_active=True
            ).order_by('order')

            chapter_map = {}
            for ch in chapters:
                course_chapter = CourseChapter.objects.create(
                    section=section, title=ch.title,
                    description=ch.description or f'Chapitre : {ch.title}',
                    order=ch.order,
                )
                chapter_map[ch.id] = course_chapter
                created_chapters += 1

            # Lecons sans chapitre -> regroupees dans un chapitre "General"
            general_chapter = None

            for i, lesson in enumerate(lessons_qs):
                if lesson.chapter_id and lesson.chapter_id in chapter_map:
                    course_chapter = chapter_map[lesson.chapter_id]
                else:
                    if general_chapter is None:
                        general_chapter = CourseChapter.objects.create(
                            section=section, title='Général',
                            description='Leçons non rattachées à un chapitre spécifique',
                            order=len(chapter_map) + 1,
                        )
                        created_chapters += 1
                    course_chapter = general_chapter

                CourseLesson.objects.create(
                    chapter=course_chapter, title=lesson.title,
                    content_type='text', duration_seconds=lesson.min_duration_seconds or 600,
                    is_preview_free=(i == 0), download_allowed=False,
                    text_content=lesson.content or lesson.description or '',
                    order=lesson.order,
                )
                created_lessons += 1

        print(f'\n=== SEED COURS TERMINE ===')
        print(f'  Cours crees      : {created_courses}')
        print(f'  Cours ignores    : {skipped} (deja existants)')
        print(f'  Sections creees  : {created_sections}')
        print(f'  Chapitres crees  : {created_chapters}')
        print(f'  Lecons creees    : {created_lessons}')
        print(f'  Total Course en base : {Course.objects.count()}')
