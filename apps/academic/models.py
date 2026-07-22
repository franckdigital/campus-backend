from django.db import models
from django.conf import settings
from apps.core.models import BaseModel, Site, AcademicYear
from apps.students.models import Student
import uuid


class Program(BaseModel):
    """Program/Filière model."""
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    duration_years = models.PositiveIntegerField(default=3)
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name='programs'
    )

    class Meta:
        db_table = 'programs'
        verbose_name = 'Filière'
        verbose_name_plural = 'Filières'
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Level(BaseModel):
    """Level/Niveau model."""
    # A Level always belongs to exactly one Program/filière (e.g. "Licence 3
    # Marketing Management" vs "Licence 3 Droit" are two distinct Level rows)
    # — cycle is a cross-filière grouping ("every L3, whichever filière") used
    # by FeeConfiguration to configure one barème for a whole promotion year
    # instead of one row per filière. Kept in sync with the duplicated
    # CYCLE_CHOICES on finance.FeeConfiguration (see that model's comment).
    CYCLE_CHOICES = [
        ('L1', 'Licence 1'), ('L2', 'Licence 2'), ('L3', 'Licence 3'),
        ('BTS1', 'BTS 1'), ('BTS2', 'BTS 2'),
        ('DUT1', 'DUT 1'), ('DUT2', 'DUT 2'),
        ('M1', 'Master 1'), ('M2', 'Master 2'),
    ]
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    order = models.PositiveIntegerField(default=1)
    cycle = models.CharField(
        max_length=10, choices=CYCLE_CHOICES, null=True, blank=True,
        verbose_name="Cycle",
        help_text="Regroupement transversal (ex: Licence 3) utilisé pour configurer un barème valable pour toutes les filières de ce cycle."
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='levels'
    )

    class Meta:
        db_table = 'levels'
        verbose_name = 'Niveau'
        verbose_name_plural = 'Niveaux'
        ordering = ['program', 'order']
        unique_together = ['program', 'code']

    def __str__(self):
        return f"{self.program.code} - {self.name}"


class Class(BaseModel):
    """Class model."""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    level = models.ForeignKey(
        Level,
        on_delete=models.CASCADE,
        related_name='classes'
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name='classes'
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name='classes'
    )
    max_students = models.PositiveIntegerField(default=50)
    main_teacher = models.ForeignKey(
        'TeacherProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='main_classes'
    )

    class Meta:
        db_table = 'classes'
        verbose_name = 'Classe'
        verbose_name_plural = 'Classes'
        ordering = ['level', 'name']
        unique_together = ['code', 'academic_year', 'site']

    def __str__(self):
        return f"{self.code} - {self.name} ({self.academic_year.code})"


class Subject(BaseModel):
    """Subject/Matière model."""
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    coefficient = models.DecimalField(max_digits=4, decimal_places=2, default=1.00)
    hours_per_week = models.DecimalField(max_digits=4, decimal_places=2, default=2.00)

    class Meta:
        db_table = 'subjects'
        verbose_name = 'Matière'
        verbose_name_plural = 'Matières'
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class TeacherProfile(BaseModel):
    """Teacher profile linked to user account."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_profile'
    )
    employee_id = models.CharField(max_length=50, unique=True)
    specialization = models.CharField(max_length=255, blank=True)
    qualification = models.CharField(max_length=255, blank=True)
    hire_date = models.DateField()
    contract_type = models.CharField(
        max_length=50,
        choices=[
            ('PERMANENT', 'Permanent'),
            ('CONTRACT', 'Contractuel'),
            ('VISITING', 'Vacataire'),
        ],
        default='PERMANENT'
    )
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bio = models.TextField(blank=True)
    academic_year = models.ForeignKey(
        'core.AcademicYear', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='teacher_profiles'
    )
    contract_hours_per_week = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'teacher_profiles'
        verbose_name = 'Profil enseignant'
        verbose_name_plural = 'Profils enseignants'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.employee_id} - {self.user.full_name}"


class TeacherSite(models.Model):
    """Teacher access to multiple sites."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.CASCADE,
        related_name='teacher_sites'
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='site_teachers'
    )
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'teacher_sites'
        unique_together = ['teacher', 'site']

    def __str__(self):
        return f"{self.teacher.user.full_name} - {self.site.name}"


class TeacherDocument(BaseModel):
    """Documents uploaded for a teacher (ID, diplomas, certificates…)."""
    DOCUMENT_TYPES = [
        ('IDENTITY', "Pièce d'identité"),
        ('DIPLOMA', 'Diplôme'),
        ('CERTIFICATE', 'Certificat'),
        ('OTHER', 'Autre'),
    ]
    teacher = models.ForeignKey(
        TeacherProfile, on_delete=models.CASCADE, related_name='documents'
    )
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='OTHER')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='teacher_documents/%Y/')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='uploaded_teacher_documents'
    )

    class Meta:
        db_table = 'teacher_documents'
        verbose_name = 'Document enseignant'
        verbose_name_plural = 'Documents enseignants'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.teacher.user.full_name} – {self.title}"


class TeacherExperience(BaseModel):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='experiences')
    position = models.CharField(max_length=255)          # "Poste / Titre"
    company = models.CharField(max_length=255)           # "Entreprise / Établissement"
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)   # null = poste actuel
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'teacher_experiences'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.teacher.user.full_name} – {self.position} @ {self.company}"


class ClassSubjectTeacher(BaseModel):
    """Assignment of teachers to subjects in classes."""
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='subject_teachers'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='class_teachers'
    )
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.CASCADE,
        related_name='class_subjects'
    )

    class Meta:
        db_table = 'class_subject_teachers'
        verbose_name = 'Attribution enseignant'
        verbose_name_plural = 'Attributions enseignants'
        unique_together = ['class_obj', 'subject']

    def __str__(self):
        return f"{self.class_obj.code} - {self.subject.code} - {self.teacher.user.full_name}"


class Enrollment(BaseModel):
    """Student enrollment in a class."""
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name='enrollments'
    )
    enrollment_date = models.DateField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('ENROLLED', 'Inscrit'),
            ('DROPPED', 'Abandon'),
            ('TRANSFERRED', 'Transféré'),
            ('GRADUATED', 'Diplômé'),
        ],
        default='ENROLLED'
    )

    class Meta:
        db_table = 'enrollments'
        verbose_name = 'Inscription'
        verbose_name_plural = 'Inscriptions'
        unique_together = ['student', 'academic_year']

    def __str__(self):
        return f"{self.student.matricule} - {self.class_obj.code}"


class Room(BaseModel):
    """Classroom/Room model."""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='rooms'
    )
    building = models.CharField(max_length=100, blank=True)
    floor = models.CharField(max_length=20, blank=True)
    capacity = models.PositiveIntegerField(default=30)
    room_type = models.CharField(
        max_length=50,
        choices=[
            ('CLASSROOM', 'Salle de classe'),
            ('LAB', 'Laboratoire'),
            ('AMPHITHEATER', 'Amphithéâtre'),
            ('MEETING', 'Salle de réunion'),
            ('OTHER', 'Autre'),
        ],
        default='CLASSROOM'
    )
    equipment = models.JSONField(default=list, blank=True)

    # GPS geofencing — set these to restrict QR attendance to students inside the room
    gps_latitude      = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True,
                                             help_text='Latitude WGS84 du centre de la salle')
    gps_longitude     = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True,
                                             help_text='Longitude WGS84 du centre de la salle')
    gps_radius_meters = models.PositiveIntegerField(default=50,
                                                     help_text='Rayon en mètres autorisé pour le pointage')

    @property
    def has_gps(self):
        return self.gps_latitude is not None and self.gps_longitude is not None

    class Meta:
        db_table = 'rooms'
        verbose_name = 'Salle'
        verbose_name_plural = 'Salles'
        unique_together = ['code', 'site']
        ordering = ['site', 'building', 'name']

    def __str__(self):
        return f"{self.site.code} - {self.code} ({self.name})"


class Semester(models.Model):
    SEMESTER_CHOICES = [('S1','Semestre 1'),('S2','Semestre 2'),('T1','Trimestre 1'),('T2','Trimestre 2'),('T3','Trimestre 3')]
    academic_year = models.ForeignKey('core.AcademicYear', on_delete=models.CASCADE, related_name='semesters')
    name = models.CharField(max_length=50, choices=SEMESTER_CHOICES)
    label = models.CharField(max_length=100, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['academic_year', 'start_date']
        unique_together = ['academic_year', 'name']
    def __str__(self): return f"{self.label or self.name}"


class LevelSubject(BaseModel):
    """Association matière ↔ niveau (filière + niveau)."""
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name='level_subjects')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='level_subjects')
    coefficient = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    hours_per_week = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        db_table = 'level_subjects'
        verbose_name = 'Matière par niveau'
        verbose_name_plural = 'Matières par niveau'
        unique_together = ['level', 'subject']
        ordering = ['subject__name']

    def __str__(self):
        return f"{self.level} - {self.subject.code}"


class Session(BaseModel):
    """Class session/schedule model."""
    DAY_CHOICES = [
        (0, 'Lundi'),
        (1, 'Mardi'),
        (2, 'Mercredi'),
        (3, 'Jeudi'),
        (4, 'Vendredi'),
        (5, 'Samedi'),
        (6, 'Dimanche'),
    ]

    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sessions'
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions'
    )
    semester = models.ForeignKey(
        'Semester',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions',
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_recurring = models.BooleanField(default=True)
    specific_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'sessions'
        verbose_name = 'Séance'
        verbose_name_plural = 'Séances'
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        day_name = dict(self.DAY_CHOICES).get(self.day_of_week, '')
        return f"{self.class_obj.code} - {self.subject.code} - {day_name} {self.start_time}"
