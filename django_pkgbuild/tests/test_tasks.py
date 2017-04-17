import os
import shutil
from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings

from django_pkgbuild.models import Architecture, Package, Repository
from django_pkgbuild.tasks import refresh_packages


@override_settings(PKGBUILD={
    'packages_root': os.getcwd() + '/django_pkgbuild/tests/packages',
    'repositories_root': os.getcwd() + '/django_pkgbuild/tests/repositories',
    'static': True,
    'delta': True
})
class TasksTestCase(TestCase):
    fixtures = ['test-architectures']

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

    def test_refresh_packages(self):
        refresh_packages()

        # Test Package
        test_pkg = Package.objects.get(name='test-package')
        self.assertEqual(test_pkg.provides.count(), 0)
        self.assertFalse(test_pkg.virtual)

        test_base_pkg = test_pkg.base_package
        self.assertEqual(test_base_pkg.name, 'test-package')
        self.assertEqual(test_base_pkg.version, '1:1.0.0-1')
        self.assertEqual(test_base_pkg.architectures.count(), 2)
        self.assertIn(self.i686_arch, test_base_pkg.architectures.all())
        self.assertIn(self.x86_64_arch, test_base_pkg.architectures.all())
        self.assertEqual(test_base_pkg.build_depends.count(), 0)
        self.assertFalse(test_base_pkg.building)
        self.assertFalse(test_base_pkg.builds)
        self.assertFalse(test_base_pkg.official)

        # Test Official Package
        test_official_pkg = Package.objects.get(name='test-official-package')
        self.assertEqual(test_official_pkg.provides.count(), 0)
        self.assertFalse(test_official_pkg.virtual)

        test_official_base_pkg = test_official_pkg.base_package
        self.assertEqual(test_official_base_pkg.name, 'test-official-package')
        self.assertEqual(test_official_base_pkg.version, '1.1.0-3')
        self.assertEqual(test_official_base_pkg.architectures.count(), 2)
        self.assertIn(self.i686_arch, test_official_base_pkg.architectures.all())
        self.assertIn(self.x86_64_arch, test_official_base_pkg.architectures.all())
        self.assertEqual(test_official_base_pkg.build_depends.count(), 0)
        self.assertFalse(test_official_base_pkg.building)
        self.assertFalse(test_official_base_pkg.builds)
        self.assertTrue(test_official_base_pkg.official)

        # Test Depends Package
        test_depends_pkg = Package.objects.get(name='test-depends-package')
        self.assertEqual(test_depends_pkg.provides.count(), 0)
        self.assertFalse(test_depends_pkg.virtual)

        test_depends_base_pkg = test_depends_pkg.base_package
        self.assertEqual(test_depends_base_pkg.name, 'test-depends-package')
        self.assertEqual(test_depends_base_pkg.version, '1.0.1-1')
        self.assertEqual(test_depends_base_pkg.architectures.count(), 2)
        self.assertIn(self.i686_arch, test_depends_base_pkg.architectures.all())
        self.assertIn(self.x86_64_arch, test_depends_base_pkg.architectures.all())
        self.assertEqual(test_depends_base_pkg.build_depends.count(), 1)
        self.assertIn(test_pkg, test_depends_base_pkg.build_depends.all())
        self.assertFalse(test_depends_base_pkg.building)
        self.assertFalse(test_depends_base_pkg.builds)
        self.assertFalse(test_depends_base_pkg.official)

        # Test Provides Package
        test_virtual_pkg = Package.objects.get(name='test-virtual-package')
        self.assertEqual(test_virtual_pkg.provides.count(), 0)
        self.assertTrue(test_virtual_pkg.virtual)

        test_provides_pkg = Package.objects.get(name='test-provides-package')
        self.assertEqual(test_provides_pkg.provides.count(), 1)
        self.assertIn(test_virtual_pkg, test_provides_pkg.provides.all())
        self.assertFalse(test_provides_pkg.virtual)

        self.assertEqual(test_virtual_pkg.base_package, test_provides_pkg.base_package)

        test_provides_base_pkg = test_provides_pkg.base_package
        self.assertEqual(test_provides_base_pkg.name, 'test-provides-package')
        self.assertEqual(test_provides_base_pkg.version, '1.3.2-2')
        self.assertEqual(test_provides_base_pkg.architectures.count(), 1)
        self.assertNotIn(self.i686_arch, test_provides_base_pkg.architectures.all())
        self.assertIn(self.x86_64_arch, test_provides_base_pkg.architectures.all())
        self.assertEqual(test_provides_base_pkg.build_depends.count(), 0)
        self.assertFalse(test_provides_base_pkg.building)
        self.assertFalse(test_provides_base_pkg.builds)
        self.assertFalse(test_provides_base_pkg.official)

        # Test Split Package
        test_first_pkg = Package.objects.get(name='test-first-package')
        self.assertEqual(test_first_pkg.provides.count(), 0)
        self.assertFalse(test_first_pkg.virtual)

        test_second_pkg = Package.objects.get(name='test-second-package')
        self.assertEqual(test_second_pkg.provides.count(), 0)
        self.assertFalse(test_second_pkg.virtual)

        self.assertEqual(test_first_pkg.base_package, test_second_pkg.base_package)

        test_split_base_pkg = test_first_pkg.base_package
        self.assertEqual(test_split_base_pkg.name, 'test-split-package')
        self.assertEqual(test_split_base_pkg.version, '2.1.0-2')
        self.assertEqual(test_split_base_pkg.architectures.count(), 1)
        self.assertNotIn(self.i686_arch, test_split_base_pkg.architectures.all())
        self.assertIn(self.x86_64_arch, test_split_base_pkg.architectures.all())
        self.assertEqual(test_split_base_pkg.build_depends.count(), 0)
        self.assertFalse(test_split_base_pkg.building)
        self.assertFalse(test_split_base_pkg.builds)
        self.assertFalse(test_split_base_pkg.official)

    def tearDown(self):
        shutil.rmtree(self.repos_path)
