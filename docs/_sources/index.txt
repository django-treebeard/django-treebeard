
:mod:`treebeard` --- Efficient tree model implementations for Django
====================================================================

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

