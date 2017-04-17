from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='django-pkgbuild',
    version='0.1.0',
    description='Django app to manage unofficial Arch Linux repositories',
    long_description=readme,
    author='Maxime Gauduin',
    author_email='alucryd@archlinux.org',
    url='https://github.com/alucryd/django-pkgbuild',
    license=license,
    packages=find_packages(exclude=('docs')),
    include_package_data=True,
    install_requires=['django-q'],
)
