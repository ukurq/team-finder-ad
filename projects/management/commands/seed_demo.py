from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from projects.models import Project, Skill

DEMO_PASSWORD = "demo-pass-12345"

USERS = [
    ("anna@example.com", "Анна", "Иванова", "Backend-разработчик, люблю Django."),
    ("boris@example.com", "Борис", "Петров", "Frontend и немного дизайна."),
    ("vera@example.com", "Вера", "Сидорова", "Data science, Python."),
]

PROJECTS = [
    (
        "anna@example.com",
        "TeamFinder",
        "Платформа поиска команды для pet-проектов.",
        ["Python", "Django"],
    ),
    (
        "boris@example.com",
        "Трекер привычек",
        "Мобильное веб-приложение для привычек.",
        ["JavaScript", "CSS"],
    ),
    (
        "vera@example.com",
        "Прогноз погоды",
        "Модель прогноза по открытым данным.",
        ["Python", "Pandas"],
    ),
]


class Command(BaseCommand):
    help = "Создаёт тестовых пользователей и проекты (пароль: %s)." % DEMO_PASSWORD

    def handle(self, *args, **options):
        User = get_user_model()
        users = {}
        for email, name, surname, about in USERS:
            user, _ = User.objects.get_or_create(
                email=email, defaults={"name": name, "surname": surname, "about": about}
            )
            user.set_password(DEMO_PASSWORD)
            user.save()
            users[email] = user

        for owner_email, title, description, skills in PROJECTS:
            owner = users[owner_email]
            project, created = Project.objects.get_or_create(
                name=title, owner=owner, defaults={"description": description}
            )
            project.participants.add(owner)
            for skill_name in skills:
                skill, _ = Skill.objects.get_or_create(name=skill_name)
                project.skills.add(skill)
        self.stdout.write(self.style.SUCCESS("Тестовые данные созданы."))
