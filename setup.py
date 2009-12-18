#!/usr/bin/env python

import os
from distutils.command.install import INSTALL_SCHEMES
from distutils.core import setup

version = '1.52'

classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python",
    "Operating System :: OS Independent",
    "Topic :: Software Development :: Libraries",
    "Topic :: Utilities",
    "Environment :: Web Environment",
    "Framework :: Django",
]

root_dir = os.path.dirname(__file__)
long_desc = open((root_dir if root_dir else '.')+'/README').read()

setup(
    name='django-treebeard',
    version=version,
    url='http://code.tabo.pe/django-treebeard/',
    author='Gustavo Picon',
    author_email='tabo@tabo.pe',
    license='Apache License 2.0',
    packages = ['treebeard', 'treebeard.templatetags'],
    package_dir={'treebeard': 'treebeard'},
    package_data={'treebeard': ['templates/admin/*.html']},
    description='Efficient Materialized Path tree implementation for'
                ' Django 1.0+',
    classifiers=classifiers,
    long_description=long_desc,
)

