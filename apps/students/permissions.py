from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

from .models import Student


class IsEnrolledOrExempt(BasePermission):
    """A student who hasn't paid at least the minimum enrollment threshold
    (see apps.finance.models.get_min_enrollment_payment) toward their
    scolarité can only use: login/auth, their own profile
    ('me'/'financial-summary'), and the CinetPay payment flow — everything
    else in the app is blocked until they pay.

    Non-student users are never affected. Views/viewsets opt out of the gate
    explicitly (self-documenting, survives renames better than a name
    allowlist buried in this file):
      - `fee_gate_exempt = True` on the whole view/viewset
      - `fee_gate_exempt_actions = (...)` for specific ViewSet actions only
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or user.user_type != 'STUDENT':
            return True

        if getattr(view, 'fee_gate_exempt', False):
            return True

        action = getattr(view, 'action', None)
        if action and action in getattr(view, 'fee_gate_exempt_actions', ()):
            return True

        student = Student.objects.only('id', 'is_enrolled').filter(user=user).first()
        if not student or student.is_enrolled:
            return True

        # The stored flag only self-heals when the student's own financial-
        # summary/dossier view runs (see apps.students.views.financial_summary),
        # so a student who already paid stays locked out of every other screen
        # (grades, notifications, enrollments...) until they happen to revisit
        # that one screen. Recompute from real invoice data here too, instead
        # of trusting a flag that may simply never have been refreshed.
        from apps.finance.models import sync_enrollment_status
        if sync_enrollment_status(student):
            return True

        raise PermissionDenied(
            "Veuillez régler au moins le minimum requis de vos frais de scolarité "
            "pour accéder à cette fonctionnalité. Rendez-vous dans Mes finances "
            "pour effectuer le paiement."
        )
