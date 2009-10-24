# -*- coding: utf-8 -*-
"""

    treebeard.admin
    ---------------

    Django admin support.

    :copyright: 2008-2009 by Gustavo Picon
    :license: Apache License 2.0

    Original contribution by aleh.fl

"""

from django.contrib import admin

from treebeard.forms import TreeFormAdmin


class TreeAdmin(admin.ModelAdmin):
    """ Manages treebeard model. """
    change_list_template = 'admin/tree_change_list.html'
    form = TreeFormAdmin
