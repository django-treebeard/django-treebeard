django-treebeard
================

`django-treebeard <https://tabo.pe/projects/django-treebeard/>`_
is a library that implements efficient tree implementations for the
`Django Web Framework 1.0+ <http://www.djangoproject.com/>`_, written by
`Gustavo Picón <https://tabo.pe>`_ and licensed under the Apache License 2.0.

``django-treebeard`` is:

- **Flexible**: Includes 3 different tree implementations with the same API:

  1. :doc:`Adjacency List <al_tree>`
  2. :doc:`Materialized Path <mp_tree>`
  3. :doc:`Nested Sets <ns_tree>`

- **Fast**: Optimized non-naive tree operations (see :doc:`benchmarks`).
- **Easy**: Uses `Django Model Inheritance with abstract classes`_ 
  to define your own models.
- **Clean**: Testable and well tested code base. Code/branch test coverage
  is above 96%.


Contents
--------

.. toctree::
   :maxdepth: 2

   intro
   api
   mp_tree
   ns_tree
   al_tree
   admin
   forms
   exceptions
   benchmarks
   changes


.. _`Django Model Inheritance with abstract classes`:
   http://docs.djangoproject.com/en/dev/topics/db/models/#abstract-base-classes


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
