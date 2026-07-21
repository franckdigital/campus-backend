from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied


class IsTuitionUpToDateOrNotGated(BasePermission):
    """Blocks a STUDENT from evaluations/devoirs/examens (quiz attempts,
    assignment submissions, exam sessions) when they're behind on their
    tuition payment schedule (échéancier) — regardless of modality.

    Opposite polarity from apps.students.permissions.IsEnrolledOrExempt:
    that one is default-deny-unless-exempted (blocks everything except an
    allowlist); this one is default-ALLOW-unless-the-view-opts-in, since it
    must only block evaluation actions, not lesson/course browsing:
      - `tuition_gate_required = True` on a whole APIView
      - `tuition_gate_actions = (...)` for specific ViewSet actions only

    A student with no payment schedule configured for their site/filière/
    niveau (see FeeConfiguration.installments) is never blocked — the
    échéancier feature is opt-in per niveau, not a blanket new restriction.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or user.user_type != 'STUDENT':
            return True

        is_gated = getattr(view, 'tuition_gate_required', False)
        if not is_gated:
            action = getattr(view, 'action', None)
            is_gated = bool(action) and action in getattr(view, 'tuition_gate_actions', ())
        if not is_gated:
            return True

        from apps.students.models import Student
        from apps.finance.models import compute_tuition_schedule_status

        student = Student.objects.filter(user=user).first()
        if not student:
            return True

        status = compute_tuition_schedule_status(student)
        if status['is_up_to_date']:
            return True

        raise PermissionDenied(
            "Vous n'êtes pas à jour de votre échéancier de scolarité. "
            "Merci de régulariser votre situation auprès de l'administration "
            "pour accéder aux évaluations, devoirs et examens."
        )
