#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
from distutils.core import setup

treebeard = __import__('treebeard')
version_tuple = treebeard.VERSION
version = "%d.%d" % version_tuple[:2]
if version_tuple[2] is not None:
    svnf = os.path.join(os.path.dirname(os.path.abspath(treebeard.__file__)),
                        '.svn/entries')
    gotdir = False
    version = '%s_%s' % (version, str(version_tuple[2]))
    if os.path.isfile(svnf):
        for ln in open(svnf):
            ln = ln.rstrip()
            if gotdir:
                version = '%s_rev%s' % (version, ln.replace(' ', ''))
                break
            if ln == 'dir':
                gotdir = True

setup(
    name = 'django-treebeard',
    version = version,
    url = 'http://code.google.com/p/django-treebeard/',
    author = 'Gustavo Picon',
    author_email = 'gpicon@gmail.com',
    license = 'Apache License 2.0',
    packages = ['treebeard'],
    description = 'Efficient Materialized Path tree implementation for'
                  ' Django 1.0+',
)

