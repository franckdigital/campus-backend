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
    queryset = ReportCard.objects.select_related(
        'student__user', 'class_group', 'semester__academic_year'
    ).all()
    serializer_class = ReportCardSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['student', 'class_group', 'semester', 'status', 'is_published', 'semester__academic_year']

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
                }
            )
            cards.append(card)

        return Response(ReportCardSerializer(cards, many=True).data)

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
