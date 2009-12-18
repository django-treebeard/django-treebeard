# -*- coding: utf-8 -*-
"""

    treebeard
    ---------

    :synopsys: Efficient Tree implementations for Django 1.0+
    :copyright: 2008-2009 by `Gustavo Picon <http://tabo.pe>`_
    :license: Apache License 2.0
    :version: 1.52
    :url: http://code.tabo.pe/django-treebeard/
    :documentation:
       `treebeard-docs
       <http://docs.tabo.pe/django-treebeard/1.52/>`_
    :examples:
       `treebeard-examples
       <http://django.tabo.pe/tbexample/>`_
       (`source
       <http://code.tabo.pe/django-treebeard/src/1.52/tbexample/>`_)
    :tests:
       `treebeard-tests
       <http://code.tabo.pe/django-treebeard/src/1.52/treebeard/tests.py>`_
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

       1. Run :command:`easy_install django-treebeard` to install the
          `latest treebeard version from PyPi`_
          1.1. If you don't like easy_install, download a release from the
          `treebeard download page`_ or get a development version
          from the `treebeard mercurial repository`_ and run
          :command:`python setup.py install`
       2. Add ``'treebeard'`` to the ``INSTALLED_APPS`` section in your django
          settings file.
       3. Create a new model that inherits from one of ``django-treebeard``'s
          abstract tree models: :class:`mp_tree.MP_Node` (materialized path),
          :class:`ns_tree.NS_Node` (nested sets) or :class:`al_tree.AL_Node`
          (adjacency list).
       4. Run :command:`python manage.py syncdb`
       5. (Optional) If you are going to use the :class:`admin.TreeAdmin`
          class for the django admin, you should install treebeard as a
          directory instead of an egg:
          :command:`easy_install --always-unzip django-treebeard`.
          If you install treebeard as an egg, you'll need to enable
          ``django.template.loaders.eggs.load_template_source`` in the
          ``TEMPLATE_LOADERS`` setting in your django settings file.
          Either way, you need to add the path (filesystem or python
          namespace) to treebeard's templates in ``TEMPLATE_DIRS``.


    Read the :class:`models.Node` API reference for detailed info.

    .. _`treebeard download page`:
       http://code.tabo.pe/django-treebeard/downloads/
    .. _`treebeard mercurial repository`:
       http://code.tabo.pe/django-treebeard/src/
    .. _`latest treebeard version from PyPi`:
       http://pypi.python.org/pypi/django-treebeard/

"""

__version__ = '1.52'

