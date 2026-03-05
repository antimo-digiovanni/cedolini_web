from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameBackend(ModelBackend):
    """Allow login with either username or email address."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(get_user_model().USERNAME_FIELD)

        if username is None or password is None:
            return None

        UserModel = get_user_model()

        # Prefer username lookup first to avoid ambiguity when emails are duplicated.
        try:
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            users = UserModel._default_manager.filter(Q(email__iexact=username))
            if users.count() != 1:
                return None
            user = users.first()

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
