from django import forms
from django.contrib import admin
from django.db.models import Q

from .models import Architecture, BasePackage, Package, Build, Repository


class RepositoryForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        """Hide provides and filter packages per the repository architectures."""
        super(RepositoryForm, self).__init__(*args, **kwargs)
        self.fields['architectures'].queryset = Architecture.objects.exclude(name='any')
        if self.instance.id is None:
            self.fields['packages'].queryset = Package.objects.none()
        else:
            self.fields['packages'].queryset = Package.objects.filter(
                Q(base_package__architectures__in=self.instance.architectures.all()) |
                Q(base_package__architectures__name='any'),
                virtual=False
            ).distinct()


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    form = RepositoryForm

admin.site.register(Architecture)
admin.site.register(BasePackage)
admin.site.register(Package)
admin.site.register(Build)
