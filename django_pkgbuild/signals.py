from django.db.models import Q
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from .tasks import remove_package_from_database
from .models import BasePackage, Package, Repository


@receiver(post_save, sender=Repository)
def create_repo_dir(sender, instance, *args, **kwargs):
    """Automatically create the repository base directory."""
    path = instance.base_directory()
    if not path.is_dir():
        path.mkdir()


@receiver(m2m_changed, sender=Repository.architectures.through)
def create_arch_dir(sender, instance, action, reverse, model, pk_set, using, **kwargs):
    """Automatically create architecture directories inside the base repository."""
    if action == 'post_add':
        for arch in instance.architectures.all():
            path = instance.directory(arch)
            if not path.is_dir():
                path.mkdir()


@receiver(m2m_changed, sender=Repository.architectures.through)
def filter_multilib_arch(sender, instance, action, reverse, model, pk_set, using, **kwargs):
    """Automatically remove architectures other than x86_64 in multilib repositories."""
    if action == 'post_add':
        if instance.multilib:
            instance.architectures.remove(*instance.architectures.exclude(name='x86_64'))


@receiver(m2m_changed, sender=Repository.packages.through)
def add_package_to_repo(sender, instance, action, reverse, model, pk_set, using, **kwargs):
    """Automatically add build dependencies to a repository."""
    if action == 'post_add':
        deps_pk_set = BasePackage.objects.filter(packages__id__in=pk_set).values_list('build_depends', flat=True)
        deps = Package.objects.filter(id__in=deps_pk_set).exclude(Q(id__in=pk_set) |
                                                                  Q(providers__id__in=pk_set) |
                                                                  Q(providers__id__in=deps_pk_set))
        if deps.count():
            instance.packages.add(*deps)


@receiver(m2m_changed, sender=Repository.packages.through)
def remove_package_from_repo(sender, instance, action, reverse, model, pk_set, using, **kwargs):
    """Automatically remove packages from the database when they are removed from the repository."""
    if action == 'post_remove':
        for arch in instance.architectures.all():
            for pkg in Package.objects.filter(id__in=pk_set):
                remove_package_from_database(pkg, arch, instance)
