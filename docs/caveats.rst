Known Caveats
=============

Raw Queries
-----------

``django-treebeard`` uses Django raw SQL queries for
some write operations, and raw queries don't update the objects in the
ORM since it's being bypassed.

Because of this, if you have a node in memory and plan to use it after a
tree modification (adding/removing/moving nodes), you need to reload it.


