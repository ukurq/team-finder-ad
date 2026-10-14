from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from core.services import paginate

from .constants import USERS_PER_PAGE
from .forms import LoginForm, ProfileForm, RegisterForm
from .models import User


def register(request):
    if request.user.is_authenticated:
        return redirect("projects:list")
    form = RegisterForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("users:login")
    return render(request, "users/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("projects:list")
    form = LoginForm(request.POST or None, request=request)
    if form.is_valid():
        login(request, form.user)
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}
        ):
            return redirect(next_url)
        return redirect("projects:list")
    return render(request, "users/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("projects:list")


def user_detail(request, user_id):
    profile = get_object_or_404(User, pk=user_id)
    # Шаблон ожидает владельца страницы в переменной ``user``.
    return render(request, "users/user-details.html", {"user": profile})


@login_required
def edit_profile(request):
    form = ProfileForm(
        request.POST or None, request.FILES or None, instance=request.user
    )
    if form.is_valid():
        form.save()
        return redirect("users:detail", user_id=request.user.id)
    return render(request, "users/edit_profile.html", {"form": form})


@login_required
def change_password(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Пароль изменён.")
        return redirect("users:detail", user_id=user.id)
    return render(request, "users/change_password.html", {"form": form})


def user_list(request):
    page_obj = paginate(
        request, User.objects.filter(is_active=True), USERS_PER_PAGE
    )
    return render(
        request,
        "users/participants.html",
        {"page_obj": page_obj, "query_prefix": ""},
    )
