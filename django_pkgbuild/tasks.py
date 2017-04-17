import os
import shutil
import subprocess
from datetime import date
from pathlib import Path

from django.conf import settings
from django.test import Client
from django_q.tasks import async

from .models import Architecture, BasePackage, Build, Package, Repository


def parse_srcinfo(base_package):
    """Generates and parses attributes from a .SRCINFO file."""
    base_package.build_depends.clear()
    base_package.architectures.clear()
    subprocess.run(['mksrcinfo'], cwd=base_package.directory())
    path = base_package.directory() / '.SRCINFO'
    with open(path, 'r') as f:
        # Parse pkgbase info
        line = f.readline()
        item = line.strip().split(' = ')
        base_provides = set()
        while item[0] != 'pkgname':
            if item[0] == 'pkgbase':
                base_package.name = item[1]
            elif item[0] == 'pkgver':
                base_package.version = item[1]
            elif item[0] == 'pkgrel':
                base_package.version = f'{base_package.version}-{item[1]}'
            elif item[0] == 'epoch':
                base_package.version = f'{item[1]}:{base_package.version}'
            elif item[0] == 'arch':
                base_package.architectures.add(Architecture.objects.get_or_create(name=item[1])[0])
            elif item[0] == 'makedepends':
                # Use filter to avoid Package.DoesNotExist
                base_package.build_depends.add(*Package.objects.filter(name=item[1], virtual=False))
            elif item[0] == 'depends':
                # Use filter to avoid Package.DoesNotExist
                base_package.build_depends.add(*Package.objects.filter(name=item[1], virtual=False))
            elif item[0] == 'provides':
                provides = Package.objects.get_or_create(base_package=base_package, name=item[1], virtual=True)[0]
                base_provides.add(provides)
            line = f.readline()
            item = line.strip().split(' = ')
        # Parse pkgname info
        while line:
            if item[0] == 'pkgname':
                pkg = Package.objects.get_or_create(base_package=base_package, name=item[1])[0]
                pkg.provides.clear()
                for provides in base_provides:
                    pkg.provides.add(provides)
            elif item[0] == 'provides':
                provides = Package.objects.get_or_create(base_package=base_package, name=item[1], virtual=True)[0]
                pkg.provides.add(provides)
            line = f.readline()
            item = line.strip().split(' = ')
    base_package.save()
    # Add transitive build_depends
    depends_count = 0
    while depends_count != base_package.build_depends.count():
        depends_count = base_package.build_depends.count()
        for pkg in base_package.build_depends.all():
            base_package.build_depends.add(*pkg.base_package.build_depends.all())
    # Clean up build_depends
    base_package.build_depends.remove(*Package.objects.filter(providers__in=base_package.build_depends.all()))


def add_package_to_database(package, architecture, repository):
    """Add a package to the specified repository database."""
    pkg_dir = package.base_package.directory()
    pkg_filename = package.filename(architecture)
    db_dir = repository.directory(architecture)
    db_filename = repository.filename()
    shutil.copy(pkg_dir / pkg_filename, db_dir)
    if settings.PKGBUILD.get('delta', False):
        subprocess.run(['repo-add', '-d', db_filename, pkg_filename], cwd=db_dir)
    else:
        subprocess.run(['repo-add', db_filename, pkg_filename], cwd=db_dir)


def remove_package_from_database(package, architecture, repository):
    """Remove a package from the specified repository database."""
    pkg_name = package.name
    db_dir = repository.directory(architecture)
    db_filename = repository.filename()
    subprocess.run(['repo-remove', db_filename, pkg_name], cwd=db_dir)


def check_bzr(base_package):
    """Check if a new bazaar commit exists."""
    if 'srcdest' in settings.PKGBUILD:
        bzr_root = Path(settings.PKGBUILD['srcdest']) / base_package.name.rsplit('-', maxsplit=1)[0]
    else:
        bzr_root = base_package.directory() / base_package.name.rsplit('-', maxsplit=1)[0]
    behind = False
    if bzr_root.is_dir():
        old = subprocess.run(['bzr', 'revno'], cwd=bzr_root, stdout=subprocess.PIPE).stdout
        print(old)
        subprocess.run(['bzr', 'pull'], cwd=bzr_root, stdout=subprocess.DEVNULL)
        new = subprocess.run(['bzr', 'revno'], cwd=bzr_root, stdout=subprocess.PIPE).stdout
        print(new)
        behind = new != old
    return behind


def check_git(base_package):
    """Check if a new git commit exists."""
    if 'srcdest' in settings.PKGBUILD:
        git_root = Path(settings.PKGBUILD['srcdest']) / base_package.name.rsplit('-', maxsplit=1)[0]
    else:
        git_root = base_package.directory() / base_package.name.rsplit('-', maxsplit=1)[0]
    behind = False
    if git_root.is_dir():
        old = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], cwd=git_root, stdout=subprocess.PIPE).stdout
        print(old)
        subprocess.run(['git', 'fetch', '--all', '-p'], cwd=git_root, stdout=subprocess.DEVNULL)
        new = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], cwd=git_root, stdout=subprocess.PIPE).stdout
        print(new)
        behind = new != old
    return behind


def check_hg(base_package):
    """Check if a new mercurial commit exists."""
    if 'srcdest' in settings.PKGBUILD:
        hg_root = Path(settings.PKGBUILD['srcdest']) / base_package.name.rsplit('-', maxsplit=1)[0]
    else:
        hg_root = base_package.directory() / base_package.name.rsplit('-', maxsplit=1)[0]
    behind = False
    if hg_root.is_dir():
        old = subprocess.run(['hg', 'id', '-n'], cwd=hg_root, stdout=subprocess.PIPE).stdout
        print(old)
        subprocess.run(['hg', 'pull'], cwd=hg_root, stdout=subprocess.DEVNULL)
        new = subprocess.run(['hg', 'id', '-n'], cwd=hg_root, stdout=subprocess.PIPE).stdout
        print(new)
        behind = new != old
    return behind


def check_svn(base_package):
    """Check if a new subversion commit exists."""
    if 'srcdest' in settings.PKGBUILD:
        svn_root = Path(settings.PKGBUILD['srcdest']) / base_package.name.rsplit('-', maxsplit=1)[0]
    else:
        svn_root = base_package.directory() / base_package.name.rsplit('-', maxsplit=1)[0]
    behind = False
    if svn_root.is_dir():
        old = subprocess.run(['svnversion'], cwd=svn_root, stdout=subprocess.PIPE).stdout
        print(old)
        subprocess.run(['svn', 'up'], cwd=svn_root, stdout=subprocess.DEVNULL)
        new = subprocess.run(['svnversion'], cwd=svn_root, stdout=subprocess.PIPE).stdout
        print(new)
        behind = new != old
    return behind


def build_package(package, architecture, repository, force=False):
    """Build a package for the specified architecture and repository."""
    base_pkg = package.base_package
    any_pkg = base_pkg.architectures.filter(name='any').exists()
    any_arch = Architecture.objects.get_or_create(name='any')[0]
    base_pkg.building = True
    base_pkg.save()
    build = Build.objects.filter(base_package=base_pkg,
                                 version=base_pkg.version,
                                 architecture=any_arch if any_pkg else architecture,
                                 target=repository.target)
    vcs_behind = (base_pkg.name.endswith('-bzr') and check_bzr(base_pkg) or
                  base_pkg.name.endswith('-git') and check_git(base_pkg) or
                  base_pkg.name.endswith('-hg') and check_hg(base_pkg) or
                  base_pkg.name.endswith('-svn') and check_svn(base_pkg))
    print(force)
    print(vcs_behind)
    print(build)
    if force or vcs_behind or not build.exists():
        cmd = ['sudo', repository.chbuild(architecture)]
        if base_pkg.build_depends.count():
            cmd.append('--')
            for pkg in base_pkg.build_depends.all():
                cmd.append('-I')
                cmd.append(f'{pkg.base_package.directory()}/{pkg.filename(architecture)}')
        if settings.PKGBUILD.get('debug', False):
            proc = subprocess.run(cmd, cwd=base_pkg.directory())
        else:
            proc = subprocess.run(cmd, cwd=base_pkg.directory(), stdout=subprocess.DEVNULL)
        if proc.returncode:
            base_pkg.builds = False
        else:
            base_pkg.builds = True
            parse_srcinfo(base_pkg)
            build = Build.objects.get_or_create(base_package=base_pkg,
                                                version=base_pkg.version,
                                                architecture=any_arch if any_pkg else architecture)[0]
            build.target = repository.target
            build.date = date.today()
            build.save()
    base_pkg.building = False
    base_pkg.save()


def build_package_repo(package, repository, force=False):
    """Build a package for the specified repository."""
    name = package.name
    version = package.base_package.version
    for arch in repository.architectures.all():
        task_name = f'{name}-{version}-{repository.target}-{arch}'
        async(build_package, package, arch, repository, force,
              group=repository.name, task_name=task_name, hook=build_package_hook)


def build_packages_repo(repository, force=False):
    """Build all packages from the specified repository."""
    for pkg in sorted(repository.packages.all()):
        for arch in repository.architectures.all():
            task_name = f'{pkg.name}-{pkg.base_package.version}-{repository.target}-{arch}'
            async(build_package, pkg, arch, repository, force,
                  group=repository.name, task_name=task_name, hook=build_package_hook)


def build_packages(force=False):
    """Build packages from all repositories."""
    for repo in Repository.objects.all():
        build_packages_repo(repo, force)


def generate_index():
    """Generate a static index."""
    c = Client()
    with open(Path(settings.PKGBUILD['repositories_root']) / 'index.html', 'wb') as f:
        f.write(c.get('/').content)


def find_pkgbuild(root):
    """Look for a PKGBUILD and return True if the package is official."""
    path = root / 'PKGBUILD'
    # Try unofficial package
    if path.is_file():
        base_pkg = BasePackage.objects.get_or_create(base_directory=path.parent)[0]
        parse_srcinfo(base_pkg)
    else:
        # Try official package
        path = root / 'trunk' / 'PKGBUILD'
        if path.is_file():
            base_pkg = BasePackage.objects.get_or_create(base_directory=path.parent.parent,
                                                         official=True)[0]
            parse_srcinfo(base_pkg)
            return True
    return False


def refresh_packages():
    """Refresh packages from git."""
    root = Path(settings.PKGBUILD['packages_root'])
    git_dir = root / '.git'
    if git_dir.is_dir():
        subprocess.run(['git', 'pull'], cwd=root)
    # Limit depth to 2
    first_level = os.scandir(root)
    # Ignore hidden directories
    for fldir in [d for d in first_level if d.is_dir() and not d.name.startswith('.')]:
        try:
            if find_pkgbuild(root / fldir):
                # Continue if official so trunk doesn't get scanned
                continue
        except PermissionError:
            pass
        second_level = os.scandir(fldir)
        for sldir in [d for d in second_level if d.is_dir() and not d.name.startswith('.')]:
            try:
                find_pkgbuild(root / fldir / sldir)
            except PermissionError:
                pass
    # Second pass to resolve build_depends and delete old packages
    for base_pkg in BasePackage.objects.all():
        path = base_pkg.directory() / 'PKGBUILD'
        if path.is_file():
            parse_srcinfo(base_pkg)
        else:
            base_pkg.delete()


def build_package_hook(task):
    pkg = task.args[0]
    arch = task.args[1]
    repo = task.args[2]
    if pkg.base_package.builds:
        add_package_to_database(pkg, arch, repo)
    if settings.PKGBUILD.get('static', False):
        generate_index()


def refresh_packages_hook(task):
    build_packages()
    if settings.PKGBUILD.get('static', False):
        generate_index()
