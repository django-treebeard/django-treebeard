# -*- coding: utf-8 -*-
"""

    treebeard
    ---------

    :synopsys: Efficient Materialized Path tree implementation
               for Django 1.0+
    :copyright: 2008 by `Gustavo Picon <http://gpicon.org>`_
    :license: Apache License 2.0
    :version: 0.9-svn
    :url: http://code.google.com/p/django-treebeard/
    :documentation:
       `treebeard-docs
       <http://django-treebeard.googlecode.com/svn/docs/index.html>`_
    :examples:
       `treebeard-tests
       <http://code.google.com/p/django-treebeard/source/browse/trunk/treebeard/tests.py>`_

    ``django-treebeard`` is an efficient implementation of Materialized Path
    trees for Django 1.0+, as described by `Vadim Tropashko`_ in `SQL Design
    Patterns`_. Materialized Path is probably the fastest way of working with
    trees in SQL without the need of extra work in the database, like Oracle's
    ``CONNECT BY`` or sprocs and triggers for nested intervals.

    In a materialized path approach, every node in the tree will have a
    :attr:`~treebeard.MPNode.path` attribute, where the full path from the root
    to the node will be stored. This has the advantage of needing very simple
    and fast queries, at the risk of inconsistency because of the
    denormalization of ``parent``/``child`` foreign keys. This can be prevented
    with transactions (and of course you are already using them, right?).

    ``django-treebeard`` uses a particular approach: every step in the path has
    a fixed width and has no separators. This makes queries predictable and
    faster at the cost of using more characters to store a step. To attack this
    problem, every step number is encoded.

    Also, two extra fields are stored in every node:
    :attr:`~treebeard.MPNode.depth` and :attr:`~treebeard.MPNode.numchild`.
    This makes the read operations faster, at the cost of a little more
    maintenance on tree updates/inserts/deletes. Don't worry, even with these
    extra steps, materialized path is more efficient than other approaches.

    .. note::
       
       The materialized path approach makes heavy use of ``LIKE`` in your
       database, with clauses like ``WHERE path LIKE '002003%'``. If you think
       that ``LIKE`` is too slow, you're right, but in this case the
       :attr:`~treebeard.MPNode.path` field is indexed in the database, and all
       ``LIKE`` clauses that don't **start** with a ``%`` character will use the
       index. This is what makes the materialized path approach so fast.

    ``django-treebeard`` uses `Django Model Inheritance with abstract classes`_
    to let you define your own models. To use ``django-treebeard``:

       1. Download a release from the `treebeard download page`_ or get a
          development version from the `treebeard subversion repository`_.
       2. Run :command:`python setup.py install`
       3. Add ``'treebeard'`` to the ``INSTALLED_APPS`` section in your django
          settings file.
       4. Create a new model that inherits from :class:`treebeard.MPNode`
       5. Run :command:`python manage.py syncdb`

    Read the :class:`treebeard.MPNode` API reference for detailed info.

    .. _`Vadim Tropashko`: http://vadimtropashko.wordpress.com/
    .. _`Sql Design Patterns`:
       http://www.rampant-books.com/book_2006_1_sql_coding_styles.htm
    .. _`Django Model Inheritance with abstract classes`:
      http://docs.djangoproject.com/en/dev/topics/db/models/#abstract-base-classes
    .. _`treebeard download page`:
       http://code.google.com/p/django-treebeard/downloads/list
    .. _`treebeard subversion repository`:
       http://code.google.com/p/django-treebeard/source/checkout

"""

VERSION = (0, 9, 'svn')

from mp_tree import MPNode, InvalidPosition, InvalidMoveToDescendant, \
   PathOverflow, MissingNodeOrderBy

