from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from django.db.models import Avg
from io import BytesIO
from decimal import Decimal, ROUND_HALF_UP

from .models import GradeCategory, Evaluation, Grade, ReportCard
from .serializers import (
    GradeCategorySerializer, EvaluationSerializer,
    GradeSerializer, ReportCardSerializer
)


# ─────────────────────────────────────────────────────────────────────────────
# E-Learning ↔ Grades sync
# ─────────────────────────────────────────────────────────────────────────────

class ElearningEvaluationsView(APIView):
    """GET /elearning-evaluations/?class_group=X — liste devoirs/quiz/examens E-Learning."""

    def get(self, request):
        from apps.elearning.models import Assignment, Quiz, SecureExam
        class_id = request.query_params.get('class_group')
        if not class_id:
            return Response([])

        items = []
        for a in Assignment.objects.filter(
            class_obj=class_id, status='PUBLISHED'
        ).select_related('subject', 'class_obj').order_by('title'):
            items.append({
                'type': 'ASSIGNMENT', 'id': str(a.id),
                'title': a.title,
                'subject_id': str(a.subject_id),
                'subject_name': a.subject.name,
                'class_name': a.class_obj.name,
                'max_score': float(a.max_score),
                'due_date': str(a.due_date.date()) if a.due_date else None,
            })

        for q in Quiz.objects.filter(
            class_obj=class_id, is_published=True
        ).select_related('subject', 'class_obj').order_by('title'):
            max_s = float(q.max_score) if q.max_score else 20
            items.append({
                'type': 'QUIZ', 'id': str(q.id),
                'title': q.title,
                'subject_id': str(q.subject_id),
                'subject_name': q.subject.name,
                'class_name': q.class_obj.name,
                'max_score': max_s,
            })

        for e in SecureExam.objects.filter(
            class_obj=class_id, is_published=True
        ).select_related('subject', 'class_obj').order_by('title'):
            items.append({
                'type': 'EXAM', 'id': str(e.id),
                'title': e.title,
                'subject_id': str(e.subject_id),
                'subject_name': e.subject.name,
                'class_name': e.class_obj.name,
                'max_score': float(e.max_score),
            })

        return Response(items)


class ElearningStudentScoresView(APIView):
    """GET /elearning-student-scores/{type}/{id}/ — scores étudiants pour un item E-Learning."""

    def get(self, request, item_type, item_id):
        from apps.elearning.models import (
            Assignment, AssignmentSubmission, AssignmentCorrection,
            Quiz, QuizAttempt,
            SecureExam, ExamSession,
        )
        from apps.academic.models import Enrollment

        students_data = []
        item_info = {}

        if item_type == 'ASSIGNMENT':
            try:
                obj = Assignment.objects.select_related('subject', 'class_obj').get(id=item_id)
            except Assignment.DoesNotExist:
                return Response({'detail': 'Devoir introuvable'}, status=404)

            enrollments = Enrollment.objects.filter(
                class_obj=obj.class_obj, status='ENROLLED', is_active=True
            ).select_related('student__user')

            subs = {str(s.student_id): s for s in AssignmentSubmission.objects.filter(assignment=obj)}
            corrections = {}
            for s in subs.values():
                if hasattr(s, 'correction'):
                    try:
                        corrections[str(s.student_id)] = s.correction
                    except Exception:
                        pass

            for enr in enrollments:
                student = enr.student
                sid = str(student.id)
                cor = corrections.get(sid)
                sub = subs.get(sid)
                students_data.append({
                    'student_id': sid,
                    'student_name': student.user.full_name if student.user else '',
                    'student_matricule': student.matricule,
                    'score': float(cor.score) if cor else None,
                    'max_score': float(obj.max_score),
                    'submitted': sub is not None,
                    'graded': cor is not None,
                    'comment': cor.feedback if cor else '',
                })

            item_info = {
                'type': 'ASSIGNMENT', 'id': str(obj.id), 'title': obj.title,
                'subject_id': str(obj.subject_id), 'subject_name': obj.subject.name,
                'class_id': str(obj.class_obj_id), 'class_name': obj.class_obj.name,
                'max_score': float(obj.max_score),
            }

        elif item_type == 'QUIZ':
            try:
                obj = Quiz.objects.select_related('subject', 'class_obj').get(id=item_id)
            except Quiz.DoesNotExist:
                return Response({'detail': 'Quiz introuvable'}, status=404)

            enrollments = Enrollment.objects.filter(
                class_obj=obj.class_obj, status='ENROLLED', is_active=True
            ).select_related('student__user')

            best_attempts = {}
            for att in QuizAttempt.objects.filter(quiz=obj).select_related('student'):
                sid = str(att.student_id)
                if sid not in best_attempts or float(att.percent) > float(best_attempts[sid].percent):
                    best_attempts[sid] = att

            max_s = float(obj.max_score) if obj.max_score else 20

            for enr in enrollments:
                student = enr.student
                sid = str(student.id)
                att = best_attempts.get(sid)
                score_on_max = round(float(att.percent) / 100 * 20, 2) if att else None
                students_data.append({
                    'student_id': sid,
                    'student_name': student.user.full_name if student.user else '',
                    'student_matricule': student.matricule,
                    'score': score_on_max,
                    'max_score': 20,
                    'submitted': att is not None,
                    'graded': att is not None and att.is_graded,
                    'percent': float(att.percent) if att else None,
                    'comment': f"{float(att.percent):.0f}% — {'Réussi' if att.is_passed else 'Échoué'}" if att else '',
                })

            item_info = {
                'type': 'QUIZ', 'id': str(obj.id), 'title': obj.title,
                'subject_id': str(obj.subject_id), 'subject_name': obj.subject.name,
                'class_id': str(obj.class_obj_id), 'class_name': obj.class_obj.name,
                'max_score': 20,
            }

        elif item_type == 'EXAM':
            try:
                obj = SecureExam.objects.select_related('subject', 'class_obj').get(id=item_id)
            except SecureExam.DoesNotExist:
                return Response({'detail': 'Examen introuvable'}, status=404)

            enrollments = Enrollment.objects.filter(
                class_obj=obj.class_obj, status='ENROLLED', is_active=True
            ).select_related('student__user')

            sessions = {str(s.student_id): s for s in ExamSession.objects.filter(exam=obj).select_related('student')}

            for enr in enrollments:
                student = enr.student
                sid = str(student.id)
                ses = sessions.get(sid)
                score = float(ses.score) if ses and ses.score is not None else None
                students_data.append({
                    'student_id': sid,
                    'student_name': student.user.full_name if student.user else '',
                    'student_matricule': student.matricule,
                    'score': score,
                    'max_score': float(obj.max_score),
                    'submitted': ses is not None and ses.status == 'SUBMITTED',
                    'graded': ses is not None and ses.score is not None,
                    'comment': ses.feedback if ses else '',
                })

            item_info = {
                'type': 'EXAM', 'id': str(obj.id), 'title': obj.title,
                'subject_id': str(obj.subject_id), 'subject_name': obj.subject.name,
                'class_id': str(obj.class_obj_id), 'class_name': obj.class_obj.name,
                'max_score': float(obj.max_score),
            }

        else:
            return Response({'detail': 'Type invalide (ASSIGNMENT|QUIZ|EXAM)'}, status=400)

        students_data.sort(key=lambda x: x['student_name'])
        return Response({'item': item_info, 'students': students_data})


class ElearningImportGradesView(APIView):
    """POST /elearning-import-grades/ — importe les scores E-Learning dans le modèle Grade."""

    def post(self, request):
        from apps.students.models import Student
        from apps.academic.models import Semester

        item_type   = request.data.get('type')
        item_id     = request.data.get('item_id')
        semester_id = request.data.get('semester_id')
        grades_data = request.data.get('grades', [])

        if not item_type or not item_id or not grades_data:
            return Response({'detail': 'type, item_id et grades requis'}, status=400)

        semester = None
        if semester_id:
            try:
                semester = Semester.objects.get(id=semester_id)
            except Semester.DoesNotExist:
                pass

        # Resolve subject + class from source item
        from apps.elearning.models import Assignment, Quiz, SecureExam
        subject_id = class_id = None
        max_score  = Decimal('20')

        if item_type == 'ASSIGNMENT':
            obj = Assignment.objects.select_related('subject', 'class_obj').get(id=item_id)
            subject_id, class_id, max_score = obj.subject_id, obj.class_obj_id, obj.max_score
        elif item_type == 'QUIZ':
            obj = Quiz.objects.select_related('subject', 'class_obj').get(id=item_id)
            subject_id, class_id, max_score = obj.subject_id, obj.class_obj_id, Decimal('20')
        elif item_type == 'EXAM':
            obj = SecureExam.objects.select_related('subject', 'class_obj').get(id=item_id)
            subject_id, class_id, max_score = obj.subject_id, obj.class_obj_id, obj.max_score
        else:
            return Response({'detail': 'Type invalide'}, status=400)

        from django.utils import timezone as tz
        created = updated = 0

        for item in grades_data:
            student_id = item.get('student_id')
            score      = item.get('score')
            if student_id is None or score is None:
                continue
            try:
                student = Student.objects.get(id=student_id)
            except Student.DoesNotExist:
                continue

            try:
                qs = Grade.objects.filter(
                    student=student,
                    subject_id=subject_id,
                    class_group_id=class_id,
                    semester=semester,
                    evaluation__isnull=True,
                )
                defaults = dict(
                    score=Decimal(str(score)),
                    max_score=max_score,
                    date=tz.now().date(),
                    comment=item.get('comment', ''),
                    entered_by=request.user,
                )
                if qs.exists():
                    qs.update(**defaults)
                    updated += 1
                else:
                    Grade.objects.create(
                        student=student,
                        subject_id=subject_id,
                        class_group_id=class_id,
                        semester=semester,
                        evaluation=None,
                        **defaults,
                    )
                    created += 1
            except Exception:
                continue

        return Response({'created': created, 'updated': updated})


def _compute_student_averages(student, class_group, semester):
    """
    Returns (global_average, subject_averages_dict).
    subject_averages = {subject_id: {name, code, coefficient, average, grades: [...]}}
    global_average = weighted avg of subject averages by coefficient.
    """
    from apps.academic.models import Subject, LevelSubject

    grades_qs = Grade.objects.filter(
        student=student,
        class_group=class_group,
        semester=semester,
    ).select_related('subject', 'evaluation')

    # Group by subject
    subject_map = {}
    for g in grades_qs:
        sid = str(g.subject_id)
        if sid not in subject_map:
            subject_map[sid] = {
                'subject_id': sid,
                'subject_name': g.subject.name,
                'subject_code': g.subject.code,
                'coefficient': float(g.subject.coefficient),
                'grades': [],
            }
        subject_map[sid]['grades'].append({
            'evaluation_id': str(g.evaluation_id) if g.evaluation_id else None,
            'evaluation_title': g.evaluation.title if g.evaluation else '',
            'eval_type': g.evaluation.eval_type if g.evaluation else '',
            'eval_coefficient': float(g.evaluation.coefficient) if g.evaluation else 1,
            'score': float(g.score),
            'max_score': float(g.max_score),
            'score_on_20': round(float(g.score) / float(g.max_score) * 20, 2) if g.max_score else 0,
        })

    # Compute subject average (weighted by evaluation coefficient)
    total_coeff = Decimal('0')
    total_weighted = Decimal('0')

    for sid, s in subject_map.items():
        eval_coeff_sum = sum(gr['eval_coefficient'] for gr in s['grades'])
        if eval_coeff_sum > 0:
            subj_avg = sum(
                gr['score_on_20'] * gr['eval_coefficient']
                for gr in s['grades']
            ) / eval_coeff_sum
        else:
            subj_avg = 0
        s['average'] = round(subj_avg, 2)

        coeff = Decimal(str(s['coefficient']))
        total_coeff += coeff
        total_weighted += Decimal(str(subj_avg)) * coeff

    if total_coeff > 0:
        global_avg = (total_weighted / total_coeff).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        global_avg = Decimal('0.00')

    return global_avg, subject_map


def _status_from_average(avg):
    avg = float(avg)
    if avg >= 16:
        return 'HONORS'
    elif avg >= 10:
        return 'PASS'
    elif avg >= 8:
        return 'CONDITIONAL'
    else:
        return 'FAIL'


class GradeCategoryViewSet(viewsets.ModelViewSet):
    queryset = GradeCategory.objects.all()
    serializer_class = GradeCategorySerializer


class EvaluationViewSet(viewsets.ModelViewSet):
    queryset = Evaluation.objects.select_related(
        'subject', 'class_group', 'semester', 'locked_by', 'created_by'
    ).all()
    serializer_class = EvaluationSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['subject', 'class_group', 'semester', 'eval_type', 'is_locked']
    ordering_fields = ['date', 'created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        evaluation = self.get_object()
        if evaluation.is_locked:
            return Response({'detail': 'Déjà verrouillée'}, status=status.HTTP_400_BAD_REQUEST)
        evaluation.lock(request.user)
        return Response(EvaluationSerializer(evaluation).data)

    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        evaluation = self.get_object()
        evaluation.unlock()
        return Response(EvaluationSerializer(evaluation).data)

    @action(detail=True, methods=['get'], url_path='students-grades')
    def students_grades(self, request, pk=None):
        """Returns all enrolled students with their score for this evaluation."""
        from apps.academic.models import Enrollment

        evaluation = self.get_object()
        enrollments = Enrollment.objects.filter(
            class_obj=evaluation.class_group,
            status='ENROLLED',
            is_active=True,
        ).select_related('student__user')

        existing_grades = {
            str(g.student_id): g
            for g in Grade.objects.filter(evaluation=evaluation).select_related('student')
        }

        result = []
        for enr in enrollments:
            student = enr.student
            sid = str(student.id)
            grade = existing_grades.get(sid)
            result.append({
                'student_id': sid,
                'student_name': student.user.full_name if student.user else '',
                'student_matricule': student.matricule,
                'score': float(grade.score) if grade else None,
                'comment': grade.comment if grade else '',
                'grade_id': str(grade.id) if grade else None,
            })

        result.sort(key=lambda x: x['student_name'])
        return Response(result)

    @action(detail=True, methods=['post'], url_path='enter-grades')
    def enter_grades(self, request, pk=None):
        """Bulk create/update grades for this evaluation. Payload: {grades: [{student_id, score, comment}]}"""
        evaluation = self.get_object()
        if evaluation.is_locked:
            return Response({'detail': 'Évaluation verrouillée'}, status=status.HTTP_400_BAD_REQUEST)

        grades_data = request.data.get('grades', [])
        if not grades_data:
            return Response({'detail': 'Aucune note fournie'}, status=status.HTTP_400_BAD_REQUEST)

        from apps.students.models import Student

        created, updated = 0, 0
        for item in grades_data:
            student_id = item.get('student_id')
            score = item.get('score')
            if student_id is None or score is None:
                continue
            try:
                student = Student.objects.get(id=student_id)
            except Student.DoesNotExist:
                continue

            try:
                existing_qs = Grade.objects.filter(student=student, evaluation=evaluation)
                existing_count = existing_qs.count()

                if existing_count > 1:
                    # Remove duplicates, keep the most recent
                    oldest_ids = list(existing_qs.order_by('created_at').values_list('id', flat=True)[:-1])
                    Grade.objects.filter(id__in=oldest_ids).delete()
                    existing_count = 1

                grade_defaults = {
                    'subject': evaluation.subject,
                    'class_group': evaluation.class_group,
                    'semester': evaluation.semester,
                    'score': Decimal(str(score)),
                    'max_score': evaluation.max_score,
                    'date': evaluation.date,
                    'comment': item.get('comment', ''),
                    'entered_by': request.user,
                }

                if existing_count == 1:
                    existing_qs.update(**grade_defaults)
                    updated += 1
                else:
                    Grade.objects.create(student=student, evaluation=evaluation, **grade_defaults)
                    created += 1
            except Exception:
                continue

        try:
            from apps.core.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='UPDATE',
                model_name='Grade',
                object_id=str(evaluation.id),
                object_repr=str(evaluation),
                changes={
                    'evaluation': evaluation.title,
                    'subject': str(evaluation.subject),
                    'class': str(evaluation.class_group),
                    'grades_created': created,
                    'grades_updated': updated,
                },
            )
        except Exception:
            pass

        return Response({'created': created, 'updated': updated})


class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.select_related(
        'student', 'subject', 'semester', 'category', 'class_group', 'evaluation'
    ).all()
    serializer_class = GradeSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['student', 'subject', 'semester', 'class_group', 'category', 'evaluation']
    ordering_fields = ['date', 'score', 'created_at']


class ReportCardViewSet(viewsets.ModelViewSet):
    serializer_class = ReportCardSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['student', 'class_group', 'semester', 'status', 'is_published', 'semester__academic_year']

    def get_queryset(self):
        qs = ReportCard.objects.select_related(
            'student__user', 'class_group', 'semester__academic_year'
        )
        # Students only see published bulletins — avoids needing frontend filter update
        user = self.request.user
        if hasattr(user, 'student_profile') and not user.is_staff:
            qs = qs.filter(is_published=True)
        return qs

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate/regenerate bulletins for all students in a class/semester."""
        from apps.academic.models import Enrollment

        class_group_id = request.data.get('class_group_id')
        semester_id = request.data.get('semester_id')

        if not class_group_id or not semester_id:
            return Response(
                {'detail': 'class_group_id et semester_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from apps.academic.models import Class, Semester
        try:
            class_group = Class.objects.get(id=class_group_id)
            semester = Semester.objects.get(id=semester_id)
        except (Class.DoesNotExist, Semester.DoesNotExist):
            return Response({'detail': 'Classe ou semestre introuvable'}, status=status.HTTP_404_NOT_FOUND)

        enrollments = Enrollment.objects.filter(
            class_obj=class_group,
            status='ENROLLED',
            is_active=True,
        ).select_related('student__user')

        cards = []
        student_averages = []

        for enr in enrollments:
            avg, subject_map = _compute_student_averages(enr.student, class_group, semester)
            student_averages.append((enr.student, avg, subject_map))

        # Compute ranks
        student_averages.sort(key=lambda x: -float(x[1]))
        total = len(student_averages)

        for rank, (student, avg, subject_map) in enumerate(student_averages, 1):
            card, _ = ReportCard.objects.update_or_create(
                student=student,
                class_group=class_group,
                semester=semester,
                defaults={
                    'average': avg,
                    'rank': rank,
                    'total_students': total,
                    'status': _status_from_average(avg),
                    'subject_averages': subject_map,
                    'is_published': True,
                }
            )
            cards.append(card)

        return Response(ReportCardSerializer(cards, many=True).data)

    @action(detail=False, methods=['post'], url_path='repair-ranks')
    def repair_ranks(self, request):
        """Re-rank all report cards: within each (class_group, semester), sort by average DESC and assign ranks 1..N."""
        groups = ReportCard.objects.values('class_group', 'semester').distinct()
        total_fixed = 0

        for g in groups:
            cards = list(ReportCard.objects.filter(
                class_group_id=g['class_group'],
                semester_id=g['semester'],
                average__isnull=False,
            ))
            if not cards:
                continue
            cards.sort(key=lambda c: -float(c.average or 0))
            n = len(cards)
            for rank, card in enumerate(cards, 1):
                if card.rank != rank or card.total_students != n:
                    card.rank = rank
                    card.total_students = n
                    card.save(update_fields=['rank', 'total_students'])
                    total_fixed += 1

        return Response({
            'detail': f'{total_fixed} bulletin(s) re-classé(s).',
            'fixed': total_fixed,
        })

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        card = self.get_object()
        card.is_published = not card.is_published
        card.save(update_fields=['is_published'])
        return Response(ReportCardSerializer(card).data)

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        card = self.get_object()
        pdf_buffer = _generate_bulletin_pdf(card)
        student_name = card.student.user.full_name.replace(' ', '_') if card.student.user else 'bulletin'
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="bulletin_{student_name}.pdf"'
        return response

    @action(detail=True, methods=['get'], url_path='html',
            permission_classes=[], authentication_classes=[])
    def html_view(self, request, pk=None):
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from django.http import HttpResponseForbidden

        token = request.query_params.get('token')
        if token:
            try:
                jwt_auth = JWTAuthentication()
                validated = jwt_auth.get_validated_token(token.encode())
                request.user = jwt_auth.get_user(validated)
            except Exception:
                return HttpResponseForbidden('Token invalide')
        elif not request.user or not request.user.is_authenticated:
            return HttpResponseForbidden('Authentification requise')

        try:
            card = ReportCard.objects.select_related(
                'student__user', 'class_group__site', 'semester__academic_year'
            ).get(pk=pk)
        except ReportCard.DoesNotExist:
            from django.http import HttpResponseNotFound
            return HttpResponseNotFound('Bulletin introuvable')

        from .bulletin_html import generate_bulletin_html
        return HttpResponse(generate_bulletin_html(card), content_type='text/html; charset=utf-8')


def _generate_bulletin_pdf(card):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    school_name = card.class_group.site.name if hasattr(card.class_group, 'site') else 'Établissement'

    title_style = ParagraphStyle('title', parent=styles['Heading1'],
                                 alignment=TA_CENTER, fontSize=14, spaceAfter=6)
    subtitle_style = ParagraphStyle('subtitle', parent=styles['Normal'],
                                    alignment=TA_CENTER, fontSize=10, spaceAfter=4)
    label_style = ParagraphStyle('label', parent=styles['Normal'], fontSize=9)

    story.append(Paragraph(school_name.upper(), title_style))
    story.append(Paragraph("BULLETIN DE NOTES", title_style))
    story.append(Spacer(1, 0.3*cm))

    semester_label = card.semester.label if card.semester else ''
    year_label = card.semester.academic_year.name if card.semester and card.semester.academic_year else ''
    story.append(Paragraph(f"{semester_label} – Année {year_label}", subtitle_style))
    story.append(Spacer(1, 0.4*cm))

    # Student info table
    student_name = card.student.user.full_name if card.student.user else ''
    matricule = card.student.matricule
    info_data = [
        ['Étudiant :', student_name, 'Classe :', card.class_group.name],
        ['Matricule :', matricule, 'Moyenne :', f"{card.average}/20" if card.average else '--'],
        ['Rang :', f"{card.rank}/{card.total_students}" if card.rank else '--', 'Mention :', dict(ReportCard.STATUS_CHOICES).get(card.status, card.status)],
    ]
    info_table = Table(info_data, colWidths=[3*cm, 6*cm, 3*cm, 5*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f0f0f0')),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))

    # Grades table
    subject_averages = card.subject_averages or {}
    headers = ['Matière', 'Coeff', 'Moy./20', 'Moy. pondérée']
    table_data = [headers]

    total_coeff = 0
    total_weighted = 0
    for sid, s in subject_averages.items():
        coeff = s.get('coefficient', 1)
        avg = s.get('average', 0)
        table_data.append([
            s.get('subject_name', ''),
            str(coeff),
            f"{avg:.2f}",
            f"{avg * coeff:.2f}",
        ])
        total_coeff += coeff
        total_weighted += avg * coeff

    # Totals row
    table_data.append([
        'TOTAL / MOYENNE GÉNÉRALE',
        str(total_coeff),
        '',
        f"{(total_weighted / total_coeff):.2f}" if total_coeff else '--',
    ])

    col_widths = [9*cm, 2*cm, 3*cm, 3*cm]
    grades_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    grades_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f8ff')]),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8e8f0')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(grades_table)
    story.append(Spacer(1, 0.6*cm))

    # Comments
    if card.teacher_comment:
        story.append(Paragraph(f"<b>Appréciation du professeur principal :</b> {card.teacher_comment}", label_style))
        story.append(Spacer(1, 0.3*cm))
    if card.principal_comment:
        story.append(Paragraph(f"<b>Appréciation du directeur :</b> {card.principal_comment}", label_style))
        story.append(Spacer(1, 0.3*cm))

    # Signature lines
    sig_data = [['Signature du professeur', '', 'Cachet et signature de la direction']]
    sig_table = Table(sig_data, colWidths=[7*cm, 3*cm, 7*cm])
    sig_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 20),
    ]))
    story.append(sig_table)

    doc.build(story)
    buffer.seek(0)
    return buffer
