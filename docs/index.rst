
:mod:`treebeard` --- Efficient Materialized Path tree implementation for Django
===============================================================================

.. automodule:: treebeard

   .. autoclass:: Node
      :show-inheritance:

      .. automethod:: add_root
      .. automethod:: get_first_root_node
      .. automethod:: get_last_root_node
      .. automethod:: get_root_nodes
      .. automethod:: load_bulk
      .. automethod:: dump_bulk
      .. automethod:: find_problems
      .. automethod:: fix_tree

      .. automethod:: add_child
      .. automethod:: add_sibling
      .. automethod:: delete
      .. automethod:: get_ancestors
      .. automethod:: get_children
      .. automethod:: get_descendants
      .. automethod:: get_first_child
      .. automethod:: get_first_sibling
      .. automethod:: get_next_sibling
      .. automethod:: get_parent
      .. automethod:: get_prev_sibling
      .. automethod:: get_root
      .. automethod:: get_siblings
      .. automethod:: is_child_of
      .. automethod:: is_descendant_of
      .. automethod:: is_sibling_of
      .. automethod:: move
      .. automethod:: save

   .. autoexception:: InvalidPosition

   .. autoexception:: InvalidMoveToDescendant
   
   .. autoexception:: PathOverflow

   .. autoexception:: MissingNodeOrderBy


:mod:`treebeard.mp_tree` --- Efficient Materialized Path tree implementation for Django
=======================================================================================

.. automodule:: treebeard.mp_tree

   .. autoclass:: MPNode
      :show-inheritance:

      .. automethod:: add_root
      .. automethod:: get_first_root_node
      .. automethod:: get_last_root_node
      .. automethod:: get_root_nodes
      .. automethod:: load_bulk
      .. automethod:: dump_bulk
      .. automethod:: find_problems
      .. automethod:: fix_tree

      .. automethod:: add_child
      .. automethod:: add_sibling
      .. automethod:: delete
      .. automethod:: get_ancestors
      .. automethod:: get_children
      .. automethod:: get_descendants
      .. automethod:: get_first_child
      .. automethod:: get_first_sibling
      .. automethod:: get_next_sibling
      .. automethod:: get_parent
      .. automethod:: get_prev_sibling
      .. automethod:: get_root
      .. automethod:: get_siblings
      .. automethod:: is_child_of
      .. automethod:: is_descendant_of
      .. automethod:: is_sibling_of
      .. automethod:: move
      .. automethod:: save


:mod:`tbbench` --- tree
=======================

.. automodule:: tbbench

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

