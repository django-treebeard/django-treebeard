#!/usr/bin/env python
# -*- coding: utf-8 -*-


from distutils.core import setup

setup(
    name = 'django-treebeard',
    version = '1.2a',
    url = 'http://code.google.com/p/django-treebeard/',
    author = 'Gustavo Picon',
    author_email = 'tabo@gpicon.org',
    license = 'Apache License 2.0',
    packages = ['treebeard'],
    description = 'Efficient Materialized Path tree implementation for'
                  ' Django 1.0+',
)

