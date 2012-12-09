Known Caveats
=============

Django Bugs
-----------

Django 1.3, MySQL and Proxy Models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Due to a `bug in Django 1.3`_, deleting nodes could be problematic
**ONLY** under the following conditions:

   * Proxy models are used. Most users don't use this. If you are not
     sure that you are using proxy models, then you are not, and
     shouldn't worry about this.
   * Django 1.3.X is used
   * MySQL is being used.

Solutions to this problem, either:

   * Don't use proxy models
   * Use PostgreSQL
   * Use Django 1.4+

.. note::

   The actual problem resides in MySQL. This Django bug
   is a regression because Django stopped working around
   a limitation in MySQL: MySQL, even while using InnoDB,
   doesn't support referred constraints checks (which is
   enough reason to upgrade to PostgreSQL).

Due to this, ``treebeard`` doesn't support this problematic
configuration and the test suite expect failures (xfail)
when it finds it.

.. _`bug in Django 1.3`: https://code.djangoproject.com/ticket/17918
