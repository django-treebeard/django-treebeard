django-treebeard
================

`django-treebeard <https://github.com/django-treebeard/django-treebeard/>`_
is a library that implements efficient tree implementations for the
`Django Web Framework <http://www.djangoproject.com/>`_, originally written by
`Gustavo Picón <https://tabo.pe>`_ and licensed under the Apache License 2.0.

``django-treebeard`` is:

- **Flexible**: Includes 4 different tree implementations with the same API:

  1. :doc:`Adjacency List <al_tree>`
  2. :doc:`Materialized Path <mp_tree>`
  3. :doc:`Nested Sets <ns_tree>`
  4. :doc:`PostgreSQL Ltree <ltree>` (experimental)

- **Fast**: Optimized non-naive tree operations
- **Easy**: Uses Django's :ref:`model-inheritance` to define your own models.
- **Clean**: Testable and well tested code base. Code test coverage is above 96%.


Overview
--------

.. toctree::

   install
   tutorial
   caveats

.. toctree::
   :titlesonly:

   changes

Reference
---------

.. toctree::

   api
   mp_tree
   ns_tree
   al_tree
   ltree
   exceptions

Additional features
-------------------

.. toctree::

   admin
   forms

Development
-----------

.. toctree::

   tests


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
