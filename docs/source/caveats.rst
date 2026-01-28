Known Caveats
=============

Raw Queries
-----------

``django-treebeard`` uses Django raw SQL queries for
some write operations, and raw queries don't update the objects in the
ORM since it's being bypassed.

Because of this, if you have a node in memory and plan to use it after a
tree modification (adding/removing/moving nodes), you need to reload it.


Inconsistent state
------------------

The nature of tree implementations means that updating one object in a tree
frequently requires making updates to several other objects (e.g., parents, siblings, children)
in order to ensure efficiency of querying.

Treebeard wraps all create/update operations in a database transaction to minimise the impact of
race conditions, but it is still possible for data to end up in an inconsistent state in cases where
large numbers of concurrent writes take place. Projects may wish to consider overriding Treebeard methods to apply additional 
locks (e.g., lock the whole table when performing a move) to further reduce the chance of inconsistencies.
This comes with a potentially significant performance penalty.

``MP_Node`` ships with a ``fix_tree()`` method that can be used to find and correct inconsistencies
in Materialized Path trees.

Overriding the default manager
------------------------------

One of the most common source of bug reports in ``django-treebeard``
is the overriding of the default managers in the subclasses.

``django-treebeard`` relies on the default manager for correctness
and internal maintenance. If you override the default manager,
by overriding the ``objects`` member in your subclass, you
*WILL* have errors and inconsistencies in your tree.

To avoid this problem, if you need to override the default
manager, you *MUST* subclass the manager from
the base manager class for the tree you are using.

Read the documentation in each tree type for details.


Custom Managers
---------------

Related to the previous caveat, if you need to create custom
managers, you *MUST* subclass the manager from the
base manager class for the tree you are using.

Read the documentation in each tree type for details.
