Nested Sets trees
=================

.. module:: treebeard.ns_tree

An implementation of Nested Sets trees for Django, as described by
`Joe Celko`_ in `Trees and Hierarchies in SQL for Smarties`_.

Nested sets have very efficient reads at the cost of high maintenance on
write/delete operations.

.. warning::

   As with all tree implementations, please be aware of the
   :doc:`caveats`.


.. inheritance-diagram:: NS_Node
.. autoclass:: NS_Node
  :show-inheritance:

  .. warning::

     If you need to define your own
     :py:class:`~django.db.models.Manager` class,
     you'll need to subclass
     :py:class:`~NS_NodeManager`.

     Also, if in your manager you need to change the default
     queryset handler, you'll need to subclass
     :py:class:`~NS_NodeQuerySet`.


  .. attribute:: node_order_by

     Attribute: a list of model fields that will be used for node
     ordering. When enabled, all tree operations will assume this ordering.

     Example:

     .. code-block:: python

        node_order_by = ['field1', 'field2', 'field3']

     .. warning::
         
         ``node_order_by`` values are used to determine correct node ordering *before*
         an object is inserted/moved. This means any fields that
         are auto-populated at a database level, e.g., ``AutoField()``, or ``DateTimeField(auto_now=True)``
         will be ignored for the purpose of ordering if a value isn't provided manually.


  .. attribute:: depth

     ``PositiveIntegerField``, depth of a node in the tree. A root node
     has a depth of *1*.

  .. attribute:: lft

     ``PositiveIntegerField``

  .. attribute:: rgt

     ``PositiveIntegerField``

  .. attribute:: tree_id

     ``PositiveIntegerField``


.. autoclass:: NS_NodeManager
  :show-inheritance:

  .. automethod:: find_problems

   Example:

     .. code-block:: python

        MyNodeModel.objects.find_problems()

     .. note::

        A node won't appear in more than one list, even when it exhibits
        more than one problem. This method stops checking a node when it
        finds a problem and continues to the next node.

     .. note::

        These problems can't be solved automatically.

.. autoclass:: NS_NodeQuerySet
  :show-inheritance:

Signals
-------

The :mod:`treebeard.ns_tree` module defines several signals that are sent when
bulk updates are made to the tree. Along with the standard Django ``post_save``
and ``post_delete`` signals that track changes to individual node instances,
these can be used to keep external data stores such as search indexes in sync
with the tree.

.. attribute:: gap_altered

   Sent after a bulk update has been performed to expand or shrink a gap in
   the ``lft``/``rgt`` sequence, with the following arguments:

   ``sender``
      The model class where the update occurred.

   ``tree_id``
      The tree ID of the tree that was updated.

   ``start_index``
      The starting index of the update. All ``lft`` and ``rgt`` values greater
      than or equal to this index, within the tree identified by ``tree_id``,
      were incremented or decremented by ``offset``.

   ``offset``
      The amount by which the gap was expanded (positive) or shrunk (negative).

   ``using``
      The database alias being used.

.. attribute:: tree_ids_incremented

   Sent after a bulk update has been performed to increment tree IDs to allow a
   new root-level node to be inserted, with the following arguments:

   ``sender``
      The model class where the update occurred.

   ``min_tree_id``
      The starting tree ID of the update. All tree IDs greater than or equal to
      this value were incremented by 1.

   ``using``
      The database alias being used.

.. attribute:: subtree_moved

   Sent after a bulk update has been performed to move a subtree, with the
   following arguments:

   ``sender``
      The model class where the update occurred.

   ``tree_id``
      The tree ID of the tree that the subtree was moved from.

   ``lft``
      The initial left value of the topmost node that was moved.

   ``rgt``
      The initial right value of the topmost node that was moved. The update
      operation applies to all nodes in the tree ``tree_id`` with left values
      greater than or equal to ``lft`` and right values less than or equal to
      ``rgt``.

   ``target_tree_id``
      The tree ID of the target tree where the subtree was moved to.

   ``index_offset``
      The amount by which the left and right values of the moved nodes were
      incremented (positive) or decremented (negative) during the move.

   ``depth_offset``
      The amount by which the ``depth`` of the moved nodes was changed during
      the move.

   ``using``
      The database alias being used.

.. attribute:: nodes_deleted

   Sent after one or more nodes are deleted, with the following arguments:

   ``sender``
      The model class where the deletion occurred.

   ``removed_ranges``
      A list of tuples, each containing the tree ID, left value, and right
      value of a contiguous range of nodes that were deleted.

   ``using``
      The database alias being used.

.. _`Joe Celko`: http://en.wikipedia.org/wiki/Joe_Celko
.. _`Trees and Hierarchies in SQL for Smarties`:
  https://shop.elsevier.com/books/joe-celkos-trees-and-hierarchies-in-sql-for-smarties/celko/978-0-12-387733-8
