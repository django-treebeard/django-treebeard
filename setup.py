#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
from setuptools import setup, find_packages
from treebeard import __version__
import codecs


def root_dir():
    try:
        return os.path.dirname(__file__)
    except NameError:
        return '.'


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
    long_description=codecs.open(os.path.join(root_dir(), 'README.rst'), encoding='utf-8').read(),
    install_requires=['Django>=1.8'],
    tests_require=['pytest'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.8',
        'Framework :: Django :: 1.9',
        'Framework :: Django :: 1.10',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries',
        'Topic :: Utilities'])


if __name__ == '__main__':
    setup(**setup_args)
