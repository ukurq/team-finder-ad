import shutil
import tempfile
import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Project, Skill

User = get_user_model()

TEMP_MEDIA = tempfile.mkdtemp()


def tearDownModule():
    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ProjectsTestBase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", password="pass12345", name="Иван", surname="Петров"
        )
        self.other = User.objects.create_user(
            email="other@example.com", password="pass12345", name="Анна", surname="Иванова"
        )
        self.project = Project.objects.create(
            name="Pet-проект", description="Описание", owner=self.owner
        )
        self.project.participants.add(self.owner)

    def post_json(self, url, data=None):
        return self.client.post(
            url, data=json.dumps(data or {}), content_type="application/json"
        )


class ProjectListTests(ProjectsTestBase):
    def test_list_is_public_and_paginated_by_12(self):
        for i in range(14):
            Project.objects.create(name=f"P{i}", owner=self.owner)
        response = self.client.get(reverse("projects:list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 12)
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 2)

    def test_filter_by_skill(self):
        python = Skill.objects.create(name="Python")
        Skill.objects.create(name="Go")
        self.project.skills.add(python)
        Project.objects.create(name="Без навыков", owner=self.owner)

        response = self.client.get(reverse("projects:list"), {"skill": "Python"})
        projects = list(response.context["page_obj"])
        self.assertEqual(projects, [self.project])
        self.assertEqual(response.context["active_skill"], "Python")
        self.assertEqual(list(response.context["all_skills"]), ["Go", "Python"])


class ProjectCrudTests(ProjectsTestBase):
    def test_create_requires_login(self):
        response = self.client.get(reverse("projects:create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response["Location"])

    def test_create_adds_owner_as_participant(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("projects:create"),
            {"name": "Новый", "description": "d", "status": "open"},
        )
        project = Project.objects.get(name="Новый")
        self.assertRedirects(response, reverse("projects:detail", args=[project.id]))
        self.assertEqual(project.owner, self.owner)
        self.assertIn(self.owner, project.participants.all())

    def test_only_owner_can_edit(self):
        url = reverse("projects:edit", args=[self.project.id])
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.owner)
        response = self.client.post(
            url, {"name": "Изменён", "description": "d", "status": "open"}
        )
        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Изменён")

    def test_github_url_must_be_github(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("projects:create"),
            {
                "name": "X",
                "description": "d",
                "status": "open",
                "github_url": "https://example.com/repo",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Project.objects.filter(name="X").exists())

    def test_complete_only_by_owner(self):
        url = reverse("projects:complete", args=[self.project.id])
        self.client.force_login(self.other)
        self.assertEqual(self.post_json(url).status_code, 403)
        self.client.force_login(self.owner)
        response = self.post_json(url)
        self.assertEqual(response.json(), {"status": "ok"})
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.CLOSED)


class ParticipationTests(ProjectsTestBase):
    def test_toggle_participate(self):
        url = reverse("projects:toggle_participate", args=[self.project.id])
        self.client.force_login(self.other)

        response = self.post_json(url)
        self.assertEqual(response.json(), {"status": "ok", "participant": True})
        self.assertIn(self.other, self.project.participants.all())

        response = self.post_json(url)
        self.assertEqual(response.json(), {"status": "ok", "participant": False})
        self.assertNotIn(self.other, self.project.participants.all())

    def test_anonymous_cannot_participate(self):
        url = reverse("projects:toggle_participate", args=[self.project.id])
        self.assertEqual(self.post_json(url).status_code, 401)

    def test_cannot_join_closed_project(self):
        self.project.status = Project.Status.CLOSED
        self.project.save()
        self.client.force_login(self.other)
        url = reverse("projects:toggle_participate", args=[self.project.id])
        self.assertEqual(self.post_json(url).status_code, 400)


class SkillTests(ProjectsTestBase):
    def test_suggestions_limited_to_10(self):
        for i in range(15):
            Skill.objects.create(name=f"Skill{i:02d}")
        response = self.client.get(reverse("projects:skills"), {"q": "skill"})
        self.assertEqual(len(response.json()), 10)

    def test_add_new_and_existing_skill(self):
        self.client.force_login(self.owner)
        url = reverse("projects:add_skill", args=[self.project.id])

        response = self.post_json(url, {"name": "Django"})
        self.assertEqual(response.status_code, 200)
        skill_id = response.json()["id"]
        self.assertEqual(Skill.objects.filter(name="Django").count(), 1)

        # Повторное добавление по имени (в другом регистре) не плодит дубликатов.
        response = self.post_json(url, {"name": "django"})
        self.assertEqual(response.json()["id"], skill_id)
        self.assertEqual(Skill.objects.count(), 1)
        self.assertEqual(self.project.skills.count(), 1)

    def test_add_by_id(self):
        skill = Skill.objects.create(name="Docker")
        self.client.force_login(self.owner)
        url = reverse("projects:add_skill", args=[self.project.id])
        response = self.post_json(url, {"skill_id": skill.id})
        self.assertEqual(response.json()["name"], "Docker")
        self.assertIn(skill, self.project.skills.all())

    def test_only_owner_manages_skills(self):
        skill = Skill.objects.create(name="Docker")
        self.project.skills.add(skill)
        add_url = reverse("projects:add_skill", args=[self.project.id])
        remove_url = reverse("projects:remove_skill", args=[self.project.id, skill.id])

        self.assertEqual(self.post_json(add_url, {"name": "X"}).status_code, 401)
        self.client.force_login(self.other)
        self.assertEqual(self.post_json(add_url, {"name": "X"}).status_code, 403)
        self.assertEqual(self.post_json(remove_url).status_code, 403)
        self.assertIn(skill, self.project.skills.all())

    def test_remove_skill(self):
        skill = Skill.objects.create(name="Docker")
        self.project.skills.add(skill)
        self.client.force_login(self.owner)
        url = reverse("projects:remove_skill", args=[self.project.id, skill.id])
        self.assertEqual(self.post_json(url).json(), {"status": "ok"})
        self.assertNotIn(skill, self.project.skills.all())
        # Сам навык остаётся в справочнике.
        self.assertTrue(Skill.objects.filter(pk=skill.pk).exists())


class ProjectDetailTests(ProjectsTestBase):
    def test_detail_is_public(self):
        response = self.client.get(reverse("projects:detail", args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Необходимые навыки")
        self.assertNotContains(response, "add-skill-btn")

    def test_owner_sees_add_skill_button(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("projects:detail", args=[self.project.id]))
        self.assertContains(response, "add-skill-btn")
