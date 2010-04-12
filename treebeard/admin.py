"Django admin support for treebeard"

from django.contrib import admin

from treebeard.forms import MoveNodeForm


class TreeAdmin(admin.ModelAdmin):
    "Django Admin class for treebeard"
    change_list_template = 'admin/tree_change_list.html'
    form = MoveNodeForm
