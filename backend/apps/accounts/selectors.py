from apps.accounts.models import User, normalize_email


def find_active_user_by_email(email: str) -> User | None:
    return User.objects.filter(email=normalize_email(email), is_active=True).first()
