from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounts.models import User
from apps.academic.models import (
    TeacherProfile, Class, Subject, ClassSubjectTeacher, Session, Room
)
import uuid
from datetime import date, time


SITE_ID = uuid.UUID('8a11cf10-0206-4e21-9fb7-67cd29e34358')

CLASS_M1 = uuid.UUID('03e7f5ab-1e5b-49c4-96be-6e95c6ae8316')
CLASS_M2 = uuid.UUID('67e92e89-d874-46a6-a4df-fcc2b30d2ad5')

SUBJ_ALGO    = uuid.UUID('7e4555d7-8773-44af-9892-bdad05ef21ea')
SUBJ_ANGLAIS = uuid.UUID('5d424849-c9e6-4e25-a776-08e1ad6565d7')
SUBJ_BD      = uuid.UUID('03814e89-76a3-49b7-ae08-6b79ba225ffa')
SUBJ_JAVA    = uuid.UUID('05bea411-81e7-42c0-898e-3c478f9e7db3')
SUBJ_PYTHON  = uuid.UUID('de62b7df-2481-4771-8c80-13a31b03e335')
SUBJ_MATHS   = uuid.UUID('27ba6ecc-c5ae-4262-8be4-5a60daf0f2c8')
SUBJ_RESEAUX = uuid.UUID('a9a79978-c220-4591-8918-7b2aa21d7cd8')

TEACHERS = [
    {
        'first_name': 'Kouadio',
        'last_name': 'MENSAH',
        'email': 'k.mensah@campus.ci',
        'phone': '+22507112233',
        'employee_id': 'EMP-001',
        'specialization': 'Informatique & Algorithmes',
        'qualification': 'Doctorat en Informatique',
        'contract_type': 'PERMANENT',
        'hourly_rate': 12000,
        'assignments': [
            (CLASS_M1, SUBJ_ALGO),
            (CLASS_M2, SUBJ_ALGO),
            (CLASS_M2, SUBJ_PYTHON),
        ],
        'sessions': [
            {'class_id': CLASS_M1, 'subject_id': SUBJ_ALGO, 'day': 1, 'start': time(8,0), 'end': time(10,0)},
            {'class_id': CLASS_M2, 'subject_id': SUBJ_ALGO, 'day': 3, 'start': time(10,0), 'end': time(12,0)},
            {'class_id': CLASS_M2, 'subject_id': SUBJ_PYTHON, 'day': 5, 'start': time(14,0), 'end': time(16,0)},
        ],
    },
    {
        'first_name': 'Aissatou',
        'last_name': 'DIABATE',
        'email': 'a.diabate@campus.ci',
        'phone': '+22507445566',
        'employee_id': 'EMP-002',
        'specialization': 'Bases de donnees & Reseaux',
        'qualification': 'Master en Systemes Distribues',
        'contract_type': 'PERMANENT',
        'hourly_rate': 10000,
        'assignments': [
            (CLASS_M1, SUBJ_BD),
            (CLASS_M2, SUBJ_BD),
            (CLASS_M1, SUBJ_RESEAUX),
        ],
        'sessions': [
            {'class_id': CLASS_M1, 'subject_id': SUBJ_BD, 'day': 2, 'start': time(8,0), 'end': time(10,0)},
            {'class_id': CLASS_M2, 'subject_id': SUBJ_BD, 'day': 4, 'start': time(10,0), 'end': time(12,0)},
            {'class_id': CLASS_M1, 'subject_id': SUBJ_RESEAUX, 'day': 4, 'start': time(14,0), 'end': time(16,0)},
        ],
    },
    {
        'first_name': 'Thierry',
        'last_name': 'KOUAME',
        'email': 't.kouame@campus.ci',
        'phone': '+22507778899',
        'employee_id': 'EMP-003',
        'specialization': 'Developpement Java & Web',
        'qualification': 'Ingenieur en Genie Logiciel',
        'contract_type': 'CONTRACT',
        'hourly_rate': 8000,
        'assignments': [
            (CLASS_M1, SUBJ_JAVA),
            (CLASS_M2, SUBJ_JAVA),
        ],
        'sessions': [
            {'class_id': CLASS_M1, 'subject_id': SUBJ_JAVA, 'day': 1, 'start': time(10,0), 'end': time(12,0)},
            {'class_id': CLASS_M2, 'subject_id': SUBJ_JAVA, 'day': 3, 'start': time(8,0), 'end': time(10,0)},
        ],
    },
    {
        'first_name': 'Marie-Claire',
        'last_name': 'BROU',
        'email': 'm.brou@campus.ci',
        'phone': '+22507001122',
        'employee_id': 'EMP-004',
        'specialization': 'Mathematiques & Anglais',
        'qualification': 'CAPES Mathematiques',
        'contract_type': 'VISITING',
        'hourly_rate': 6000,
        'assignments': [
            (CLASS_M1, SUBJ_MATHS),
            (CLASS_M2, SUBJ_MATHS),
            (CLASS_M1, SUBJ_ANGLAIS),
            (CLASS_M2, SUBJ_ANGLAIS),
        ],
        'sessions': [
            {'class_id': CLASS_M1, 'subject_id': SUBJ_MATHS, 'day': 2, 'start': time(10,0), 'end': time(12,0)},
            {'class_id': CLASS_M2, 'subject_id': SUBJ_MATHS, 'day': 5, 'start': time(8,0), 'end': time(10,0)},
            {'class_id': CLASS_M1, 'subject_id': SUBJ_ANGLAIS, 'day': 5, 'start': time(10,0), 'end': time(12,0)},
            {'class_id': CLASS_M2, 'subject_id': SUBJ_ANGLAIS, 'day': 1, 'start': time(14,0), 'end': time(16,0)},
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed demo teacher profiles with assignments and sessions'

    @transaction.atomic
    def handle(self, *args, **options):
        Session.objects.filter(teacher__isnull=False).delete()
        ClassSubjectTeacher.objects.all().delete()
        TeacherProfile.objects.all().delete()
        User.objects.filter(user_type='TEACHER').delete()
        self.stdout.write('Cleared existing teacher data')

        class_m1 = Class.objects.get(id=CLASS_M1)
        class_m2 = Class.objects.get(id=CLASS_M2)
        class_map = {CLASS_M1: class_m1, CLASS_M2: class_m2}

        subject_map = {s.id: s for s in Subject.objects.all()}

        for data in TEACHERS:
            user = User.objects.create_user(
                email=data['email'],
                password='campus2025',
                first_name=data['first_name'],
                last_name=data['last_name'],
                phone=data['phone'],
                user_type='TEACHER',
                site_id=SITE_ID,
                is_active=True,
            )

            profile = TeacherProfile.objects.create(
                user=user,
                employee_id=data['employee_id'],
                specialization=data['specialization'],
                qualification=data['qualification'],
                contract_type=data['contract_type'],
                hire_date=date(2022, 9, 1),
                hourly_rate=data['hourly_rate'],
            )

            cst_map = {}
            for class_id, subject_id in data['assignments']:
                cst = ClassSubjectTeacher.objects.create(
                    class_obj=class_map[class_id],
                    subject=subject_map[subject_id],
                    teacher=profile,
                )
                cst_map[(class_id, subject_id)] = cst

            for s in data['sessions']:
                Session.objects.create(
                    class_obj=class_map[s['class_id']],
                    subject=subject_map[s['subject_id']],
                    teacher=profile,
                    day_of_week=s['day'],
                    start_time=s['start'],
                    end_time=s['end'],
                )

            self.stdout.write(
                f'  Created: {user.first_name} {user.last_name} '
                f'({data["contract_type"]}) — '
                f'{len(data["assignments"])} affectations, '
                f'{len(data["sessions"])} seances'
            )

        self.stdout.write(self.style.SUCCESS(
            f'Done: {len(TEACHERS)} enseignants seeded'
        ))
