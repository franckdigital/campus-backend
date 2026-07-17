from celery import shared_task
import logging

logger = logging.getLogger(__name__)

# Fallback values used only when no ReminderConfig(reminder_type='ECHEANCIER')
# exists at all yet in apps.notifications.models — kept so the task still
# behaves exactly as before for installs that haven't configured anything
# from the admin "Alertes & Rappels" screen.
DEFAULT_REMINDER_START_DAY = 25
DEFAULT_REMINDER_INTERVAL_DAYS = 3
REMINDER_CATEGORY = 'echeancier_reminder'


def _get_echeancier_config(student):
    """Resolve the most specific active ECHEANCIER ReminderConfig matching
    this student's site/program/level (mirrors FeeConfiguration's own
    site/program/level priority matching — see get_student_org_scope).
    Returns (config, configs_exist): config is None if nothing matches (or
    nothing configured yet); configs_exist tells the caller whether that
    None means "fall back to hard-coded defaults" (no config exists at all
    system-wide) vs "configs exist, but none apply to this student".
    """
    from apps.notifications.models import ReminderConfig
    from apps.students.models import get_student_org_scope

    all_configs = list(ReminderConfig.objects.filter(reminder_type='ECHEANCIER', is_active=True))
    if not all_configs:
        return None, False

    site_id, program_id, level_id = get_student_org_scope(student)
    best, best_score = None, -1
    for c in all_configs:
        if c.matches_scope(site_id, program_id, level_id):
            score = c.scope_specificity
            if score > best_score:
                best, best_score = c, score
    return best, True


def _maybe_remind_student(student, today, config=None, force=False):
    """Send an échéancier reminder to one student + their parents if (and
    only if) they're actually due for one today. Returns the number of
    notifications sent (0 if skipped). Factored out of send_echeancier_reminders
    so a test/shell script can exercise this exact logic against a specific
    student without looping over — and potentially notifying — every real
    student in the database.

    config=None (automatic daily run): resolves the best-matching active
    config for this student's site/program/level. config=<instance> (the
    "Envoyer maintenant" admin action on one specific config): that exact
    config is used, but ONLY if the student is actually in its scope — an
    admin forcing a Site A-only reminder must never reach Site B students.

    force=True bypasses the start-day/frequency/deadline timing checks
    below, but still respects the scope check above and
    is_up_to_date/echeance_override — forcing a send must not nag a student
    who has nothing due or who this config doesn't target.
    """
    from apps.finance.models import compute_tuition_schedule_status
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_notification, _get_student_parents
    from apps.students.models import get_student_org_scope

    schedule_status = compute_tuition_schedule_status(student)
    if not schedule_status['has_schedule']:
        return 0
    if schedule_status['is_up_to_date'] or schedule_status['echeance_override']:
        return 0

    if config is not None:
        site_id, program_id, level_id = get_student_org_scope(student)
        if not config.matches_scope(site_id, program_id, level_id):
            return 0
        configs_exist = True
    else:
        config, configs_exist = _get_echeancier_config(student)
        if config is None and configs_exist:
            # Configs exist for other sites/programs/levels, but none target
            # this student — no fallback to defaults, same as a barème that
            # simply doesn't cover this student.
            return 0

    start_day     = (config.echeancier_start_day if config and config.echeancier_start_day else DEFAULT_REMINDER_START_DAY)
    interval_days = (config.echeancier_frequency_days if config and config.echeancier_frequency_days else DEFAULT_REMINDER_INTERVAL_DAYS)
    deadline      = config.echeancier_deadline_date if config else None

    last_reminder = Notification.objects.filter(
        recipient=student.user,
        notification_type='REMINDER',
        data__category=REMINDER_CATEGORY,
    ).order_by('-created_at').first()

    if not force:
        if deadline and today > deadline:
            return 0
        if last_reminder is None:
            # First reminder of a new shortfall cycle — only starts on/after
            # the configured start day, never earlier in the month.
            if today.day < start_day:
                return 0
        else:
            days_since = (today - last_reminder.created_at.date()).days
            if days_since < interval_days:
                return 0

    remaining = float(schedule_status['cumulative_due']) - float(schedule_status['cumulative_paid'])
    if remaining <= 0:
        return 0

    remaining_str = f'{remaining:,.0f}'.replace(',', ' ')
    title = 'Rappel — échéancier de scolarité'
    sent_count = 0

    student_notif = Notification.send(
        recipient=student.user,
        notification_type='REMINDER',
        priority='HIGH',
        title=title,
        message=(
            f'Vous avez un solde de {remaining_str} FCFA en retard sur votre échéancier '
            f'de scolarité. Merci de régulariser votre situation auprès de l\'administration.'
        ),
        data={'category': REMINDER_CATEGORY, 'student_id': str(student.id)},
        action_url='/student/finances',
        site=student.site,
    )
    dispatch_notification(student_notif, channels=['IN_APP', 'PUSH'])
    sent_count += 1

    for parent_user in _get_student_parents(student):
        parent_notif = Notification.send(
            recipient=parent_user,
            notification_type='REMINDER',
            priority='HIGH',
            title=title,
            message=(
                f'Votre enfant {student.user.full_name} a un solde de {remaining_str} FCFA '
                f'en retard sur son échéancier de scolarité. Merci de régulariser la situation '
                f'auprès de l\'administration.'
            ),
            data={'category': REMINDER_CATEGORY, 'student_id': str(student.id)},
            action_url='/parent/children',
            site=student.site,
        )
        dispatch_notification(parent_notif, channels=['IN_APP', 'PUSH'])
        sent_count += 1

    return sent_count


@shared_task(name='finance.send_echeancier_reminders')
def send_echeancier_reminders(force=False, config=None):
    """Daily periodic task: nag students (and their parents) who are behind
    on their échéancier de scolarité — whether they've paid nothing at all or
    only partially — starting on the configured start day, then every
    configured N days, until they're fully up to date, the admin grants an
    override, or the configured deadline has passed.

    Each student resolves their OWN best-matching ECHEANCIER config by
    site/program/level (see _get_echeancier_config) when config=None: pass a
    specific config only to force one exact config's send-now (see
    ReminderConfigViewSet.send_now), in which case out-of-scope students are
    silently skipped (see _maybe_remind_student).

    Idempotent per run: a student/parent pair only ever gets one reminder
    per interval window, tracked via the most recent Notification of type
    REMINDER tagged with data.category=echeancier_reminder.
    """
    from django.utils import timezone
    from apps.students.models import Student

    today = timezone.now().date()
    sent_count = 0

    students = Student.objects.filter(is_active=True, status='ACTIVE').select_related('user', 'site')
    for student in students:
        sent_count += _maybe_remind_student(student, today, config=config, force=force)

    logger.info('send_echeancier_reminders: %d notification(s) sent', sent_count)
    return sent_count
