from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Count, Q

from .models import (
    Program, Level, Class, Subject, TeacherProfile, TeacherSite,
    ClassSubjectTeacher, Enrollment, Room, Session, Semester, LevelSubject,
    TeacherDocument, TeacherExperience,
)
from .serializers import (
    ProgramSerializer, LevelSerializer, SubjectSerializer,
    TeacherProfileSerializer, TeacherProfileCreateSerializer, TeacherListSerializer,
    TeacherSiteSerializer, ClassSerializer, ClassListSerializer,
    ClassSubjectTeacherSerializer, EnrollmentSerializer,
    RoomSerializer, SessionSerializer, SemesterSerializer, LevelSubjectSerializer,
    TeacherDocumentSerializer, TeacherExperienceSerializer,
)
from .permissions import IsAdminStaffOrOwningTeacher


def _teacher_profile_of(request):
    """None for ADMIN/STAFF (unrestricted); the TeacherProfile for a teacher; None for
    anyone else too (students never reach here — writes are blocked by permission_classes)."""
    user = request.user
    if getattr(user, 'user_type', None) in ('ADMIN', 'STAFF'):
        return None
    return getattr(user, 'teacher_profile', None)


class SemesterViewSet(viewsets.ModelViewSet):
    queryset = Semester.objects.select_related('academic_year').all()
    serializer_class = SemesterSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['academic_year', 'name', 'is_current']
    ordering_fields = ['start_date', 'end_date']


class ProgramViewSet(viewsets.ModelViewSet):
    queryset = Program.objects.select_related('site').annotate(
        levels_count=Count('levels', filter=Q(levels__is_active=True))
    ).all()
    serializer_class = ProgramSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'created_at']
    filterset_fields = ['site', 'is_active']

    @action(detail=True, methods=['get'])
    def levels(self, request, pk=None):
        program = self.get_object()
        levels = program.levels.all()
        serializer = LevelSerializer(levels, many=True)
        return Response(serializer.data)


class LevelViewSet(viewsets.ModelViewSet):
    queryset = Level.objects.select_related('program').annotate(
        # distinct=True: two Count()s over different reverse relations on the
        # same queryset would otherwise fan out and inflate each other via the
        # join, so each must count only its own distinct related rows.
        classes_count=Count('classes', filter=Q(classes__is_active=True), distinct=True),
        subjects_count=Count('level_subjects', filter=Q(level_subjects__is_active=True), distinct=True),
    ).all()
    serializer_class = LevelSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'code']
    ordering_fields = ['order', 'name']
    filterset_fields = ['program', 'is_active']

    def get_queryset(self):
        queryset = super().get_queryset()
        p = self.request.query_params
        site_id = p.get('site_id') or p.get('site') or p.get('program__site')
        if site_id:
            # Level has no direct site FK — site is reachable only via program.site
            queryset = queryset.filter(program__site_id=site_id)
        return queryset


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.annotate(
        levels_count=Count('level_subjects', filter=Q(level_subjects__is_active=True))
    ).all()
    serializer_class = SubjectSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'code']
    filterset_fields = ['is_active']

    def get_queryset(self):
        qs = super().get_queryset()
        # Subject has no site FK (it's a shared catalog across sites) — a
        # bare ?site= was silently ignored by django-filter, so every site's
        # dashboard showed the platform-wide subject count instead of just
        # the subjects actually assigned to a class at that site.
        site = self.request.query_params.get('site')
        if site:
            qs = qs.filter(class_teachers__class_obj__site_id=site).distinct()
        return qs


class TeacherViewSet(viewsets.ModelViewSet):
    queryset = TeacherProfile.objects.select_related('user').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['employee_id', 'user__email', 'user__first_name', 'user__last_name']
    ordering_fields = ['user__last_name', 'hire_date']
    filterset_fields = ['contract_type', 'is_active']

    def get_queryset(self):
        queryset = super().get_queryset()
        p = self.request.query_params
        site_id = p.get('site_id') or p.get('site')
        if site_id:
            # TeacherProfile.sites is not a direct M2M — uses TeacherSite through model
            queryset = queryset.filter(teacher_sites__site_id=site_id).distinct()
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return TeacherListSerializer
        if self.action == 'create':
            return TeacherProfileCreateSerializer
        return TeacherProfileSerializer

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Return the TeacherProfile of the currently authenticated user."""
        try:
            teacher = TeacherProfile.objects.select_related('user').get(user=request.user)
            serializer = TeacherProfileSerializer(teacher, context={'request': request})
            return Response(serializer.data)
        except TeacherProfile.DoesNotExist:
            return Response({'detail': 'Profil enseignant non trouvé.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='assign-sites')
    def assign_sites(self, request, pk=None):
        teacher = self.get_object()
        site_ids = request.data.get('site_ids', [])
        primary_site_id = request.data.get('primary_site_id')

        TeacherSite.objects.filter(teacher=teacher).exclude(site_id__in=site_ids).delete()

        for site_id in site_ids:
            is_primary = str(site_id) == str(primary_site_id)
            TeacherSite.objects.update_or_create(
                teacher=teacher,
                site_id=site_id,
                defaults={'is_primary': is_primary}
            )

        return Response(TeacherProfileSerializer(teacher).data)

    @action(detail=True, methods=['get'])
    def sites(self, request, pk=None):
        teacher = self.get_object()
        teacher_sites = teacher.teacher_sites.select_related('site')
        serializer = TeacherSiteSerializer(teacher_sites, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def sessions(self, request, pk=None):
        teacher = self.get_object()
        sessions = teacher.sessions.select_related(
            'class_obj__site', 'class_obj__academic_year', 'subject', 'room', 'semester'
        ).filter(is_active=True)
        serializer = SessionSerializer(sessions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def load(self, request):
        """Aggregate weekly hours and assignment counts for each active teacher."""
        teachers = TeacherProfile.objects.filter(is_active=True).select_related('user').prefetch_related(
            'sessions', 'class_subjects__class_obj__level__program', 'class_subjects__subject'
        )
        result = []
        for teacher in teachers:
            sessions = teacher.sessions.filter(is_active=True)
            weekly_hours = 0.0
            for s in sessions:
                h1 = s.start_time.hour * 60 + s.start_time.minute
                h2 = s.end_time.hour * 60 + s.end_time.minute
                weekly_hours += max(0, h2 - h1) / 60.0

            assignments = teacher.class_subjects.filter(is_active=True)
            result.append({
                'id': str(teacher.id),
                'employee_id': teacher.employee_id,
                'full_name': teacher.user.full_name,
                'email': teacher.user.email,
                'specialization': teacher.specialization,
                'contract_type': teacher.contract_type,
                'sessions_count': sessions.count(),
                'weekly_hours': round(weekly_hours, 1),
                'subjects_count': assignments.values('subject').distinct().count(),
                'classes_count': assignments.values('class_obj').distinct().count(),
            })
        result.sort(key=lambda x: x['full_name'])
        return Response(result)

    @action(detail=True, methods=['get'], url_path='profil')
    def profil(self, request, pk=None):
        """Detailed teacher profile: info + assignments + sessions + workload."""
        teacher = self.get_object()
        user = teacher.user

        assignments = teacher.class_subjects.select_related(
            'class_obj__level__program', 'subject'
        ).filter(is_active=True)

        sessions = teacher.sessions.select_related('class_obj', 'subject', 'room').filter(is_active=True)

        weekly_hours = 0.0
        for s in sessions:
            h1 = s.start_time.hour * 60 + s.start_time.minute
            h2 = s.end_time.hour * 60 + s.end_time.minute
            weekly_hours += max(0, h2 - h1) / 60.0

        aff_data = [
            {
                'id': str(a.id),
                'subject_id': str(a.subject.id),
                'subject_code': a.subject.code,
                'subject_name': a.subject.name,
                'class_id': str(a.class_obj.id),
                'class_name': a.class_obj.name,
                'class_code': a.class_obj.code,
                'level_name': a.class_obj.level.name,
                'program_name': a.class_obj.level.program.name,
            }
            for a in assignments
        ]

        day_names = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi',
                     4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'}
        sess_data = [
            {
                'id': str(s.id),
                'day_of_week': s.day_of_week,
                'day_name': day_names.get(s.day_of_week, ''),
                'start_time': s.start_time.strftime('%H:%M'),
                'end_time': s.end_time.strftime('%H:%M'),
                'subject_name': s.subject.name,
                'class_name': s.class_obj.name,
                'room_name': s.room.name if s.room else None,
            }
            for s in sorted(sessions, key=lambda x: (x.day_of_week, str(x.start_time)))
        ]

        monthly_hours = (teacher.contract_hours_per_week * 4) if teacher.contract_hours_per_week else None

        return Response({
            'id': str(teacher.id),
            'employee_id': teacher.employee_id,
            'full_name': user.full_name,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone': getattr(user, 'phone', ''),
            'avatar': user.avatar.url if getattr(user, 'avatar', None) and user.avatar else None,
            'specialization': teacher.specialization,
            'qualification': teacher.qualification,
            'hire_date': teacher.hire_date.strftime('%Y-%m-%d') if teacher.hire_date else None,
            'contract_type': teacher.contract_type,
            'hourly_rate': str(teacher.hourly_rate) if teacher.hourly_rate else None,
            'bio': teacher.bio,
            'is_active': teacher.is_active,
            'academic_year': str(teacher.academic_year_id) if teacher.academic_year_id else None,
            'academic_year_name': teacher.academic_year.name if teacher.academic_year_id else None,
            'contract_hours_per_week': teacher.contract_hours_per_week,
            'monthly_hours': monthly_hours,
            'sites': [
                {'site_name': ts.site.name, 'is_primary': ts.is_primary}
                for ts in teacher.teacher_sites.select_related('site').all()
            ],
            'assignments': aff_data,
            'sessions': sess_data,
            'experiences': [
                {
                    'id': str(e.id),
                    'position': e.position,
                    'company': e.company,
                    'start_date': e.start_date.strftime('%Y-%m-%d') if e.start_date else None,
                    'end_date': e.end_date.strftime('%Y-%m-%d') if e.end_date else None,
                    'is_current': e.is_current,
                    'description': e.description,
                }
                for e in teacher.experiences.all()
            ],
            'stats': {
                'assignments_count': len(aff_data),
                'classes_count': assignments.values('class_obj').distinct().count(),
                'subjects_count': assignments.values('subject').distinct().count(),
                'sessions_count': len(sess_data),
                'weekly_hours': round(weekly_hours, 1),
                'overloaded': weekly_hours > 18,
                'contract_hours_per_week': teacher.contract_hours_per_week,
                'monthly_hours': monthly_hours,
            },
        })

    @action(detail=True, methods=['get'], url_path='fiche',
            permission_classes=[], authentication_classes=[])
    def fiche(self, request, pk=None):
        """Génère la fiche complète de l'enseignant en HTML imprimable (auth via ?token=)."""
        from django.http import HttpResponse
        from rest_framework.response import Response as DRFResponse
        import logging
        import html as html_mod
        logger = logging.getLogger(__name__)

        # Auth via ?token= ou Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        token_str = request.query_params.get('token', '')
        jwt_token = token_str or (
            auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
        )
        if jwt_token:
            try:
                from rest_framework_simplejwt.authentication import JWTAuthentication
                jwt_auth = JWTAuthentication()
                validated = jwt_auth.get_validated_token(jwt_token)
                user = jwt_auth.get_user(validated)
            except Exception:
                return DRFResponse({'detail': 'Token invalide ou expiré'}, status=401)
        else:
            return DRFResponse({'detail': 'Non autorisé'}, status=401)

        if not user or not getattr(user, 'is_authenticated', False):
            return DRFResponse({'detail': 'Non autorisé'}, status=401)

        try:
            teacher = TeacherProfile.objects.select_related('user').prefetch_related(
                'teacher_sites__site',
                'class_subjects__class_obj__level__program',
                'class_subjects__subject',
                'sessions__class_obj',
                'sessions__subject',
                'sessions__room',
                'experiences',
            ).get(pk=pk)
        except TeacherProfile.DoesNotExist:
            return DRFResponse({'detail': 'Enseignant introuvable'}, status=404)

        try:
            from .teacher_pdf_utils import generate_teacher_fiche_html
            html = generate_teacher_fiche_html(teacher)
            return HttpResponse(html, content_type='text/html; charset=utf-8')
        except Exception as exc:
            logger.exception('Erreur génération fiche enseignant: %s', exc)
            return HttpResponse(
                f'<html><body style="font-family:sans-serif;padding:40px">'
                f'<h2 style="color:red">Erreur génération fiche</h2>'
                f'<pre>{html_mod.escape(str(exc))}</pre>'
                f'</body></html>',
                content_type='text/html; charset=utf-8',
                status=500,
            )

    @action(detail=True, methods=['get', 'post'], url_path='experiences')
    def experiences(self, request, pk=None):
        teacher = self.get_object()
        if request.method == 'GET':
            exps = teacher.experiences.all()
            return Response(TeacherExperienceSerializer(exps, many=True).data)
        serializer = TeacherExperienceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(teacher=teacher)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='experiences/(?P<exp_id>[^/.]+)')
    def delete_experience(self, request, pk=None, exp_id=None):
        teacher = self.get_object()
        try:
            exp = teacher.experiences.get(pk=exp_id)
        except TeacherExperience.DoesNotExist:
            return Response({'detail': 'Introuvable'}, status=status.HTTP_404_NOT_FOUND)
        exp.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get', 'post'], url_path='documents')
    def documents(self, request, pk=None):
        teacher = self.get_object()
        if request.method == 'GET':
            docs = teacher.documents.all()
            serializer = TeacherDocumentSerializer(docs, many=True, context={'request': request})
            return Response(serializer.data)

        # POST — upload a new document
        serializer = TeacherDocumentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(teacher=teacher, uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='documents/(?P<doc_id>[^/.]+)')
    def delete_document(self, request, pk=None, doc_id=None):
        teacher = self.get_object()
        try:
            doc = teacher.documents.get(pk=doc_id)
        except TeacherDocument.DoesNotExist:
            return Response({'detail': 'Document introuvable'}, status=status.HTTP_404_NOT_FOUND)
        doc.file.delete(save=False)
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClassViewSet(viewsets.ModelViewSet):
    queryset = Class.objects.select_related(
        'level', 'level__program', 'academic_year', 'site', 'main_teacher'
    ).annotate(
        student_count=Count('enrollments', filter=Q(enrollments__is_active=True))
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'code', 'created_at']
    filterset_fields = ['level', 'academic_year', 'site', 'is_active']

    def get_serializer_class(self):
        if self.action == 'list':
            return ClassListSerializer
        return ClassSerializer

    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        class_obj = self.get_object()
        enrollments = class_obj.enrollments.select_related('student__user').filter(is_active=True)
        serializer = EnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='assign-teacher')
    def assign_teacher(self, request, pk=None):
        class_obj = self.get_object()
        subject_id = request.data.get('subject_id')
        teacher_id = request.data.get('teacher_id')

        cst, created = ClassSubjectTeacher.objects.update_or_create(
            class_obj=class_obj,
            subject_id=subject_id,
            defaults={'teacher_id': teacher_id}
        )
        return Response(ClassSubjectTeacherSerializer(cst).data)

    @action(detail=True, methods=['get'])
    def schedule(self, request, pk=None):
        class_obj = self.get_object()
        sessions = class_obj.sessions.select_related('subject', 'teacher', 'room').filter(is_active=True)
        serializer = SessionSerializer(sessions, many=True)
        return Response(serializer.data)


class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.select_related('student__user', 'class_obj', 'academic_year').all()
    serializer_class = EnrollmentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['student__matricule', 'student__user__first_name', 'student__user__last_name']
    ordering_fields = ['enrollment_date', 'status']
    filterset_fields = ['student', 'class_obj', 'academic_year', 'status', 'is_active']
    
    def get_queryset(self):
        """Filter enrollments by site to prevent cross-site data leakage."""
        queryset = super().get_queryset()
        
        # If user has a site restriction, filter by it
        user = self.request.user
        if hasattr(user, 'site') and user.site:
            queryset = queryset.filter(class_obj__site=user.site)
        
        return queryset


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.select_related('site').all()
    serializer_class = RoomSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'code', 'building']
    ordering_fields = ['name', 'capacity']
    filterset_fields = ['site', 'room_type', 'is_active']


class SessionViewSet(viewsets.ModelViewSet):
    queryset = Session.objects.select_related(
        'class_obj__academic_year', 'class_obj__site', 'subject', 'teacher__user', 'room', 'semester'
    ).all()
    serializer_class = SessionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['day_of_week', 'start_time']
    filterset_fields = ['subject', 'room', 'day_of_week', 'is_active', 'semester']
    permission_classes = [IsAuthenticated, IsAdminStaffOrOwningTeacher]

    def get_queryset(self):
        queryset = super().get_queryset()
        p = self.request.query_params

        site_id = p.get('site_id') or p.get('site')
        if site_id:
            queryset = queryset.filter(class_obj__site_id=site_id)

        class_id = p.get('class_id')
        if class_id:
            queryset = queryset.filter(class_obj_id=class_id)

        teacher_id = p.get('teacher_id')
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)

        semester_id = p.get('semester_id')
        if semester_id:
            queryset = queryset.filter(semester_id=semester_id)

        academic_year_id = p.get('academic_year_id')
        if academic_year_id:
            queryset = queryset.filter(class_obj__academic_year_id=academic_year_id)

        return queryset

    def _check_no_overlap(self, teacher, day_of_week, start_time, end_time, exclude_id=None):
        qs = Session.objects.filter(
            teacher=teacher, day_of_week=day_of_week, is_active=True,
            start_time__lt=end_time, end_time__gt=start_time,
        )
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        clash = qs.select_related('subject').first()
        if clash:
            raise ValidationError({'detail':
                f"Ce créneau chevauche un cours déjà planifié ({clash.subject.code} "
                f"{clash.start_time.strftime('%H:%M')}-{clash.end_time.strftime('%H:%M')})."
            })

    def perform_create(self, serializer):
        teacher = _teacher_profile_of(self.request)
        if teacher is None:
            serializer.save()
            return

        class_obj = serializer.validated_data.get('class_obj')
        subject = serializer.validated_data.get('subject')
        if not ClassSubjectTeacher.objects.filter(
            teacher=teacher, class_obj=class_obj, subject=subject, is_active=True
        ).exists():
            raise PermissionDenied("Vous n'enseignez pas cette matière pour cette classe.")

        self._check_no_overlap(
            teacher,
            serializer.validated_data.get('day_of_week'),
            serializer.validated_data.get('start_time'),
            serializer.validated_data.get('end_time'),
        )
        serializer.save(teacher=teacher)

    def perform_update(self, serializer):
        teacher = _teacher_profile_of(self.request)
        if teacher is None:
            serializer.save()
            return

        instance = serializer.instance
        day_of_week = serializer.validated_data.get('day_of_week', instance.day_of_week)
        start_time = serializer.validated_data.get('start_time', instance.start_time)
        end_time = serializer.validated_data.get('end_time', instance.end_time)
        self._check_no_overlap(teacher, day_of_week, start_time, end_time, exclude_id=instance.id)
        serializer.save(teacher=teacher)


class LevelSubjectViewSet(viewsets.ModelViewSet):
    queryset = LevelSubject.objects.select_related('level__program', 'subject').all()
    serializer_class = LevelSubjectSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['level', 'subject', 'is_mandatory', 'is_active']
    ordering_fields = ['subject__name', 'created_at']


class ClassSubjectTeacherViewSet(viewsets.ModelViewSet):
    queryset = ClassSubjectTeacher.objects.select_related(
        'class_obj__level__program', 'subject', 'teacher__user'
    ).all()
    serializer_class = ClassSubjectTeacherSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['class_obj', 'subject', 'teacher', 'is_active']
    search_fields = ['teacher__user__first_name', 'teacher__user__last_name', 'subject__name', 'class_obj__name']
    ordering_fields = ['created_at']
    permission_classes = [IsAuthenticated, IsAdminStaffOrOwningTeacher]

    def _allowed_site_ids(self, teacher):
        """Sites this teacher may self-assign classes in. Empty set = unknown
        (no TeacherSite row and no existing assignment yet) => don't restrict,
        rather than silently blocking a teacher's very first self-assignment."""
        site_ids = set(TeacherSite.objects.filter(teacher=teacher).values_list('site_id', flat=True))
        site_ids |= set(
            ClassSubjectTeacher.objects.filter(teacher=teacher).values_list('class_obj__site_id', flat=True)
        )
        return site_ids

    def create(self, request, *args, **kwargs):
        class_obj_id = request.data.get('class_obj')
        subject_id = request.data.get('subject')
        teacher = _teacher_profile_of(request)

        if teacher is None:
            # Admin/staff: idempotent update-or-create, unchanged.
            teacher_id = request.data.get('teacher')
            obj, created = ClassSubjectTeacher.objects.update_or_create(
                class_obj_id=class_obj_id,
                subject_id=subject_id,
                defaults={'teacher_id': teacher_id, 'is_active': True}
            )
            serializer = self.get_serializer(obj)
            st = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response(serializer.data, status=st)

        # Teacher self-service: never silently reassign another teacher's slot.
        allowed_sites = self._allowed_site_ids(teacher)
        if allowed_sites:
            class_obj = Class.objects.filter(id=class_obj_id).first()
            if class_obj and class_obj.site_id not in allowed_sites:
                raise ValidationError({'detail': "Cette classe n'appartient pas à votre site."})

        existing = ClassSubjectTeacher.objects.filter(
            class_obj_id=class_obj_id, subject_id=subject_id, is_active=True
        ).select_related('teacher__user').first()
        if existing:
            if existing.teacher_id == teacher.id:
                serializer = self.get_serializer(existing)
                return Response(serializer.data, status=status.HTTP_200_OK)
            raise ValidationError({'detail':
                f"Cette matière est déjà enseignée par {existing.teacher.user.full_name} pour cette classe."
            })

        obj = ClassSubjectTeacher.objects.create(
            class_obj_id=class_obj_id, subject_id=subject_id, teacher=teacher, is_active=True,
        )
        serializer = self.get_serializer(obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
