import re
from urllib.parse import urlparse

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

PHONE_RE = re.compile(r"^(?:\+7|8)\d{10}$")


def normalize_phone(value):
    value = re.sub(r"[\s\-()]", "", value or "")
    if not value:
        return ""
    if not PHONE_RE.match(value):
        raise forms.ValidationError(
            "Телефон должен быть в формате 8XXXXXXXXXX или +7XXXXXXXXXX."
        )
    if value.startswith("8"):
        value = "+7" + value[1:]
    return value


def validate_github_url(value):
    if not value:
        return value
    host = (urlparse(value).hostname or "").lower()
    if host not in ("github.com", "www.github.com"):
        raise forms.ValidationError("Укажите ссылку на GitHub (github.com).")
    return value


class RegisterForm(forms.ModelForm):
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("name", "surname", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Пользователь с таким email уже зарегистрирован."
            )
        return email

    def _post_clean(self):
        super()._post_clean()
        password = self.cleaned_data.get("password")
        if password:
            try:
                validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error("password", error)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email")
        password = cleaned.get("password")
        if email and password:
            self.user = authenticate(
                self.request, username=email.strip().lower(), password=password
            )
            if self.user is None:
                raise forms.ValidationError("Неверный email или пароль.")
        return cleaned


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("name", "surname", "avatar", "about", "phone", "github_url")
        widgets = {"about": forms.Textarea(attrs={"rows": 4})}

    def clean_phone(self):
        return normalize_phone(self.cleaned_data.get("phone"))

    def clean_github_url(self):
        return validate_github_url(self.cleaned_data.get("github_url"))
