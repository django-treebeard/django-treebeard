Nested Sets trees
=================

.. module:: treebeard.ns_tree
.. moduleauthor:: Gustavo Picon <tabo@tabo.pe>

An implementation of Nested Sets trees for Django 1.0+, as described by
`Joe Celko`_ in `Trees and Hierarchies in SQL for Smarties`_.

Nested sets have very efficient reads at the cost of high maintenance on
write/delete operations.


.. _`Joe Celko`: http://en.wikipedia.org/wiki/Joe_Celko
.. _`Trees and Hierarchies in SQL for Smarties`:
  http://www.elsevier.com/wps/product/cws_home/702605

.. inheritance-diagram:: NS_Node
.. autoclass:: NS_Node
  :show-inheritance:


  .. attribute:: node_order_by

     Attribute: a list of model fields that will be used for node
     ordering. When enabled, all tree operations will assume this ordering.

     Example::

        node_order_by = ['field1', 'field2', 'field3']

  .. attribute:: depth

     ``PositiveIntegerField``, depth of a node in the tree. A root node
     has a depth of *1*.

  .. attribute:: lft

     ``PositiveIntegerField``

  .. attribute:: rgt

     ``PositiveIntegerField``

  .. attribute:: tree_id

     ``PositiveIntegerField``

  .. automethod:: get_tree

        See: :meth:`treebeard.Node.get_tree`

        .. note::

            This metod returns a queryset.
