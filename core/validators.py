import re
from urllib.parse import urlparse

from django.core.exceptions import ValidationError

PHONE_RE = re.compile(r"^(?:\+7|8)\d{10}$")
GITHUB_HOSTS = ("github.com", "www.github.com")


def validate_github_url(value):
    host = (urlparse(value).hostname or "").lower()
    if host not in GITHUB_HOSTS:
        raise ValidationError("Укажите ссылку на GitHub (github.com).")


def validate_phone(value):
    if not PHONE_RE.match(value):
        raise ValidationError(
            "Телефон должен быть в формате 8XXXXXXXXXX или +7XXXXXXXXXX."
        )
