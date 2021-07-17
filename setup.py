#!/usr/bin/env python
from setuptools import setup, find_packages
from treebeard import __version__


with open('README.md') as fh:
    long_description = fh.read()


setup_args = dict(
    name='django-treebeard',
    version=__version__,
    url='https://github.com/django-treebeard/django-treebeard/',
    author='Gustavo Picon',
    author_email='tabo@tabo.pe',
    license='Apache License 2.0',
    packages=find_packages(exclude=['docs']),
    include_package_data=True,
    description='Efficient tree implementations for Django',
    long_description=long_description,
    long_description_content_type='text/markdown',
    python_requires='>=3.6',
    install_requires=['Django>=2.2'],
    tests_require=[
        'pytest-django>=4.0,<5.0',

        # adds cwd() to the pythonpath, so we can run tests without
        # installing treebeard
        'pytest-pythonpath>=0.7,<1.0'
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.0',
        'Framework :: Django :: 3.1',
        'Framework :: Django :: 3.2',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries',
        'Topic :: Utilities'])


if __name__ == '__main__':
    setup(**setup_args)
