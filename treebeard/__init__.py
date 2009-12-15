# -*- coding: utf-8 -*-
"""

    treebeard
    ---------

    :synopsys: Efficient Tree implementations for Django 1.0+
    :copyright: 2008-2009 by `Gustavo Picon <http://tabo.pe>`_
    :license: Apache License 2.0
    :version: 1.5
    :url: http://code.tabo.pe/django-treebeard/
    :documentation:
       `treebeard-docs
       <http://docs.tabo.pe/django-treebeard/1.5/>`_
    :examples:
       `treebeard-examples
       <http://django.tabo.pe/tbexample/>`_
       (`source
       <http://code.tabo.pe/django-treebeard/src/1.5/tbexample/>`_)
    :tests:
       `treebeard-tests
       <http://code.tabo.pe/django-treebeard/src/1.5/treebeard/tests.py>`_
    :benchmarks: `treebeard-benchmarks <#module-tbbench>`_

    ``django-treebeard`` is a library that implements efficient tree
    implementations for the `Django Web Framework 1.0+
    <http://www.djangoproject.com/>`_. It includes 3 different tree
    implementations: Adjacency List, Materialized Path and Nested Sets. Each
    one has it's own strength and weaknesses (see
    `Benchmarks <#module-tbbench>`_) but share the same
    API, so it's easy to switch between implementations.

    ``django-treebeard`` uses `Django Model Inheritance with abstract classes`_
    to let you define your own models. To use ``django-treebeard``:

       1. Download a release from the `treebeard download page`_ or get a
          development version from the `treebeard mercurial repository`_.
       2. Run :command:`python setup.py install`
       3. Add ``'treebeard'`` to the ``INSTALLED_APPS`` section in your django
          settings file.
       4. Create a new model that inherits from one of ``django-treebeard``'s
          abstract tree models: :class:`mp_tree.MP_Node` (materialized path),
          :class:`ns_tree.NS_Node` (nested sets) or :class:`al_tree.AL_Node`
          (adjacency list).
       5. Run :command:`python manage.py syncdb`


    Read the :class:`models.Node` API reference for detailed info.

    .. _`treebeard download page`:
       http://code.tabo.pe/django-treebeard/downloads/
    .. _`treebeard mercurial repository`:
       http://code.tabo.pe/django-treebeard/src/

"""

__version__ = '1.5'

