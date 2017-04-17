import getpass
from pathlib import Path

from django.conf import settings
from django.db import models
from django.db.models import Q


class Architecture(models.Model):
    name = models.CharField(max_length=8, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Package(models.Model):
    base_package = models.ForeignKey('BasePackage', models.CASCADE, related_name='packages')
    name = models.CharField(max_length=32)
    provides = models.ManyToManyField('self', related_name='providers', symmetrical=False)
    virtual = models.BooleanField(default=False)

    def filename(self, architecture):
        """Returns the package filename for the specified architecture."""
        arch = architecture.name if architecture in self.base_package.architectures.all() else 'any'
        return f'{self.name}-{self.base_package.version}-{arch}.pkg.tar.xz'

    def __eq__(self, other):
        """Returns True if both have the same name."""
        return self.name == other.name

    def __lt__(self, other):
        """Returns True if other depends on self."""
        return self in other.base_package.build_depends.all()

    def __gt__(self, other):
        """Returns True if self depends on other."""
        return self not in other.base_package.build_depends.all()

    def __str__(self):
        return f'{self.name} ({self.base_package.name})' if self.name != self.base_package.name else self.name

    class Meta:
        ordering = ['name']


class Build(models.Model):
    base_package = models.ForeignKey('BasePackage', models.CASCADE, related_name='build_history')
    version = models.CharField(max_length=32)
    architecture = models.ForeignKey(Architecture)
    target = models.CharField(max_length=32, null=True)
    date = models.DateField(null=True)

    def __str__(self):
        return f'{self.base_package.name}-{self.version}-{self.target}-{self.architecture.name}'


class BasePackage(models.Model):
    base_directory = models.FilePathField(path=settings.PKGBUILD['packages_root'], recursive=True, allow_files=False,
                                          allow_folders=True, max_length=128, unique=True)
    name = models.CharField(max_length=32, null=True)
    version = models.CharField(max_length=32, null=True)
    architectures = models.ManyToManyField(Architecture, symmetrical=False)
    build_depends = models.ManyToManyField(Package, related_name='reverse_build_depends', symmetrical=False, blank=True)
    building = models.BooleanField(default=False)
    builds = models.BooleanField(default=False)
    official = models.BooleanField(default=False)

    def directory(self):
        return Path(self.base_directory) / 'trunk' if self.official else Path(self.base_directory)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Repository(models.Model):
    EXTRA = 'extra'
    TESTING = 'testing'
    STAGING = 'stg'
    TARGET_CHOICES = (
        (EXTRA, 'extra'),
        (TESTING, 'testing'),
        (STAGING, 'staging'),
    )

    name = models.CharField(max_length=32, unique=True)
    description = models.CharField(max_length=256)
    architectures = models.ManyToManyField(Architecture)
    target = models.CharField(max_length=8, choices=TARGET_CHOICES, null=True)
    multilib = models.BooleanField(default=False)
    packages = models.ManyToManyField(Package, blank=True)

    def server(self):
        """Returns the server string for makepkg.conf."""
        return f'http://pkgbuild.com/~{getpass.getuser()}/$repo/$arch'

    def base_directory(self):
        """Returns the base repository path."""
        return Path(settings.PKGBUILD['repositories_root']) / self.name

    def directory(self, architecture):
        """Returns the repository path for the specified architecture."""
        return self.base_directory() / architecture.name

    def filename(self):
        """Returns the database filename."""
        return f'{self.name}.db.tar.gz'

    def chbuild(self, architecture):
        """Returns the full target."""
        return f'multilib-{self.target}-build' if self.multilib else f'{self.target}-{architecture.name}-build'

    def available_packages(self):
        return Package.objects.filter(
            Q(base_package__architectures__in=self.architectures.all()) |
            Q(base_package__architectures__name='any'),
            virtual=False
        ).exclude(id__in=self.packages.values_list('id', flat=True)).distinct()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Repositories'
