"Django admin support for treebeard"

from django.contrib import admin, messages
from django.conf.urls.defaults import url, patterns
from django.http import HttpResponseBadRequest, HttpResponse

from treebeard.forms import MoveNodeForm
from treebeard.exceptions import InvalidPosition, MissingNodeOrderBy, InvalidMoveToDescendant, PathOverflow

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
            url('^move/$',
                self.admin_site.admin_view(self.move_node),
                name='move_node'),
        )
        return new_urls + urls

    def move_node(self, request):
        try:
            node_id = request.POST['node_id']
            parent_id = request.POST['parent_id']
            sibling_id = request.POST['sibling_id']
            as_child = request.POST.get('as_child', False)
            as_child = bool(int(as_child))
        except KeyError, ValueError:
            # Some parameters were missing return a BadRequest
            return HttpResponseBadRequest(u'Malformed POST params')

        node = self.model.objects.get(pk=node_id)
        # Parent is not used at this time, need to handle special case
        # for root elements that do not have a parent
        #parent = self.model.objects.get(pk=parent_id)
        sibling = self.model.objects.get(pk=sibling_id)

        try:
            try:
                if as_child:
                    node.move(sibling, pos='target')
                else:
                    node.move(sibling, pos='left')
            except InvalidPosition, e:
                # This could be due two reasons (from the docs):
                # :raise InvalidPosition: when passing an invalid ``pos`` parm
                # :raise InvalidPosition: when :attr:`node_order_by` is enabled and
                #   the``pos`` parm wasn't ``sorted-sibling`` or ``sorted-child``
                # 
                # If it happened because the node is not a 'sorted-sibling' or 
                # 'sorted-child' then try to move just a child without preserving the
                # order, so try a different move
                if  as_child:
                    try:
                        # Try as unsorted tree
                        node.move(sibling, pos='last-child')
                    except InvalidPosition:
                        # We are talking about a sorted tree
                        node.move(sibling, pos='sorted-child')
                else:
                    node.move(sibling)

            # If we are here, means that we moved it in onf of the tries
            messages.info(request, u'Moved node "%s" as %s of "%s"' % (node,
                ('sibling', 'child')[as_child], sibling))

        except (MissingNodeOrderBy, PathOverflow, InvalidMoveToDescendant,
            InvalidPosition), e:
            # An error was raised while trying to move the node, then set an
            # error message and return 400, this will cause a reload on the client
            # to show the message
            print e.__class__
            messages.error(request, u'Exception raised while moving node: %s' % e)
            return HttpResponseBadRequest(u'Exception raised during move')
            
        return HttpResponse('OK')

