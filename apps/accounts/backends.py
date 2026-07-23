from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class EmailOrPhoneBackend(ModelBackend):
    """Authenticates against email (USERNAME_FIELD) first, falling back to phone.

    Some accounts (walk-in students/parents without a real email) were created
    with a synthetic email like "0777560842@escam.net" — phone login lets them
    sign in with the number they actually recognize.
    """

    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        identifier = username or email
        if identifier is None or password is None:
            return None

        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=identifier)
        except User.DoesNotExist:
            candidates = User.objects.filter(phone=identifier).exclude(phone='')
            if candidates.count() != 1:
                return None
            user = candidates.first()

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
