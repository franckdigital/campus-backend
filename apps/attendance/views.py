from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.utils import timezone
from django.db.models import Count
from django.conf import settings
import qrcode
from io import BytesIO
from django.http import HttpResponse
import json
from datetime import time as dt_time, timedelta, datetime as dt_datetime

import math
from .models import AttendanceSession, AttendanceRecord, AbsenceRequest
from .serializers import (
    AttendanceSessionSerializer, AttendanceSessionDetailSerializer,
    AttendanceRecordSerializer, QRScanSerializer,
    AbsenceRequestSerializer, AbsenceRequestCreateSerializer
)
from apps.students.models import Student
from apps.academic.models import Enrollment

DAY_START   = dt_time(7, 30)
DAY_END     = dt_time(18, 30)
EVENING_END = dt_time(22, 0)


def _haversine_meters(lat1, lon1, lat2, lon2):
    """Distance en mètres entre deux points GPS (WGS84)."""
    R = 6_371_000
    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    dphi       = math.radians(float(lat2) - float(lat1))
    dlambda    = math.radians(float(lon2) - float(lon1))
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _notify_parents_on_absence(record):
    """H2: Absence constatée → parents (multi-channel)."""
    try:
        from apps.notifications.services import notify_absence_recorded
        notify_absence_recorded(record)
    except Exception:
        pass  # Never block attendance marking for notification errors


class AttendanceSessionViewSet(viewsets.ModelViewSet):
    queryset = AttendanceSession.objects.select_related(
        'session__class_obj', 'session__subject', 'session__teacher__user', 'opened_by'
    ).all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['date', 'opened_at']
    filterset_fields = ['session', 'date', 'status', 'is_active']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AttendanceSessionDetailSerializer
        return AttendanceSessionSerializer

    def perform_create(self, serializer):
        serializer.save(opened_by=self.request.user)

    @action(detail=True, methods=['get'])
    def qr(self, request, pk=None):
        attendance_session = self.get_object()
        qr_data = json.dumps({
            'type': 'attendance',
            'code': attendance_session.qr_code,
            'session_id': str(attendance_session.id),
            'date': str(attendance_session.date)
        })
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color='black', back_color='white')
        buffer = BytesIO()
        qr_image.save(buffer, format='PNG')
        buffer.seek(0)
        return HttpResponse(buffer.getvalue(), content_type='image/png')

    @action(detail=True, methods=['post'], url_path='refresh-qr')
    def refresh_qr(self, request, pk=None):
        attendance_session = self.get_object()
        expiry_minutes = request.data.get('expiry_minutes', 15)
        attendance_session.refresh_qr(expiry_minutes)
        return Response(AttendanceSessionSerializer(attendance_session).data)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        attendance_session = self.get_object()
        attendance_session.status = 'CLOSED'
        attendance_session.closed_at = timezone.now()
        attendance_session.save()
        return Response(AttendanceSessionSerializer(attendance_session).data)

    @action(detail=True, methods=['get'])
    def records(self, request, pk=None):
        attendance_session = self.get_object()
        records = attendance_session.records.select_related('student__user', 'marked_by')
        serializer = AttendanceRecordSerializer(records, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='mark-all-absent')
    def mark_all_absent(self, request, pk=None):
        attendance_session = self.get_object()
        session = attendance_session.session
        enrollments = Enrollment.objects.filter(
            class_obj=session.class_obj, is_active=True, status='ENROLLED'
        ).select_related('student')
        for enrollment in enrollments:
            AttendanceRecord.objects.get_or_create(
                attendance_session=attendance_session,
                student=enrollment.student,
                defaults={'status': 'ABSENT', 'marked_by': request.user}
            )
        return Response({'detail': f'{enrollments.count()} etudiants marques absents'})


class AttendanceOpenView(APIView):
    def post(self, request):
        session_id = request.data.get('session_id')
        date = request.data.get('date', str(timezone.now().date()))
        expiry_minutes = request.data.get('expiry_minutes', 15)

        from apps.academic.models import Session
        try:
            session = Session.objects.get(id=session_id)
        except Session.DoesNotExist:
            return Response({'detail': 'Seance non trouvee'}, status=status.HTTP_404_NOT_FOUND)

        attendance_session, created = AttendanceSession.objects.get_or_create(
            session=session,
            date=date,
            defaults={
                'opened_by': request.user,
                'qr_expiry': timezone.now() + timezone.timedelta(minutes=expiry_minutes)
            }
        )
        if not created:
            attendance_session.refresh_qr(expiry_minutes)

        return Response(
            AttendanceSessionSerializer(attendance_session).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class AttendanceScanView(APIView):
    def post(self, request):
        serializer = QRScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        qr_code = serializer.validated_data['qr_code']
        student_id = serializer.validated_data.get('student_id')

        attendance_session = AttendanceSession.objects.get(qr_code=qr_code)

        if student_id:
            try:
                student = Student.objects.get(id=student_id)
            except Student.DoesNotExist:
                return Response({'detail': 'Etudiant non trouve'}, status=status.HTTP_404_NOT_FOUND)
        else:
            user = request.user
            if hasattr(user, 'student_profile'):
                student = user.student_profile
            else:
                return Response({'detail': 'Utilisateur non etudiant'}, status=status.HTTP_400_BAD_REQUEST)

        is_enrolled = Enrollment.objects.filter(
            student=student,
            class_obj=attendance_session.session.class_obj,
            is_active=True
        ).exists()

        if not is_enrolled:
            return Response(
                {'detail': 'Etudiant non inscrit dans cette classe'},
                status=status.HTTP_400_BAD_REQUEST
            )

        record, created = AttendanceRecord.objects.get_or_create(
            attendance_session=attendance_session,
            student=student,
            defaults={'status': 'PRESENT', 'check_in_time': timezone.now(), 'check_in_method': 'QR'}
        )
        if not created and record.status == 'ABSENT':
            record.status = 'LATE'
            record.check_in_time = timezone.now()
            record.check_in_method = 'QR'
            record.save()

        return Response(AttendanceRecordSerializer(record).data)


class AttendanceRecordViewSet(viewsets.ModelViewSet):
    queryset = AttendanceRecord.objects.select_related(
        'attendance_session__session__subject',
        'attendance_session__session__class_obj',
        'student__user', 'marked_by'
    ).all()
    serializer_class = AttendanceRecordSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['check_in_time', 'status']
    filterset_fields = ['attendance_session', 'student', 'status', 'check_in_method']

    @action(detail=False, methods=['post'], url_path='mark')
    def mark(self, request):
        """Upsert one attendance record; notifies parents on ABSENT."""
        attendance_session_id = request.data.get('attendance_session')
        student_id = request.data.get('student')
        new_status = (request.data.get('status', 'ABSENT') or '').upper()
        notes = request.data.get('notes', '')
        lat = request.data.get('latitude') or request.data.get('student_latitude')
        lon = request.data.get('longitude') or request.data.get('student_longitude')

        try:
            att_session = AttendanceSession.objects.get(id=attendance_session_id)
            student = Student.objects.get(id=student_id)
        except (AttendanceSession.DoesNotExist, Student.DoesNotExist) as e:
            return Response({'detail': str(e)}, status=status.HTTP_404_NOT_FOUND)

        defaults = {
            'status': new_status,
            'marked_by': request.user,
            'notes': notes,
            'check_in_method': 'MANUAL',
        }
        if new_status == 'PRESENT':
            defaults['check_in_time'] = timezone.now()
        if lat is not None:
            defaults['student_latitude'] = lat
        if lon is not None:
            defaults['student_longitude'] = lon

        record, created = AttendanceRecord.objects.update_or_create(
            attendance_session=att_session,
            student=student,
            defaults=defaults,
        )

        if new_status == 'ABSENT':
            _notify_parents_on_absence(record)

        return Response(
            AttendanceRecordSerializer(record).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], url_path='bulk-mark')
    def bulk_mark(self, request):
        """Mark multiple students.
        Accepts two formats:
          A) { attendance_session, records: [{student, status}, ...] }  ← mobile app
          B) { attendance_session, status, student_ids: [...] }          ← legacy / single-status bulk
        """
        attendance_session_id = request.data.get('attendance_session')
        records_list = request.data.get('records')      # format A
        student_ids  = request.data.get('student_ids', [])  # format B
        bulk_status  = (request.data.get('status', 'ABSENT') or '').upper()  # format B

        try:
            att_session = AttendanceSession.objects.get(id=attendance_session_id)
        except AttendanceSession.DoesNotExist:
            return Response({'detail': 'Session non trouvee'}, status=status.HTTP_404_NOT_FOUND)

        count = 0

        if records_list is not None:
            # Format A: per-student status
            for entry in records_list:
                sid = entry.get('student')
                new_status = (entry.get('status', 'PRESENT') or '').upper()
                if not sid:
                    continue
                try:
                    student = Student.objects.get(id=sid)
                    record, _ = AttendanceRecord.objects.update_or_create(
                        attendance_session=att_session,
                        student=student,
                        defaults={
                            'status': new_status,
                            'marked_by': request.user,
                            'check_in_method': 'MANUAL',
                        }
                    )
                    if new_status == 'ABSENT':
                        _notify_parents_on_absence(record)
                    count += 1
                except Student.DoesNotExist:
                    continue
        else:
            # Format B: same status for all (or all enrolled if student_ids empty)
            if not student_ids:
                enrollments = Enrollment.objects.filter(
                    class_obj=att_session.session.class_obj,
                    is_active=True, status='ENROLLED'
                ).select_related('student')
                student_ids = [str(e.student.id) for e in enrollments]

            for sid in student_ids:
                try:
                    student = Student.objects.get(id=sid)
                    record, _ = AttendanceRecord.objects.update_or_create(
                        attendance_session=att_session,
                        student=student,
                        defaults={
                            'status': bulk_status,
                            'marked_by': request.user,
                            'check_in_method': 'MANUAL',
                        }
                    )
                    if bulk_status == 'ABSENT':
                        _notify_parents_on_absence(record)
                    count += 1
                except Student.DoesNotExist:
                    continue

        return Response({'detail': f'{count} enregistrements mis a jour'})

    @action(detail=False, methods=['get'], url_path='student-stats')
    def student_stats(self, request):
        """Per-student absence stats for D5 dashboard."""
        class_filter = request.query_params.get('class_obj')

        enrollments_qs = Enrollment.objects.filter(
            is_active=True, status='ENROLLED'
        ).select_related('student__user', 'class_obj')

        if class_filter:
            enrollments_qs = enrollments_qs.filter(class_obj_id=class_filter)

        student_ids = list(enrollments_qs.values_list('student_id', flat=True))

        # Bulk aggregate — 2 queries total
        agg = (
            AttendanceRecord.objects
            .filter(student_id__in=student_ids)
            .values('student_id', 'status')
            .annotate(n=Count('id'))
        )
        stats_map = {}
        for row in agg:
            sid = str(row['student_id'])
            if sid not in stats_map:
                stats_map[sid] = {}
            stats_map[sid][row['status']] = row['n']

        results = []
        for enrollment in enrollments_qs:
            student = enrollment.student
            sid = str(student.id)
            counts = stats_map.get(sid, {})
            present = counts.get('PRESENT', 0)
            absent = counts.get('ABSENT', 0)
            late = counts.get('LATE', 0)
            excused = counts.get('EXCUSED', 0)
            total = present + absent + late + excused
            absence_rate = round((absent / total * 100) if total > 0 else 0, 1)
            results.append({
                'student_id': sid,
                'student_name': student.user.full_name,
                'student_matricule': student.matricule,
                'class_name': enrollment.class_obj.name,
                'class_id': str(enrollment.class_obj.id),
                'total': total,
                'present': present,
                'absent': absent,
                'late': late,
                'excused': excused,
                'absence_rate': absence_rate,
                'alert': absence_rate > 20,
            })

        results.sort(key=lambda x: x['absence_rate'], reverse=True)
        return Response(results)


class AbsenceRequestViewSet(viewsets.ModelViewSet):
    queryset = AbsenceRequest.objects.select_related('student__user', 'reviewed_by').all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['submitted_at', 'start_date']
    filterset_fields = ['student', 'status', 'is_active']

    def get_serializer_class(self):
        if self.action == 'create':
            return AbsenceRequestCreateSerializer
        return AbsenceRequestSerializer

    def perform_create(self, serializer):
        absence_request = serializer.save()
        # H2: Absence prévue → administration (multi-channel)
        try:
            from apps.notifications.services import notify_absence_planned
            notify_absence_planned(absence_request)
        except Exception:
            pass

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        absence_request = self.get_object()
        notes = request.data.get('notes', '')
        absence_request.approve(request.user, notes)
        try:
            from apps.notifications.models import Notification
            Notification.send(
                recipient=absence_request.student.user,
                notification_type='ATTENDANCE',
                title="Demande d'absence approuvee",
                message=(
                    f"Votre demande d'absence du {absence_request.start_date} "
                    f"au {absence_request.end_date} a ete approuvee."
                ),
                priority='NORMAL',
                action_url='/student/presences',
            )
        except Exception:
            pass
        return Response(AbsenceRequestSerializer(absence_request).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        absence_request = self.get_object()
        notes = request.data.get('notes', '')
        absence_request.reject(request.user, notes)
        try:
            from apps.notifications.models import Notification
            Notification.send(
                recipient=absence_request.student.user,
                notification_type='ATTENDANCE',
                title="Demande d'absence refusee",
                message=(
                    f"Votre demande d'absence du {absence_request.start_date} "
                    f"au {absence_request.end_date} a ete refusee."
                    + (f" Motif : {notes}" if notes else '')
                ),
                priority='NORMAL',
                action_url='/student/presences',
            )
        except Exception:
            pass
        return Response(AbsenceRequestSerializer(absence_request).data)


# ─── QR Code per-class attendance ─────────────────────────────────────────────

class ClassQRView(APIView):
    """GET /attendance/class-qr/<class_id>/ — PNG QR code linking to the scan page."""

    def get(self, request, class_id):
        from apps.academic.models import Class
        try:
            cls = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            return Response({'detail': 'Classe non trouvee'}, status=status.HTTP_404_NOT_FOUND)

        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5175')
        scan_url = f"{frontend_url}/scan/{class_id}"

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(scan_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')

        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        resp = HttpResponse(buf.getvalue(), content_type='image/png')
        safe_name = cls.name.replace(' ', '-')
        resp['Content-Disposition'] = f'inline; filename="qr-{safe_name}.png"'
        resp['Cache-Control'] = 'no-cache'
        return resp


class ClassStudentsView(APIView):
    """GET /attendance/class-students/<class_id>/ — enrolled students (public, for scan page)."""
    permission_classes = []
    authentication_classes = []

    def get(self, request, class_id):
        from apps.academic.models import Class
        try:
            cls = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            return Response({'detail': 'Classe non trouvee'}, status=status.HTTP_404_NOT_FOUND)

        enrollments = Enrollment.objects.filter(
            class_obj=cls, is_active=True, status='ENROLLED'
        ).select_related('student__user').order_by('student__user__last_name')

        students = [
            {
                'id': str(e.student.id),
                'name': e.student.user.full_name,
                'matricule': e.student.matricule,
            }
            for e in enrollments
        ]

        return Response({
            'class_id': str(cls.id),
            'class_name': cls.name,
            'class_code': getattr(cls, 'code', ''),
            'students': students,
        })


class StudentScanView(APIView):
    """POST /attendance/student-scan/ — public endpoint, two modes:
      - Option A (class QR): {class_id, session_id, student_id}
      - Option B (teacher QR): {class_id, code, student_id}
    """
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        student_id = request.data.get('student_id')
        class_id   = request.data.get('class_id')
        code       = request.data.get('code')       # Option B: QR token
        session_id = request.data.get('session_id') # Option A: academic Session UUID
        student_lat = request.data.get('latitude')
        student_lon = request.data.get('longitude')

        if not student_id or not class_id:
            return Response(
                {'detail': 'student_id et class_id sont requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({'detail': 'Etudiant non trouve'}, status=status.HTTP_404_NOT_FOUND)

        # ── Option B: teacher QR with expiring token ─────────────────
        if code:
            try:
                att_session = AttendanceSession.objects.select_related(
                    'session__class_obj', 'session__subject', 'session__room'
                ).get(qr_code=code)
            except AttendanceSession.DoesNotExist:
                return Response(
                    {'detail': 'QR code invalide', 'code': 'INVALID_QR'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not att_session.is_qr_valid():
                return Response(
                    {'detail': "QR code expire, demandez a l'enseignant de le rafraichir", 'code': 'QR_EXPIRED'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if att_session.is_postponed:
                return Response(
                    {'detail': 'Ce cours a ete ajourné. Aucune presence a enregistrer.', 'code': 'POSTPONED'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            active_session = att_session.session
            cls = active_session.class_obj

        # ── Option A: student picked session from today's list ────────
        elif session_id:
            from apps.academic.models import Class, Session as AcademicSession
            try:
                cls = Class.objects.get(id=class_id)
            except Class.DoesNotExist:
                return Response({'detail': 'Classe non trouvee'}, status=status.HTTP_404_NOT_FOUND)
            try:
                active_session = AcademicSession.objects.select_related(
                    'subject', 'class_obj', 'room'
                ).get(id=session_id, class_obj=cls)
            except AcademicSession.DoesNotExist:
                return Response({'detail': 'Session non trouvee'}, status=status.HTTP_404_NOT_FOUND)

            att_session, _ = AttendanceSession.objects.get_or_create(
                session=active_session,
                date=timezone.localdate(),
                defaults={'status': 'OPEN'}
            )
            if att_session.is_postponed:
                return Response(
                    {'detail': 'Ce cours a ete ajourné. Aucune presence a enregistrer.', 'code': 'POSTPONED'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        else:
            return Response(
                {'detail': 'code ou session_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── GPS geofencing check ──────────────────────────────────────
        room = getattr(active_session, 'room', None)
        if room and room.has_gps:
            if student_lat is None or student_lon is None:
                return Response(
                    {
                        'detail': 'Votre localisation GPS est requise pour pointer la presence.',
                        'code': 'GPS_REQUIRED',
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                distance = _haversine_meters(
                    room.gps_latitude, room.gps_longitude,
                    student_lat, student_lon
                )
            except (TypeError, ValueError):
                return Response(
                    {'detail': 'Coordonnees GPS invalides.', 'code': 'GPS_INVALID'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if distance > room.gps_radius_meters:
                return Response(
                    {
                        'detail': (
                            f'Vous etes trop loin de la salle ({int(distance)} m). '
                            f'Vous devez etre dans un rayon de {room.gps_radius_meters} m.'
                        ),
                        'code': 'GPS_OUT_OF_RANGE',
                        'distance_meters': round(distance),
                        'allowed_radius': room.gps_radius_meters,
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # ── Enrollment check ──────────────────────────────────────────
        is_enrolled = Enrollment.objects.filter(
            student=student, class_obj=cls, is_active=True, status='ENROLLED'
        ).exists()
        if not is_enrolled:
            return Response(
                {'detail': 'Etudiant non inscrit dans cette classe', 'code': 'NOT_ENROLLED'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── PRESENT / LATE determination ──────────────────────────────
        now_local    = timezone.localtime(timezone.now())
        current_time = now_local.time()
        is_late = current_time > (
            (dt_datetime.combine(now_local.date(), active_session.start_time) + timedelta(minutes=15)).time()
        )

        # ── Mark attendance ───────────────────────────────────────────
        record, created = AttendanceRecord.objects.get_or_create(
            attendance_session=att_session,
            student=student,
            defaults={
                'status': 'LATE' if is_late else 'PRESENT',
                'check_in_time': timezone.now(),
                'check_in_method': 'QR',
            }
        )

        if not created and record.status == 'ABSENT':
            record.status = 'LATE' if is_late else 'PRESENT'
            record.check_in_time = timezone.now()
            record.check_in_method = 'QR'
            record.save()

        return Response({
            'success': True,
            'already_marked': not created and record.status != 'ABSENT',
            'record_status': record.status,
            'is_late': record.status == 'LATE',
            'student_name': student.user.full_name,
            'class_name': cls.name,
            'subject_name': active_session.subject.name if active_session.subject else '',
            'session_time': f"{active_session.start_time.strftime('%H:%M')} - {active_session.end_time.strftime('%H:%M')}",
        })


class AutoMarkAbsentView(APIView):
    """POST /attendance/auto-mark-absent/ — marks absent all unmarked students for a date/slot."""

    def post(self, request):
        from datetime import date as date_type
        from apps.academic.models import Session as AcademicSession

        date_str = request.data.get('date', str(timezone.localdate()))
        slot     = request.data.get('slot', 'ALL')  # DAY | EVENING | ALL

        try:
            target_date = date_type.fromisoformat(date_str)
        except ValueError:
            return Response({'detail': 'Format de date invalide (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        target_dow = target_date.weekday()  # 0 = Lundi
        sessions_qs = AcademicSession.objects.filter(day_of_week=target_dow, is_active=True)

        if slot == 'DAY':
            sessions_qs = sessions_qs.filter(start_time__lt=DAY_END)
        elif slot == 'EVENING':
            sessions_qs = sessions_qs.filter(start_time__gte=DAY_END)

        marked = 0
        processed = 0

        for session in sessions_qs:
            att_session, _ = AttendanceSession.objects.get_or_create(
                session=session,
                date=target_date,
                defaults={'status': 'CLOSED'}
            )

            # Skip postponed sessions — nobody should be marked absent
            if att_session.is_postponed:
                continue

            if att_session.status == 'OPEN':
                att_session.status = 'CLOSED'
                att_session.closed_at = timezone.now()
                att_session.save()

            enrollments = Enrollment.objects.filter(
                class_obj=session.class_obj, is_active=True, status='ENROLLED'
            ).select_related('student')

            for e in enrollments:
                _, created = AttendanceRecord.objects.get_or_create(
                    attendance_session=att_session,
                    student=e.student,
                    defaults={'status': 'ABSENT', 'check_in_method': 'AUTO'}
                )
                if created:
                    marked += 1

            processed += 1

        return Response({
            'detail': f'{marked} etudiants marques absents sur {processed} seances',
            'sessions_processed': processed,
            'students_marked_absent': marked,
            'date': date_str,
            'slot': slot,
        })


class ClassTodaySessionsView(APIView):
    """GET /attendance/class-sessions-today/<class_id>/ — today's sessions (public, for scan page)."""
    permission_classes = []
    authentication_classes = []

    def get(self, request, class_id):
        from apps.academic.models import Class, Session as AcademicSession
        try:
            cls = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            return Response({'detail': 'Classe non trouvee'}, status=status.HTTP_404_NOT_FOUND)

        today     = timezone.localdate()
        today_dow = today.weekday()  # 0 = Lundi

        sessions_qs = AcademicSession.objects.filter(
            class_obj=cls,
            day_of_week=today_dow,
            is_active=True,
        ).select_related('subject').order_by('start_time')

        result = []
        for s in sessions_qs:
            att = AttendanceSession.objects.filter(session=s, date=today).first()
            result.append({
                'session_id':        str(s.id),
                'subject_name':      s.subject.name if s.subject else 'Cours',
                'start_time':        s.start_time.strftime('%H:%M'),
                'end_time':          s.end_time.strftime('%H:%M'),
                'att_session_id':    str(att.id) if att else None,
                'att_session_status': att.status if att else None,
                'is_postponed':      att.is_postponed if att else False,
                'postponement_reason': att.postponement_reason if att else '',
                'room_has_gps':      s.room.has_gps if s.room else False,
            })

        return Response({
            'class_id': str(cls.id),
            'class_name': cls.name,
            'date': str(today),
            'sessions': result,
        })


class PostponeSessionView(APIView):
    """POST /attendance/postpone-session/
    Teacher adjourns a specific session occurrence for today (or a given date).
    Body: {session_id, date (opt), reason (opt)}
    Creates or updates the AttendanceSession with is_postponed=True.
    """

    def post(self, request):
        from apps.academic.models import Session as AcademicSession
        session_id = request.data.get('session_id')
        date_str   = request.data.get('date', str(timezone.localdate()))
        reason     = request.data.get('reason', '')

        if not session_id:
            return Response({'detail': 'session_id requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from datetime import date as date_type
            target_date = date_type.fromisoformat(date_str)
        except ValueError:
            return Response({'detail': 'Format de date invalide (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = AcademicSession.objects.select_related(
                'class_obj', 'subject', 'teacher__user'
            ).get(id=session_id)
        except AcademicSession.DoesNotExist:
            return Response({'detail': 'Seance non trouvee'}, status=status.HTTP_404_NOT_FOUND)

        # Any authenticated teacher can postpone (the mobile app only surfaces their own sessions).
        # Admins/staff can always postpone.
        user = request.user
        is_teacher = hasattr(user, 'teacher_profile')
        is_admin   = user.user_type in ('ADMIN', 'STAFF')
        if not (is_teacher or is_admin):
            return Response(
                {'detail': "Seul un enseignant ou un administrateur peut ajourner ce cours."},
                status=status.HTTP_403_FORBIDDEN
            )

        att_session, created = AttendanceSession.objects.get_or_create(
            session=session,
            date=target_date,
            defaults={
                'status':        'CLOSED',
                'is_postponed':  True,
                'postponement_reason': reason,
                'postponed_by':  user,
                'postponed_at':  timezone.now(),
            }
        )

        if not created:
            att_session.is_postponed        = True
            att_session.postponement_reason = reason
            att_session.postponed_by        = user
            att_session.postponed_at        = timezone.now()
            att_session.status              = 'CLOSED'
            att_session.save(update_fields=[
                'is_postponed', 'postponement_reason',
                'postponed_by', 'postponed_at', 'status',
            ])

        # Notify enrolled students
        try:
            from apps.notifications.models import Notification
            from apps.notifications.services import dispatch_notification
            from apps.notifications.push import push_to_user
            enrollments = Enrollment.objects.filter(
                class_obj=session.class_obj, is_active=True, status='ENROLLED'
            ).select_related('student__user')

            subject_name = session.subject.name if session.subject else 'cours'
            msg = (
                f'Le cours de {subject_name} du {target_date.strftime("%d/%m/%Y")} '
                f'a ete ajourné'
                + (f' : {reason}' if reason else '.')
            )
            for enr in enrollments:
                n = Notification.send(
                    recipient=enr.student.user,
                    notification_type='SYSTEM',
                    priority='HIGH',
                    title='Cours ajourné',
                    message=msg,
                    data={'session_id': str(session.id), 'date': str(target_date)},
                )
                dispatch_notification(n, channels=['IN_APP', 'PUSH'])
                push_to_user(enr.student.user, title='Cours ajourné', body=msg,
                             data={'type': 'POSTPONED', 'session_id': str(session.id)})
        except Exception:
            pass  # Never block the postponement for notification errors

        return Response({
            'detail':     'Cours ajourné avec succès.',
            'session_id': str(session.id),
            'date':       str(target_date),
            'subject':    session.subject.name if session.subject else '',
            'reason':     reason,
            'is_postponed': True,
        }, status=status.HTTP_200_OK)

    def delete(self, request):
        """Cancel postponement (re-open the session)."""
        from apps.academic.models import Session as AcademicSession
        session_id = request.data.get('session_id')
        date_str   = request.data.get('date', str(timezone.localdate()))

        try:
            from datetime import date as date_type
            target_date = date_type.fromisoformat(date_str)
        except ValueError:
            return Response({'detail': 'Format de date invalide'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            att_session = AttendanceSession.objects.get(
                session_id=session_id, date=target_date, is_postponed=True
            )
        except AttendanceSession.DoesNotExist:
            return Response({'detail': 'Aucun ajournement trouvé pour cette séance.'}, status=status.HTTP_404_NOT_FOUND)

        att_session.is_postponed        = False
        att_session.postponement_reason = ''
        att_session.status              = 'OPEN'
        att_session.save(update_fields=['is_postponed', 'postponement_reason', 'status'])

        return Response({'detail': 'Ajournement annulé. La séance est réouverte.'})


class SessionQRView(APIView):
    """GET /attendance/session-qr/<att_session_id>/ — refresh & return QR PNG (teacher, authenticated)."""

    def get(self, request, att_session_id):
        try:
            att_session = AttendanceSession.objects.select_related(
                'session__class_obj'
            ).get(id=att_session_id)
        except AttendanceSession.DoesNotExist:
            return Response({'detail': 'Session non trouvee'}, status=status.HTTP_404_NOT_FOUND)

        att_session.refresh_qr(expiry_minutes=15)

        cls = att_session.session.class_obj
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5175')
        scan_url = f"{frontend_url}/scan/{cls.id}?code={att_session.qr_code}"

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(scan_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')

        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        resp = HttpResponse(buf.getvalue(), content_type='image/png')
        resp['Content-Disposition'] = 'inline; filename="qr-session.png"'
        resp['Cache-Control'] = 'no-cache'
        return resp
