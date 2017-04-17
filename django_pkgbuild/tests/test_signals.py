import os
import shutil
from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings

from django_pkgbuild.models import Architecture, Repository, Package


@override_settings(PKGBUILD={
    'packages_root': os.getcwd() + '/django_pkgbuild/tests/packages',
    'repositories_root': os.getcwd() + '/django_pkgbuild/tests/repositories',
    'static': True,
    'delta': True
})
class SignalsTestCase(TestCase):
    fixtures = ['test-architectures', 'test-packages']

    def setUp(self):
        self.repos_path = Path(settings.PKGBUILD["repositories_root"])
        if self.repos_path.exists():
            shutil.rmtree(self.repos_path)
        self.repos_path.mkdir(parents=True)

        self.i686_arch = Architecture.objects.get(name='i686')
        self.x86_64_arch = Architecture.objects.get(name='x86_64')

        self.repo = Repository.objects.create(name='test', description='test', target=Repository.EXTRA)
        self.repo.architectures.add(self.i686_arch)
        self.repo.architectures.add(self.x86_64_arch)

    def test_create_repo_and_arch_dirs(self):
        i686_path = self.repos_path / self.repo.name / self.i686_arch.name
        x86_64_path = self.repos_path / self.repo.name / self.x86_64_arch.name

        self.assertTrue(i686_path.is_dir())
        self.assertTrue(x86_64_path.is_dir())

    def test_add_build_depends(self):
        test_pkg = Package.objects.get(name='test-package')
        test_depends_pkg = Package.objects.get(name='test-depends-package')

        self.assertIn(test_pkg, self.repo.available_packages())
        self.assertIn(test_depends_pkg, self.repo.available_packages())

        self.repo.packages.add(test_depends_pkg)

        self.assertIn(test_pkg, self.repo.packages.all())
        self.assertIn(test_depends_pkg, self.repo.packages.all())

    def tearDown(self):
        shutil.rmtree(self.repos_path)
