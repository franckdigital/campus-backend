import django_filters

from .models import AttendanceRecord


class AttendanceRecordFilter(django_filters.FilterSet):
    site = django_filters.UUIDFilter(
        field_name='attendance_session__session__class_obj__site_id'
    )
    class_obj = django_filters.UUIDFilter(
        field_name='attendance_session__session__class_obj_id'
    )
    level = django_filters.UUIDFilter(
        field_name='attendance_session__session__class_obj__level_id'
    )
    program = django_filters.UUIDFilter(
        field_name='attendance_session__session__class_obj__level__program_id'
    )
    date_from = django_filters.DateFilter(
        field_name='attendance_session__date', lookup_expr='gte'
    )
    date_to = django_filters.DateFilter(
        field_name='attendance_session__date', lookup_expr='lte'
    )

    class Meta:
        model = AttendanceRecord
        fields = [
            'attendance_session', 'student', 'status', 'check_in_method',
            'site', 'class_obj', 'level', 'program', 'date_from', 'date_to',
        ]
