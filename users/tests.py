import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .constants import AVATAR_SIZE

User = get_user_model()

TEMP_MEDIA = tempfile.mkdtemp()


def tearDownModule():
    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AuthTests(TestCase):
    def test_register_redirects_to_login_and_creates_user(self):
        response = self.client.post(
            reverse("users:register"),
            {
                "name": "Иван",
                "surname": "Петров",
                "email": "Ivan@Example.com",
                "password": "pass12345",
            },
        )
        self.assertRedirects(response, reverse("users:login"))
        user = User.objects.get(email="ivan@example.com")
        self.assertTrue(user.check_password("pass12345"))

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(
            email="a@example.com", password="x", name="А", surname="Б"
        )
        response = self.client.post(
            reverse("users:register"),
            {"name": "В", "surname": "Г", "email": "A@example.com", "password": "pass12345"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)

    def test_login_by_email(self):
        User.objects.create_user(
            email="a@example.com", password="pass12345", name="А", surname="Б"
        )
        response = self.client.post(
            reverse("users:login"), {"email": "a@example.com", "password": "pass12345"}
        )
        self.assertRedirects(response, reverse("projects:list"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_wrong_password(self):
        User.objects.create_user(
            email="a@example.com", password="pass12345", name="А", surname="Б"
        )
        response = self.client.post(
            reverse("users:login"), {"email": "a@example.com", "password": "nope"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout(self):
        user = User.objects.create_user(
            email="a@example.com", password="x", name="А", surname="Б"
        )
        self.client.force_login(user)
        self.client.get(reverse("users:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="a@example.com", password="pass12345", name="Анна", surname="Иванова"
        )

    def test_profile_is_public(self):
        response = self.client.get(reverse("users:detail", args=[self.user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Анна Иванова")

    def test_edit_profile_requires_login(self):
        response = self.client.get(reverse("users:edit_profile"))
        self.assertEqual(response.status_code, 302)

    def test_edit_profile(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("users:edit_profile"),
            {
                "name": "Анна",
                "surname": "Сидорова",
                "about": "Backend",
                "phone": "89991234567",
                "github_url": "https://github.com/anna",
            },
        )
        self.assertRedirects(response, reverse("users:detail", args=[self.user.id]))
        self.user.refresh_from_db()
        self.assertEqual(self.user.surname, "Сидорова")
        self.assertEqual(self.user.phone, "+79991234567")

    def test_edit_profile_invalid_phone(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("users:edit_profile"),
            {"name": "А", "surname": "Б", "phone": "123"},
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "")

    def test_change_password(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("users:change_password"),
            {
                "old_password": "pass12345",
                "new_password1": "newpass98765",
                "new_password2": "newpass98765",
            },
        )
        self.assertRedirects(response, reverse("users:detail", args=[self.user.id]))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass98765"))


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class UserListTests(TestCase):
    def test_list_paginated_by_12(self):
        for i in range(13):
            User.objects.create_user(
                email=f"u{i}@example.com", password="x", name="Имя", surname=f"Ф{i}"
            )
        response = self.client.get(reverse("users:list"))
        self.assertEqual(len(response.context["page_obj"]), 12)
        response = self.client.get(reverse("users:list"), {"page": 2})
        self.assertEqual(len(response.context["page_obj"]), 1)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AvatarTests(TestCase):
    def test_avatar_generated_on_create(self):
        user = User.objects.create_user(
            email="a@example.com", password="x", name="Анна", surname="Б"
        )
        self.assertTrue(user.avatar)
        self.assertTrue(user.avatar.name.startswith("avatars/avatar_"))
        with Image.open(user.avatar.path) as image:
            self.assertEqual(image.size, (AVATAR_SIZE, AVATAR_SIZE))

    def test_avatar_kept_on_resave(self):
        user = User.objects.create_user(
            email="a@example.com", password="x", name="Анна", surname="Б"
        )
        name = user.avatar.name
        user.about = "Новое описание"
        user.save()
        self.assertEqual(User.objects.get(pk=user.pk).avatar.name, name)
