from django.contrib.auth.models import AbstractUser
from django.db import models

from core.validators import validate_github_url, validate_phone

from .constants import (
    ABOUT_MAX_LENGTH,
    AVATAR_UPLOAD_TO,
    NAME_MAX_LENGTH,
    PHONE_MAX_LENGTH,
    SURNAME_MAX_LENGTH,
)
from .managers import UserManager
from .services import generate_avatar


class User(AbstractUser):
    username = None
    first_name = None
    last_name = None

    email = models.EmailField("Email", unique=True)
    name = models.CharField("Имя", max_length=NAME_MAX_LENGTH)
    surname = models.CharField("Фамилия", max_length=SURNAME_MAX_LENGTH)
    avatar = models.ImageField("Аватар", upload_to=AVATAR_UPLOAD_TO, blank=True)
    phone = models.CharField(
        "Телефон",
        max_length=PHONE_MAX_LENGTH,
        blank=True,
        validators=[validate_phone],
    )
    github_url = models.URLField(
        "GitHub", blank=True, validators=[validate_github_url]
    )
    about = models.TextField("О себе", max_length=ABOUT_MAX_LENGTH, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name", "surname"]

    objects = UserManager()

    class Meta:
        ordering = ["-date_joined"]
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"

    def __str__(self):
        return f"{self.name} {self.surname}"

    def get_full_name(self):
        return f"{self.name} {self.surname}"

    def get_short_name(self):
        return self.name

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if not self.avatar and (update_fields is None or "avatar" in update_fields):
            self.avatar = generate_avatar(self.name)
        super().save(*args, **kwargs)
