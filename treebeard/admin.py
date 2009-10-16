from django.contrib import admin

from treebeard.forms import TreeFormAdmin


class TreeAdmin(admin.ModelAdmin):
    """ Manages treebeard model. """
    change_list_template = 'admin/tree_change_list.html'
    form = TreeFormAdmin
