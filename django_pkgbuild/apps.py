from pathlib import Path

from django.apps import AppConfig
from django.conf import settings


class PkgbuildConfig(AppConfig):
    name = 'django_pkgbuild'

    def ready(self):
        import django_pkgbuild.signals

        path = Path(settings.PKGBUILD['repositories_root'])
        if not path.is_dir():
            path.mkdir()
