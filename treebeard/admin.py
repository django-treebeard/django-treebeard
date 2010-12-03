"Django admin support for treebeard"

from django.contrib import admin, messages
from django.contrib.admin.views.main import ChangeList
from django.conf.urls.defaults import url, patterns
from django.http import HttpResponseBadRequest, HttpResponse

from treebeard.forms import MoveNodeForm
from treebeard.templatetags.admin_tree import check_empty_dict
from treebeard.exceptions import InvalidPosition, MissingNodeOrderBy, InvalidMoveToDescendant, PathOverflow

class TreeChangeList(ChangeList):

    def get_ordering(self):
        """
        Overriding default's ChangeList.get_ordering so we don't sort the
        results by '-id' as default
        """
        if not check_empty_dict(self.params):
            return super(TreeChangeList, self).get_ordering()
        return None, 'asc'


class TreeAdmin(admin.ModelAdmin):
    "Django Admin class for treebeard"
    change_list_template = 'admin/tree_change_list.html'
    form = MoveNodeForm

    def get_changelist(self, request):
        return TreeChangeList

    def queryset(self, request):
        from treebeard.al_tree import AL_Node
        if issubclass(self.model, AL_Node):
            # AL Trees return a list instead of a QuerySet for .get_tree()
            # So we're returning the regular .queryset cause we will use
            # the old admin
            return super(TreeAdmin, self).queryset(request)
        else:
            return self.model.get_tree()

    def changelist_view(self, request, extra_context=None):
        from treebeard.al_tree import AL_Node
        if issubclass(self.model, AL_Node):
            # For AL trees, use the old admin display
            self.change_list_template = 'admin/tree_list.html' 
        return super(TreeAdmin, self).changelist_view(request, extra_context)

    def get_urls(self):
        """
        Adds a url to move nodes to this admin
        """
        urls = super(TreeAdmin, self).get_urls()
        new_urls = patterns('',
            url('^move/$',
                self.admin_site.admin_view(self.move_node),),
        )
        return new_urls + urls

    def move_node(self, request):
        try:
            node_id = request.POST['node_id']
            parent_id = request.POST['parent_id']
            sibling_id = request.POST['sibling_id']
            as_child = request.POST.get('as_child', False)
            as_child = bool(int(as_child))
        except (KeyError, ValueError), e:
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
            messages.error(request, u'Exception raised while moving node: %s' % e)
            return HttpResponseBadRequest(u'Exception raised during move')
            
        return HttpResponse('OK')

