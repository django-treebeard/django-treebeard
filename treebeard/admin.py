"Django admin support for treebeard"

from django.contrib import admin
from django.conf.urls.defaults import url, patterns

from treebeard.forms import MoveNodeForm

from pprint import pprint

class TreeAdmin(admin.ModelAdmin):
    "Django Admin class for treebeard"
    change_list_template = 'admin/tree_change_list.html'
    form = MoveNodeForm

    """
    def queryset(self, request):
        print "Get tree"
        pprint(self.model.get_tree())
        print "annotated"
        pprint(self.model.get_annotated_list())
        print "Bulk"
        pprint(self.model.dump_bulk())
        return self.model.objects.all()#.order_by('-path')
        return self.model.get_tree().reverse()
    """

    def get_urls(self):
        """
        Adds a url to move nodes to this admin
        """
        urls = super(TreeAdmin, self).get_urls()
        new_urls = patterns('',
            url('^%s/%s/move/$' % (self.model._meta.app_label,
                self.model._meta.module_name),
                self.admin_site.admin_view(self.move_node)),
        )
        return urls + new_urls

    def move_node(self, request):
        pass
