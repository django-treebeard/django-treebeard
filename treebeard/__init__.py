# -*- coding: utf-8 -*-
"""

    treebeard
    ---------

    :synopsys: Efficient Materialized Path tree implementation
               for Django 1.0+
    :copyright: 2008 by Gustavo Picon
    :license: Apache License 2.0
    :version: 0.9-svn
    :url: http://code.google.com/p/django-treebeard/
    :documentation:
       `treebeard-docs
       <http://django-treebeard.googlecode.com/svn/docs/index.html>`_
    :examples:
       `treebeard-tests
       <http://code.google.com/p/django-treebeard/source/browse/trunk/treebeard/tests.py>`_

"""

VERSION = (0, 9, 'svn')

from models import MPNode, InvalidPosition, InvalidMoveToDescendant

