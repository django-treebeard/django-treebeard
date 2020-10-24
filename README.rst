================
django-treebeard
================

**django-treebeard** is a library that implements efficient tree implementations
for the Django Web Framework 1.11 and later.

It is written by Gustavo Picón and licensed under the Apache License 2.0.

Status
------

.. image:: https://readthedocs.org/projects/django-treebeard/badge/?version=latest
    :target: https://readthedocs.org/projects/django-treebeard/

.. image:: https://travis-ci.org/django-treebeard/django-treebeard.svg?branch=master
    :target: https://travis-ci.org/django-treebeard/django-treebeard

.. image:: https://img.shields.io/pypi/v/django-treebeard.svg
    :target: https://pypi.org/project/django-treebeard/

Features
--------
django-treebeard is:

- **Flexible**: Includes 3 different tree implementations with the same API:

  1. Adjacency List
  2. Materialized Path
  3. Nested Sets

- **Fast**: Optimized non-naive tree operations
- **Easy**: Uses Django Model Inheritance with abstract classes to define your own
  models.
- **Clean**: Testable and well tested code base. Code/branch test coverage is above
  96%. Tests are available in Jenkins:

  - Test suite running on different versions of Python and Django:
    https://travis-ci.org/django-treebeard/django-treebeard/

You can find the documentation in

    http://django-treebeard.readthedocs.io/en/latest/

Supported versions
==================

**django-treebeard** officially supports

* Django 2.2 - 3.0
* Python 3.6, 3.7, 3.8
* PostgreSQL, MySQL, SQLite database back-ends.
