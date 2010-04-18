#!/usr/bin/env python

import os
from distutils.core import setup

version = '1.6'

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
if not root_dir:
    root_dir = '.'
long_desc = open(root_dir + '/README').read()

setup(
    name='django-treebeard',
    version=version,
    url='http://code.tabo.pe/django-treebeard/',
    author='Gustavo Picon',
    author_email='tabo@tabo.pe',
    license='Apache License 2.0',
    packages=['treebeard', 'treebeard.templatetags'],
    package_dir={'treebeard': 'treebeard'},
    package_data={'treebeard': ['templates/admin/*.html']},
    description='Efficient tree implementations for Django 1.0+',
    classifiers=classifiers,
    long_description=long_desc,
)
