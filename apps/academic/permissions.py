from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminStaffOrOwningTeacher(BasePermission):
    """Read is open to any authenticated user (unchanged behavior — students/
    parents need to view class schedules). Write access requires ADMIN/STAFF
    (unrestricted, as before), or a TEACHER acting on their own row — object
    ownership is checked against `obj.teacher_id`.

    Previously ClassSubjectTeacherViewSet/SessionViewSet had no permission_classes
    at all, so any authenticated user (including students) could create/edit/
    delete any teacher's class assignments or timetable slots.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if getattr(user, 'user_type', None) in ('ADMIN', 'STAFF'):
            return True
        return getattr(user, 'teacher_profile', None) is not None

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if getattr(user, 'user_type', None) in ('ADMIN', 'STAFF'):
            return True
        teacher = getattr(user, 'teacher_profile', None)
        return teacher is not None and obj.teacher_id == teacher.id
