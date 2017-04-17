from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .models import Architecture, Package, Repository
from .tasks import build_package_repo, build_packages_repo


def index(request):
    repositories = Repository.objects.all()
    architectures = Architecture.objects.exclude(name='any')
    targets = Repository.TARGET_CHOICES
    return render(request, 'index.html', {'repositories': repositories,
                                          'architectures': architectures,
                                          'targets': targets,
                                          'sources_url': settings.PKGBUILD.get('sources_url', ''),
                                          'bugs_url': settings.PKGBUILD.get('bugs_url', ''),
                                          'static': settings.PKGBUILD.get('static', False)})


@require_POST
def login_view(request):
    user = authenticate(username=request.POST['username'], password=request.POST['password'])
    if user is not None:
        login(request, user)
    return redirect('index')


@require_POST
def logout_view(request):
    logout(request)
    return redirect('index')


@require_POST
@login_required
def add_repository(request):
    repo = Repository()
    repo.name = request.POST['name']
    repo.target = request.POST['target']
    repo.multilib = 'multilib' in request.POST
    repo.description = request.POST['description']
    repo.save()
    for arch in Architecture.objects.exclude(name='any'):
        if f'architecture_{arch.name}' in request.POST:
            repo.architectures.add(arch)
    return redirect('index')


@require_POST
@login_required
def modify_repository(request):
    repo = Repository.objects.get(id=request.POST['id'])
    repo.name = request.POST['name']
    repo.target = request.POST['target']
    repo.multilib = 'multilib' in request.POST
    repo.description = request.POST['description']
    repo.save()
    repo.architectures.clear()
    for arch in Architecture.objects.exclude(name='any'):
        if f'architecture_{arch.name}' in request.POST:
            repo.architectures.add(arch)
    return redirect('index')


@require_POST
@login_required
def build(request):
    pkg = Package.objects.get(id=request.POST['package_id'])
    repo = Repository.objects.get(id=request.POST['repository_id'])
    build_package_repo(pkg, repo, True)
    return redirect('index')


@require_POST
@login_required
def build_all(request):
    repo = Repository.objects.get(id=request.POST['repository_id'])
    build_packages_repo(repo, True)
    return redirect('index')


@require_POST
@login_required
def add(request):
    pkg = Package.objects.get(id=request.POST['package_id'])
    repo = Repository.objects.get(id=request.POST['repository_id'])
    repo.packages.add(pkg)
    return redirect('index')


@require_POST
@login_required
def remove(request):
    pkg = Package.objects.get(id=request.POST['package_id'])
    repo = Repository.objects.get(id=request.POST['repository_id'])
    repo.packages.remove(pkg)
    return redirect('index')
