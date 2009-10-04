import copy

from django.contrib import admin

from django.contrib.admin.views.main import ChangeList, ERROR_FLAG
from django.contrib.admin import helpers 
from django import template, forms
from django.contrib import admin
from django.contrib.admin.templatetags.admin_list import items_for_result, result_headers
from django.contrib.admin.util import quote
from django.contrib.admin.views.main import IS_POPUP_VAR
from django.db import models, connection, transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext

def multi_delete_tree(modeladmin, request, queryset):
    for obj in queryset:
        print "deleting " + obj.__unicode__()
        obj.delete()

multi_delete_tree.short_description = 'Delete selected'

class BulkUpdater:
    def __init__(self, items, bulk, position_field=None):
        self.position_field = position_field
        self.items = items
        self.bulk = bulk

    def get_data(self, id, bulk=[]):
        if len(bulk) == 0:
            bulk = self.bulk

        for item in bulk:
            if int(item['id']) == int(id):
                return copy.deepcopy(item)
            elif 'children' in item:
                found = self.get_data(id, item['children'])
                if found != None:
                    return copy.deepcopy(found)
            

    def process_children(self, start_position, items):
        new_bulk = []
        num = start_position
        for item in items:
            current_bulk = self.get_data(item['id'])
            if self.position_field != None:
                current_bulk['data'][self.position_field] = num

            if 'children' in current_bulk:
                del current_bulk['children']
            num += 1
            if 'children' in item: 
                (children, num) = self.process_children(num, item['children'])
                current_bulk['children'] = children
            new_bulk.append(current_bulk)
        return (new_bulk, num)

    def get_updated_bulk(self):
        num = 1
        (new_bulk, num) = self.process_children(num, self.items)
        return new_bulk

class TreebeardModelAdmin(admin.ModelAdmin):
    exclude = ('path', 'depth', 'numchild')

    actions = [multi_delete_tree]

    position_field = None


    def save_model(self, request, obj, form, change):
        if change:
            obj.save()
            return

        # keywords can't be unicode?
        params = dict([(str(key), value) for key, value in request.POST.items()])
        del(params['_save'])
        root_node = self.model.get_first_root_node()
        if root_node == None:
            root_node = self.model.add_root()
        root_node.add_child(**params)

    def get_actions(self, request):
        actions = super(TreebeardModelAdmin, self).get_actions(request)
        del(actions['delete_selected'])
        return actions

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        from django.utils.functional import update_wrapper
        
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = self.admin_site.name, self.model._meta.app_label, self.model._meta.module_name
       
        json_url = url(r'^json/$', wrap(self.json_view), name='%sadmin_%s_%s_json' % info)
        pattern_list = [json_url]
        pattern_list.extend(super(TreebeardModelAdmin, self).get_urls())
        return pattern_list

    def json_view(self, request):
        root_node = self.model.get_first_root_node()
        if request.method == "POST":
            try:
                tree = simplejson.loads(request.POST["nested-sortable-widget"])
            except (KeyError, ValueError):
                return HttpResponseBadRequest()

            updater = BulkUpdater(tree['items'], self.model.dump_bulk(), self.position_field)
            updated_bulk = updater.get_updated_bulk()
            print updated_bulk
            self.model.load_bulk(updated_bulk, parent=root_node, keep_ids=True)
            return HttpResponse()

        def get_node_tree(node):
            items = []
            for child in node.get_children():
                item = {'id': child.pk, 'info': [
                    unicode(child), 
                    '<a href="'+ str(child.pk) +'">Change</a>', 
                    helpers.checkbox.render(helpers.ACTION_CHECKBOX_NAME, force_unicode(child.pk)),
                ]}

                if not child.is_leaf():
                    item['children'] = get_node_tree(child)
                items.append(item)
            return items

        items = get_node_tree(root_node)


        # Force load this so the count doesn't hit the database
        count = self.model._default_manager.count() - 1 # minus root node
        return HttpResponse(simplejson.dumps({
            'requestFirstIndex': 0,
            'firstIndex': 0,
            # capitalise first character of each heading
            'columns': ['', '', ''],
            'count': count,
            'totalCount': count,
            'items': items,
        }), mimetype='text/plain')
            
    def changelist_view(self, request, extra_context=None):
        if IS_POPUP_VAR in request.GET:
            return super(TreebeardModelAdmin, self).changelist_view(
                    request, extra_context)
        
        actions = self.get_actions(request)
        if actions:
            action_form = self.action_form(auto_id=None)
            action_form.fields['action'].choices = self.get_action_choices(request)
        else:
            action_form = None 

        if '_selected_action' in request.POST:
            print request.POST.getlist('_selected_action')
        if actions and request.method == 'POST':
            response = self.response_action(request, queryset=self.model.objects.filter(pk__in=request.POST.getlist('_selected_action')))
            if response:
                return response

        opts = self.model._meta
        context = {
            'root_path': self.admin_site.root_path,
            'opts': opts,
            'app_label': opts.app_label,
            'has_add_permission': self.has_add_permission(request),
            'list_per_page': self.list_per_page,
            'action_form': action_form,
            'title': (ugettext('Select %s to change') % 
                        force_unicode(opts.verbose_name)),
            'media': forms.Media(
                js=["treebeard/js/jquery-1.2.6.min.js",
                    "treebeard/js/json.js",
                    "treebeard/js/interface-1.2.js",
                    "treebeard/js/inestedsortable.js",
                    "treebeard/js/jquery.nestedsortablewidget.js",],
                css={'all': ["treebeard/css/nestedsortablewidget.css",]}),
        }
        context.update(extra_context or {})
        return render_to_response("admin/treebeard/change_list.html", context,
                context_instance=template.RequestContext(request))

