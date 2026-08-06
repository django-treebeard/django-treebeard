# django-treebeard

django-treebeard is a library that implements efficient tree implementations for the Django Web Framework.

It was written by Gustavo Picón and licensed under the Apache License 2.0.

## Status

[![Documentation Status](https://readthedocs.org/projects/django-treebeard/badge/?version=latest)](https://django-treebeard.readthedocs.io/en/latest/?badge=latest)
[![Tests](https://github.com/django-treebeard/django-treebeard/actions/workflows/test.yml/badge.svg)]()
[![PyPI](https://img.shields.io/pypi/pyversions/django-treebeard.svg)]()
![PyPI - Django Version](https://img.shields.io/pypi/frameworkversions/django/django-treebeard.svg)
[![PyPI version](https://img.shields.io/pypi/v/django-treebeard.svg)](https://pypi.org/project/django-treebeard/)


## Features

django-treebeard is:

-   **Flexible**: Includes 3 different tree implementations with the
    same API:
    1.  Adjacency List
    2.  Materialized Path
    3.  Nested Sets
    4.  PostgreSQL ltree (experimental)
-   **Fast**: Optimized non-naive tree operations
-   **Easy**: Uses Django Model Inheritance with abstract classes to
    define your own models.
-   **Clean**: Testable and well tested code base. Code/branch test
    coverage is above 96%.

You can find the documentation at <https://django-treebeard.readthedocs.io/en/latest/>.

## System requirements

django-treebeard officially supports:

-   Django 5.2 and higher
-   Python 3.10 and higher
-   PostgreSQL, MySQL, MSSQL, SQLite database back-ends.

## Supported versions

The following versions of Treebeard are actively maintained:

- v5.x: security and bugfix support until April 2030.
- v7.x: current stable release.

Version 6 of Treebeard featured an API change that moved much of Treebeard's API
from the model class to the model manager. To mitigate the upgrade burden, v5.x
of Treebeard will receive security and bugfix releases until April 2030.