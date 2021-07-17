# django-treebeard

**django-treebeard** is a library that implements efficient tree
implementations for the Django Web Framework 2.2 and later.

It is written by Gustavo Picón and licensed under the Apache License
2.0.

## Status

[![Documentation Status](https://readthedocs.org/projects/django-treebeard/badge/?version=latest)](https://django-treebeard.readthedocs.io/en/latest/?badge=latest)
[![Tests](https://github.com/django-treebeard/django-treebeard/workflows/Tests/badge.svg)]()
[![App Veyor](https://ci.appveyor.com/api/projects/status/mwbf062v68lhw05c?svg=true)](https://ci.appveyor.com/project/mvantellingen/django-treebeard)
[![PyPI](https://img.shields.io/pypi/pyversions/django-treebeard.svg)]()
[![PyPI version](https://img.shields.io/pypi/v/django-treebeard.svg)](https://pypi.org/project/django-treebeard/)


## Features

django-treebeard is:

-   **Flexible**: Includes 3 different tree implementations with the
    same API:
    1.  Adjacency List
    2.  Materialized Path
    3.  Nested Sets
-   **Fast**: Optimized non-naive tree operations
-   **Easy**: Uses Django Model Inheritance with abstract classes to
    define your own models.
-   **Clean**: Testable and well tested code base. Code/branch test
    coverage is above 96%. Test suite running on different versions of
    Python and Django:
    <https://travis-ci.org/django-treebeard/django-treebeard/>

You can find the documentation in

> <http://django-treebeard.readthedocs.io/en/latest/>

### Supported versions

**django-treebeard** officially supports

-   Django 2.2 - 3.2
-   Python 3.6, 3.7, 3.8, 3.9
-   PostgreSQL, MySQL, MSSQL, SQLite database back-ends.
