from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

from .models import Student


class IsRegistrationFeePaidOrExempt(BasePermission):
    """A student whose registration fee isn't paid can only use: login/auth,
    their own profile ('me'/'financial-summary'), and the CinetPay payment
    flow — everything else in the app is blocked until they pay.

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

        student = Student.objects.only('registration_fee_paid').filter(user=user).first()
        if not student or student.registration_fee_paid:
            return True

        raise PermissionDenied(
            "Veuillez régler vos frais d'inscription pour accéder à cette "
            "fonctionnalité. Rendez-vous dans Mes finances pour effectuer le paiement."
        )
