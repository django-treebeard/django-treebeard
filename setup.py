#!/usr/bin/env python

from distutils.core import setup

version = '1.2a'

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

setup(
    name='django-treebeard',
    version=version,
    url='http://code.google.com/p/django-treebeard/',
    author='Gustavo Picon',
    author_email='tabo@gpicon.org',
    license='Apache License 2.0',
    packages=['treebeard'],
    description='Efficient Materialized Path tree implementation for'
                ' Django 1.0+',
    classifiers=classifiers,
    #long_description=__doc__,
)

