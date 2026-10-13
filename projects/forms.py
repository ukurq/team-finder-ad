from django import forms

from users.forms import validate_github_url

from .models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("name", "description", "github_url", "status")
        widgets = {"description": forms.Textarea(attrs={"rows": 6})}

    def clean_github_url(self):
        return validate_github_url(self.cleaned_data.get("github_url"))
