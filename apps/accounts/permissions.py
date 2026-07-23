from rest_framework.permissions import BasePermission


class IsAdminOrStaff(BasePermission):
    """Restricts to ADMIN/STAFF users.

    UserViewSet/RoleViewSet/PermissionViewSet previously had no
    permission_classes at all (only the project-wide IsAuthenticated
    default applied), so any authenticated user — including a STUDENT —
    could list every account's email/phone, promote themselves to ADMIN
    via PATCH .../users/<id>/ (user_type/site/is_active are writable
    fields), reset any other user's password, or edit/delete Roles and
    Permissions system-wide.
    """

    def has_permission(self, request, view):
        return getattr(request.user, 'user_type', None) in ('ADMIN', 'STAFF')
