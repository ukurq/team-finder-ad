import json
from http import HTTPStatus
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from core.services import paginate

from .constants import (
    MAX_SKILL_SUGGESTIONS,
    PROJECTS_PER_PAGE,
    SKILL_NAME_MAX_LENGTH,
)
from .forms import ProjectForm
from .models import Project, Skill


def project_list(request):
    projects = Project.objects.select_related("owner").prefetch_related(
        "participants"
    )
    active_skill = request.GET.get("skill", "").strip()
    if active_skill:
        projects = projects.filter(skills__name=active_skill)

    query_prefix = (
        urlencode({"skill": active_skill}) + "&" if active_skill else ""
    )
    return render(
        request,
        "projects/project_list.html",
        {
            "page_obj": paginate(request, projects, PROJECTS_PER_PAGE),
            "all_skills": Skill.objects.values_list("name", flat=True),
            "active_skill": active_skill,
            "query_prefix": query_prefix,
        },
    )


def project_detail(request, project_id):
    project = get_object_or_404(
        Project.objects.select_related("owner").prefetch_related(
            "skills", "participants"
        ),
        pk=project_id,
    )
    return render(request, "projects/project-details.html", {"project": project})


@login_required
def create_project(request):
    form = ProjectForm(request.POST or None)
    if form.is_valid():
        project = form.save(commit=False)
        project.owner = request.user
        project.save()
        project.participants.add(request.user)
        return redirect("projects:detail", project_id=project.id)
    return render(
        request, "projects/create-project.html", {"form": form, "is_edit": False}
    )


@login_required
def edit_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    if project.owner_id != request.user.id:
        return HttpResponseForbidden("Редактировать проект может только автор.")
    form = ProjectForm(request.POST or None, instance=project)
    if form.is_valid():
        form.save()
        return redirect("projects:detail", project_id=project.id)
    return render(
        request, "projects/create-project.html", {"form": form, "is_edit": True}
    )


def _json_error(message, status):
    return JsonResponse({"status": "error", "message": message}, status=status)


def _owned_project_or_error(request, project_id):
    """Возвращает (проект, None) или (None, JsonResponse с ошибкой)."""
    if not request.user.is_authenticated:
        return None, _json_error("Требуется авторизация", HTTPStatus.UNAUTHORIZED)
    project = get_object_or_404(Project, pk=project_id)
    if project.owner_id != request.user.id:
        return None, _json_error("Недостаточно прав", HTTPStatus.FORBIDDEN)
    return project, None


@require_POST
def complete_project(request, project_id):
    project, error = _owned_project_or_error(request, project_id)
    if error:
        return error
    if project.status != Project.Status.OPEN:
        return _json_error("Проект уже завершён", HTTPStatus.BAD_REQUEST)
    project.status = Project.Status.CLOSED
    project.save(update_fields=["status"])
    return JsonResponse({"status": "ok"})


@require_POST
def toggle_participate(request, project_id):
    if not request.user.is_authenticated:
        return _json_error("Требуется авторизация", HTTPStatus.UNAUTHORIZED)
    project = get_object_or_404(Project, pk=project_id)
    if project.owner_id == request.user.id:
        return _json_error(
            "Автор проекта уже является участником", HTTPStatus.BAD_REQUEST
        )
    if is_participant := project.participants.filter(pk=request.user.pk).exists():
        project.participants.remove(request.user)
    elif project.status != Project.Status.OPEN:
        return _json_error("Проект закрыт", HTTPStatus.BAD_REQUEST)
    else:
        project.participants.add(request.user)
    return JsonResponse({"status": "ok", "participant": not is_participant})


@require_GET
def skill_suggestions(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse([], safe=False)
    skills = Skill.objects.filter(name__istartswith=query)[:MAX_SKILL_SUGGESTIONS]
    return JsonResponse(
        [{"id": skill.id, "name": skill.name} for skill in skills], safe=False
    )


@require_POST
def add_skill(request, project_id):
    project, error = _owned_project_or_error(request, project_id)
    if error:
        return error
    try:
        payload = json.loads(request.body or b"{}")
    except ValueError:
        return _json_error("Некорректный JSON", HTTPStatus.BAD_REQUEST)
    if not isinstance(payload, dict):
        return _json_error("Некорректный JSON", HTTPStatus.BAD_REQUEST)

    skill_id = payload.get("skill_id")
    name = payload.get("name")
    if skill_id is not None:
        try:
            skill = Skill.objects.get(pk=int(skill_id))
        except (Skill.DoesNotExist, TypeError, ValueError):
            return _json_error("Навык не найден", HTTPStatus.NOT_FOUND)
    elif isinstance(name, str) and name.strip():
        name = name.strip()
        if len(name) > SKILL_NAME_MAX_LENGTH:
            return _json_error(
                "Слишком длинное название навыка", HTTPStatus.BAD_REQUEST
            )
        skill = Skill.objects.filter(name__iexact=name).first()
        if skill is None:
            skill = Skill.objects.create(name=name)
    else:
        return _json_error("Укажите навык", HTTPStatus.BAD_REQUEST)

    project.skills.add(skill)
    return JsonResponse({"id": skill.id, "name": skill.name})


@require_POST
def remove_skill(request, project_id, skill_id):
    project, error = _owned_project_or_error(request, project_id)
    if error:
        return error
    skill = get_object_or_404(Skill, pk=skill_id)
    project.skills.remove(skill)
    return JsonResponse({"status": "ok"})
