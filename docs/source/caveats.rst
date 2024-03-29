Known Caveats
=============

Raw Queries
-----------

``django-treebeard`` uses Django raw SQL queries for
some write operations, and raw queries don't update the objects in the
ORM since it's being bypassed.

Because of this, if you have a node in memory and plan to use it after a
tree modification (adding/removing/moving nodes), you need to reload it.


Overriding the default manager
------------------------------

One of the most common source of bug reports in ``django-treebeard``
is the overriding of the default managers in the subclasses.

``django-treebeard`` relies on the default manager for correctness
and internal maintenance. If you override the default manager,
by overriding the ``objects`` member in your subclass, you
*WILL* have errors and inconsistencies in your tree.

To avoid this problem, if you need to override the default
manager, you'll *NEED* to subclass the manager from
the base manager class for the tree you are using.

Read the documentation in each tree type for details.


Custom Managers
---------------

Related to the previous caveat, if you need to create custom
managers, you *NEED* to subclass the manager from the
base manager class for the tree you are using.

Read the documentation in each tree type for details.


Copying model instances
-----------------------

Starting in version 4.5, we made a change to support custom names
in primary fields that exposed a bug in Django's documentation.
This has been fixed in the dev version of Django (3.2 as of
writing this), but even when using older versions,
the `new instructions`_ apply.

.. _new instructions: https://docs.djangoproject.com/en/3.2/topics/db/queries/#copying-model-instances
