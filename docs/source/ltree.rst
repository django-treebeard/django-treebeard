PostgreSQL Ltree trees (experimental)
=====================================

.. module:: treebeard.ltree

This is an efficient tree implementation using PostgreSQL's `ltree`_ module. It requires
a PostgreSQL database.

This is currently an experimental implementation, open for testing and feedback from the community.

Treebeard uses a simple alphabet to generate path hierarchies for objects in the database. In order
to ensure efficient ordering, it uses an approach similar to the Materialized Path implementation
to use path values that match the desired order of nodes in the database.

To use the ``ltree`` module, you need to create the extension in your database:

   .. code-block:: psql
   
      CREATE EXTENSION IF NOT EXISTS ltree;

.. warning::

   As with all tree implementations, please be aware of the :doc:`caveats`.

.. inheritance-diagram:: LT_Node
.. autoclass:: LT_Node
  :show-inheritance:

  .. warning::

     Do not change the values of :attr:`path` directly. Use one of the included methods instead.
     Consider these values *read-only*.

  .. warning::

     Do not change the values of :attr:`node_order_by` after saving your first object. Doing so will
     result in objects being ordered incorrectly.

  .. warning::

     If you need to define your own
     :py:class:`~django.db.models.Manager` class,
     you'll need to subclass
     :py:class:`~LT_NodeManager`.

     Also, if in your manager you need to change the default
     queryset handler, you'll need to subclass
     :py:class:`~LT_NodeQuerySet`.


  Example:

  .. code-block:: python

     class SortedNode(LT_Node):
        node_order_by = ['numval', 'strval']

        numval = models.IntegerField()
        strval = models.CharField(max_length=255)

  Read the API reference of :class:`treebeard.models.Node` for info on methods
  available in this class, or read the following section for methods with
  particular arguments or exceptions.

  .. attribute:: node_order_by

     Attribute: a list of model fields that will be used for node
     ordering. When enabled, all tree operations will assume this ordering.
     This takes precedence over drag and drop ordering in the Django admin.

     Example:

     .. code-block:: python

       node_order_by = ['field1', 'field2', 'field3']

   .. warning::

      ``node_order_by`` values are used to determine correct node ordering *before*
         an object is inserted/moved. This means any fields that
         are auto-populated at a database level, e.g., ``AutoField()``, or ``DateTimeField(auto_now=True)``
         will be ignored for the purpose of ordering if a value isn't provided manually.

  .. attribute:: path

     ``ltree`` field, stores an ltree hierarchy for the node. The values are auto-generated
     by Treebeard from a simple alphabet.

  .. automethod:: add_root

     See: :meth:`treebeard.models.Node.add_root`

  .. automethod:: move

     See: :meth:`treebeard.models.Node.move`

  .. automethod:: get_tree

     See: :meth:`treebeard.models.Node.get_tree`

.. autoclass:: LT_NodeManager
  :show-inheritance:

  .. automethod:: add_child

     See: :meth:`treebeard.models.NodeManager.add_child`

  .. automethod:: add_sibling

     See: :meth:`treebeard.models.NodeManager.add_sibling`

.. autoclass:: LT_NodeQuerySet
  :show-inheritance:

Signals
-------

The :mod:`treebeard.ltree` module defines several signals that are sent when
bulk updates are made to the tree. Along with the standard Django ``post_save``
and ``post_delete`` signals that track changes to individual node instances,
these can be used to keep external data stores such as search indexes in sync
with the tree.

.. attribute:: subtree_moved_right

   Sent after a bulk update has been performed to increment existing path
   values to allow inserting a sibling node, with the following arguments:

   ``sender``
      The model class where the update occurred.

   ``path``
      A :class:`treebeard.ltree.PathValue` indicating the first path updated.
      The update operation applies to the node with this path, siblings after
      it (i.e. nodes where all path elements are equal except the last, which
      is greater), and all their descendants. For the targeted node and its
      siblings, the update operation appends an 'A' to the last element of the
      path; for example, the path ``A.C.B`` becomes ``A.C.BA``. For their
      descendants, the path elements following the incremented one are
      unchanged; for example, the path ``A.C.B.D`` becomes ``A.C.BA.D``.

   ``using``
      The database alias being used.

.. attribute:: subtree_moved

   Sent after a bulk update has been performed to update the paths of a node
   and its descendants, with the following arguments:

   ``sender``
      The model class where the update occurred.

   ``old_path``
      A :class:`treebeard.ltree.PathValue` indicating the old path of the
      topmost node before the update. The update operation applies to all nodes
      with this path as a prefix.

   ``new_path``
      A :class:`treebeard.ltree.PathValue` indicating the new path of the
      topmost node after the update. For all nodes in the update, the
      prefix ``old_path`` is replaced with ``new_path``.

   ``using``
      The database alias being used.

.. attribute:: nodes_deleted

   Sent after one or more nodes are deleted, with the following arguments:

   ``sender``
      The model class where the deletion occurred.

   ``paths_to_remove``
      A list of :class:`treebeard.ltree.PathValue` instances indicating the
      paths of the nodes that were deleted (along with their descendants). All
      nodes that have any of these paths as a prefix were deleted.

   ``using``
      The database alias being used.


.. _`ltree`: https://www.postgresql.org/docs/18/ltree.html