from django.conf import settings
from django.db import models

from core.validators import validate_github_url

from .constants import (
    PROJECT_NAME_MAX_LENGTH,
    PROJECT_STATUS_MAX_LENGTH,
    SKILL_NAME_MAX_LENGTH,
)


class Skill(models.Model):
    name = models.CharField(
        "Название", max_length=SKILL_NAME_MAX_LENGTH, unique=True
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "навык"
        verbose_name_plural = "навыки"

    def __str__(self):
        return self.name


class Project(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Открыт"
        CLOSED = "closed", "Закрыт"

    name = models.CharField("Название", max_length=PROJECT_NAME_MAX_LENGTH)
    description = models.TextField("Описание", blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_projects",
        verbose_name="Автор",
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    github_url = models.URLField(
        "GitHub", blank=True, validators=[validate_github_url]
    )
    status = models.CharField(
        "Статус",
        max_length=PROJECT_STATUS_MAX_LENGTH,
        choices=Status.choices,
        default=Status.OPEN,
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="participated_projects",
        blank=True,
        verbose_name="Участники",
    )
    skills = models.ManyToManyField(
        Skill, related_name="projects", blank=True, verbose_name="Навыки"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "проект"
        verbose_name_plural = "проекты"

    def __str__(self):
        return self.name
