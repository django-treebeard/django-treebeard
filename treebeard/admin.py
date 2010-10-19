"Django admin support for treebeard"

from django.contrib import admin

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
