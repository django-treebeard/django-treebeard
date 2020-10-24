#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
    install_requires=['Django>=2.2'],
    tests_require=['pytest'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.0',
        'Framework :: Django :: 3.1',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries',
        'Topic :: Utilities'])


if __name__ == '__main__':
    setup(**setup_args)
