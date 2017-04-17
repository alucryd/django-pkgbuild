django-pkgbuild
===============

An automated build system for unofficial Arch Linux repositories
----------------------------------------------------------------

Features
~~~~~~~~

- Pulls and scans PKGBUILDs from a git repository
- Manages multiple unofficial Arch Linux repositories
- Leverages Django Q to queue builds and schedule nightly builds
- Can be administrated from the command line or the web interface

Requirements
~~~~~~~~~~~~

- Python 3
- `Django Q <https://django-q.readthedocs.io>`_

Optional:

- `Django Extensions <https://django-extensions.readthedocs.io>`_

Installation
~~~~~~~~~~~~

- Install the ``devtools``, ``pkgbuild-introspection``, ``python-django``, ``python-django-q`` and optionally ``python-django-extensions`` packages

- Add ``django_q`` and ``django_pkgbuild`` to your ``INSTALLED_APPS`` in your project's ``settings.py``. You can enable ``django_extensions`` here as well.

.. code:: python

    INSTALLED_APPS = (
        # other apps
        'django_q',
        'django_pkgbuild',
        'django_extensions'
    )

- Run Django migrations to create the database tables::

    $ python manage.py migrate

Configuration
~~~~~~~~~~~~~

- Define the following in your project's ``settings.py``.

.. code:: python

    PKGBUILD = {
        'packages_root': os.path.expanduser('~/packages'), # required
        'repositories_root': os.path.expanduser('~/public_html'), # required
        'srcdest': '/var/lib/archbuilddest/srcdest', # optional
        'sources_url': 'https://github.com/alucryd/aur-alucryd', # optional
        'bugs_url': 'https://github.com/alucryd/aur-alucryd/issues' # optional
        'static': False, # optional
        'delta': False, # optional
        'debug': False # optional
    }

1. ``packages_root``: Root of the git repository containing your PKGBUILDs
2. ``repositories_root``: Root of the web share containing your unofficial repositories
3. ``srcdest``: Mirrors ``SRCDEST`` in your ``makepkg.conf``
4. ``sources_url``:  Add a ``Sources`` link to the navbar
5. ``bugs_url``:  Add a ``Bugs`` link to the navbar
6. ``static``:  Generate a static ``index.html`` in the repositories root
7. ``delta``:  Generate package deltas
8. ``debug``:  Show devtool's output in the cluster

- Follow Django Q's `configuration guide <https://django-q.readthedocs.io/en/latest/configure.html>`_.

.. hint::

    The ORM broker with a separate SQLite database and a single worker is recommended.

.. important::

    Make sure to set ``timeout`` to ``None`` and ``retry`` to a high value, *e.g.* ``3600``.

- Finally, add django-pkgbuild's URLs in your project's ``urls.py``.

.. code:: python

    urlpatterns = [
        # other urls
        url(r'^', include('django_pkgbuild.urls')),
    ]

Operation
~~~~~~~~~

The following operations are performed in a Django shell, or shell plus if you have Django extensions enabled, which automatically imports all models from installed applications.

~~~~~~~~~~~~~~~~~
Scan all packages
~~~~~~~~~~~~~~~~~

.. code:: python

    from django_pkgbuild.tasks import refresh_packages

    refresh_packages()

.. attention::

    This can take a while if you have a lot of PKGBUILDs to scan.

~~~~~~~~~~~~~~~~
Add a repository
~~~~~~~~~~~~~~~~

.. code:: python

    from django_pkgbuild.models import Architecture, Repository

    repo = Repository.objects.create(name='repository', description='Description', target=Repository.EXTRA, multilib=False)
    repo.architectures.add(Architecture.objects.get(name='x86_64'))

The target and multilib arguments refer to which archbuild will be called. Valid targets are:

- EXTRA
- TESTING
- STAGING

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Add a package to a repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    repo.packages.add(repo.available_packages().get(name='package'))

The ``available_packages()`` function returns a standard QuerySet, thus supports all standard filtering functions.

.. hint::

    Adding a package automatically pulls its dependencies if they have been scanned.

~~~~~~~~~~~~~~
Build packages
~~~~~~~~~~~~~~

.. code:: python

    from django_pkgbuild.tasks import build_packages, build_packages_repo, build_package_repo

    # Build all packages in all repositories
    build_packages(force)
    # Build all packages in a single repository
    build_packages_repo(repository, force)
    # Build a single package in a repository
    build_package(package, repository, force)

* ``package`` and ``repository`` are respectively ``Package`` and ``Repository`` objects.
* ``force`` is a boolean, setting it to ``True`` forces the package to be rebuilt even if it has already been built.

.. hint::

    Unless forced, VCS packages are rebuilt only when there's a new commit upstream. This assumes the repository is named after the package, minus the VCS
    suffix.

~~~~~~~~~~~~~~~~~~~~~~~
Schedule nightly builds
~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from django_q.models import Schedule

    from datetime import datetime

    Schedule.objects.create(name='Nightly Builds',
                            func='django_pkgbuild.tasks.refresh_packages',
                            hook='django_pkgbuild.tasks.refresh_packages_hook',
                            schedule_type=Schedule.DAILY,
                            next_run=datetime.utcnow().replace(hour=0, minute=0, second=0))

This will refresh all PKGBUILDs from the git repository and build all packages that need a rebuild in all repos at midnight UTC everyday.

TODO
~~~~

* Clean up old builds and delete the associated packages from their respective PKGBUILD directory
* Send an email when a build fails
* Write more tests