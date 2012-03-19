#!/usr/bin/env python

import os
from setuptools import setup
from setuptools.command.test import test


def root_dir():
    rd = os.path.dirname(__file__)
    if rd:
        return rd
    return '.'


class pytest_test(test):
    def finalize_options(self):
        test.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        pytest.main([])


setup_args = dict(
    name='django-treebeard',
    version='1.62a',
    url='https://tabo.pe/projects/django-treebeard/',
    author='Gustavo Picon',
    author_email='tabo@tabo.pe',
    license='Apache License 2.0',
    packages=['treebeard', 'treebeard.templatetags'],
    package_dir={'treebeard': 'treebeard'},
    package_data={'treebeard': ['templates/admin/*.html']},
    description='Efficient tree implementations for Django 1.0+',
    long_description=open(root_dir() + '/README').read(),
    cmdclass={'test': pytest_test},
    install_requires=['Django>=1.2'],
    tests_require=['pytest'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries',
        'Topic :: Utilities',
        'Environment :: Web Environment',
        'Framework :: Django'])

if __name__ == '__main__':
    setup(**setup_args)
