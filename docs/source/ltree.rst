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

  .. attribute:: path

     ``ltree`` field, stores an ltree hierarchy for the node. The values are auto-generated
     by Treebeard from a simple alphabet.

  .. automethod:: add_root

     See: :meth:`treebeard.models.Node.add_root`

  .. automethod:: add_child

     See: :meth:`treebeard.models.Node.add_child`

  .. automethod:: add_sibling

     See: :meth:`treebeard.models.Node.add_sibling`

  .. automethod:: move

     See: :meth:`treebeard.models.Node.move`

  .. automethod:: get_tree

     See: :meth:`treebeard.models.Node.get_tree`

.. autoclass:: LT_NodeManager
  :show-inheritance:

.. autoclass:: LT_NodeQuerySet
  :show-inheritance:


.. _`ltree`: https://www.postgresql.org/docs/18/ltree.html