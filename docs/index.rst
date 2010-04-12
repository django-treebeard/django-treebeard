
:mod:`treebeard` --- Efficient tree model implementations for Django
====================================================================

:synopsys: Efficient Tree implementations for Django 1.0+
:copyright: 2008-2010 by `Gustavo Picon <https://tabo.pe>`_
:license: Apache License 2.0
:version: 1.53a
:url: http://code.tabo.pe/django-treebeard/
:documentation:
   `treebeard-docs
   <http://docs.tabo.pe/django-treebeard/tip/>`_
:examples:
   `treebeard-examples
   <http://django.tabo.pe/tbexample/>`_
   (`source
   <http://code.tabo.pe/django-treebeard/src/tip/tbexample/>`_)
:tests:
   `treebeard-tests
   <http://code.tabo.pe/django-treebeard/src/tip/treebeard/tests.py>`_
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
   2. Add ``'treebeard'`` to the ``INSTALLED_APPS`` section in your
      django settings file.
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
      Also you need to enable `django-core-context-processors-request`_
      in the ``TEMPLATE_CONTEXT_PROCESSORS`` setting in your django
      settings file.


Read the :class:`models.Node` API reference for detailed info.

.. _`treebeard download page`:
   http://code.tabo.pe/django-treebeard/downloads/
.. _`treebeard mercurial repository`:
   http://code.tabo.pe/django-treebeard/src/
.. _`latest treebeard version from PyPi`:
   http://pypi.python.org/pypi/django-treebeard/
.. _`django-core-context-processors-request`:
   http://docs.djangoproject.com/en/dev/ref/templates/api/#django-core-context-processors-request

.. automodule:: treebeard

.. automodule:: treebeard.models

   .. autoclass:: Node
      :show-inheritance:

      .. automethod:: add_root
      .. automethod:: add_child
      .. automethod:: add_sibling
      .. automethod:: delete
      .. automethod:: get_tree
      .. automethod:: get_depth
      .. automethod:: get_ancestors
      .. automethod:: get_children
      .. automethod:: get_children_count
      .. automethod:: get_descendants
      .. automethod:: get_descendant_count
      .. automethod:: get_first_child
      .. automethod:: get_last_child
      .. automethod:: get_first_sibling
      .. automethod:: get_last_sibling
      .. automethod:: get_prev_sibling
      .. automethod:: get_next_sibling
      .. automethod:: get_parent
      .. automethod:: get_root
      .. automethod:: get_siblings
      .. automethod:: is_child_of
      .. automethod:: is_descendant_of
      .. automethod:: is_sibling_of
      .. automethod:: is_root
      .. automethod:: is_leaf
      .. automethod:: move
      .. automethod:: save
      .. automethod:: get_first_root_node
      .. automethod:: get_last_root_node
      .. automethod:: get_root_nodes
      .. automethod:: load_bulk
      .. automethod:: dump_bulk
      .. automethod:: find_problems
      .. automethod:: fix_tree
      .. automethod:: get_descendants_group_count
      .. automethod:: get_annotated_list


:mod:`treebeard.mp_tree` --- Materialized Path tree
===================================================

.. automodule:: treebeard.mp_tree

   .. autoclass:: MP_Node
      :show-inheritance:

      .. automethod:: add_root

      .. automethod:: add_child
      .. automethod:: add_sibling
      .. automethod:: move

      .. automethod:: get_tree

      .. automethod:: find_problems
      .. automethod:: fix_tree


:mod:`treebeard.al_tree` --- Adjacency List tree
================================================

.. automodule:: treebeard.al_tree

   .. autoclass:: AL_Node
      :show-inheritance:

      .. automethod:: get_depth



:mod:`treebeard.ns_tree` --- Nested Sets tree
=============================================

.. automodule:: treebeard.ns_tree

   .. autoclass:: NS_Node
      :show-inheritance:

      .. automethod:: get_tree


:mod:`treebeard.admin` --- Admin
================================

.. automodule:: treebeard.admin

   .. autoclass:: TreeAdmin



:mod:`treebeard.forms` --- Forms
================================

.. automodule:: treebeard.forms

   .. autoclass:: MoveNodeForm



:mod:`treebeard.exceptions` --- Exceptions
==========================================

.. automodule:: treebeard.exceptions
    
    .. autoexception:: InvalidPosition

    .. autoexception:: InvalidMoveToDescendant

    .. autoexception:: PathOverflow

    .. autoexception:: MissingNodeOrderBy


:mod:`tbbench` --- Benchmarks
=============================

.. automodule:: tbbench


Changes in django-treebeard
===========================

.. include:: ../CHANGES


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

