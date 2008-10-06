# -*- coding: utf-8 -*-
"""

    treebeard
    ---------

    :synopsys: Efficient Tree implementations for Django 1.0+
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


    ``django-treebeard`` uses `Django Model Inheritance with abstract classes`_
    to let you define your own models. To use ``django-treebeard``:

       1. Download a release from the `treebeard download page`_ or get a
          development version from the `treebeard subversion repository`_.
       2. Run :command:`python setup.py install`
       3. Add ``'treebeard'`` to the ``INSTALLED_APPS`` section in your django
          settings file.
       4. Create a new model that inherits from one of ``django-treebeard``'s
          abstract tree models: :class:`mp_tree.MP_Node`
       5. Run :command:`python manage.py syncdb`


    Read the :class:`Node` API reference for detailed info.

    .. _`treebeard download page`:
       http://code.google.com/p/django-treebeard/downloads/list
    .. _`treebeard subversion repository`:
       http://code.google.com/p/django-treebeard/source/checkout

"""

VERSION = (0, 9, 'svn')

from treebeard.models import Node, InvalidPosition, InvalidMoveToDescendant, \
    MissingNodeOrderBy, PathOverflow



