# -*- coding: utf-8 -*-
"""
Templatetags for django-treebeard to add drag and drop capabilities to the
nodes change list - @jjdelc

"""

from os.path import join

from django.db import models
from django.conf import settings
from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE
from django.template import Library
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.admin.templatetags.admin_list import result_hidden_fields, result_headers, _boolean_icon
from django.contrib.admin.util import lookup_field, display_for_field
from django.utils.safestring import mark_safe
from django.utils.encoding import smart_unicode, force_unicode
from django.utils.html import escape, conditional_escape


register = Library()


def items_for_result(cl, result, form):
    """
    Generates the actual list of data.
    
    @jjdelc:
    This has been shamelessly copied from original django.contrib.admin.templatetags.admin_list.items_for_result in order to alter the dispay for the first element 
    """
    first = True
    pk = cl.lookup_opts.pk.attname
    for field_name in cl.list_display:
        row_class = ''
        try:
            f, attr, value = lookup_field(field_name, result, cl.model_admin)
        except (AttributeError, ObjectDoesNotExist):
            result_repr = EMPTY_CHANGELIST_VALUE
        else:
            if f is None:
                allow_tags = getattr(attr, 'allow_tags', False)
                boolean = getattr(attr, 'boolean', False)
                if boolean:
                    allow_tags = True
                    result_repr = _boolean_icon(value)
                else:
                    result_repr = smart_unicode(value)
                # Strip HTML tags in the resulting text, except if the
                # function has an "allow_tags" attribute set to True.
                if not allow_tags:
                    result_repr = escape(result_repr)
                else:
                    result_repr = mark_safe(result_repr)
            else:
                if value is None:
                    result_repr = EMPTY_CHANGELIST_VALUE
                if isinstance(f.rel, models.ManyToOneRel):
                    result_repr = escape(getattr(result, f.name))
                else:
                    result_repr = display_for_field(value, f)
                if isinstance(f, models.DateField) or isinstance(f, models.TimeField):
                    row_class = ' class="nowrap"'
        if force_unicode(result_repr) == '':
            result_repr = mark_safe('&nbsp;')
        # If list_display_links not defined, add the link tag to the first field
        if (first and not cl.list_display_links) or field_name in cl.list_display_links:
            table_tag = {True:'th', False:'td'}[first]

            # This spacer indents the nodes based on their depth
            spacer = '<span class="spacer">&nbsp;</span>' * (result.get_depth() - 1) if first else ''

            # This shows a collapse or expand link for nodes with childs
            collapse = '<a href="#" title="" class="collapse expanded">-</a>' if result.get_children_count() > 0 else '<span class="collapse">&nbsp;</span>'

            # Add a <td/> before the first col to show the drag handler
            drag_handler = ''

            if first:
                drag_handler = '<td class="drag-handler"><span>&nbsp;</span></td>'

            first = False
            url = cl.url_for_result(result)
            # Convert the pk to something that can be used in Javascript.
            # Problem cases are long ints (23L) and non-ASCII strings.
            if cl.to_field:
                attr = str(cl.to_field)
            else:
                attr = pk
            value = result.serializable_value(attr)
            result_id = repr(force_unicode(value))[1:]
            yield mark_safe(u'%s<%s%s>%s %s <a href="%s"%s>%s</a></%s>' % \
                (drag_handler, table_tag, row_class, spacer, collapse, url, (cl.is_popup and ' onclick="opener.dismissRelatedLookupPopup(window, %s); return false;"' % result_id or ''), conditional_escape(result_repr), table_tag))
        else:
            # By default the fields come from ModelAdmin.list_editable, but if we pull
            # the fields out of the form instead of list_editable custom admins
            # can provide fields on a per request basis
            if form and field_name in form.fields:
                bf = form[field_name]
                result_repr = mark_safe(force_unicode(bf.errors) + force_unicode(bf))
            else:
                result_repr = conditional_escape(result_repr)
            yield mark_safe(u'<td%s>%s</td>' % (row_class, result_repr))
    if form and not form[cl.model._meta.pk.name].is_hidden:
        yield mark_safe(u'<td>%s</td>' % force_unicode(form[cl.model._meta.pk.name]))


def results(cl):
    parent_id = lambda n: n.get_parent().id if not n.is_root() else 0
    if cl.formset:
        for res, form in zip(cl.result_list, cl.formset.forms):
            yield res.id, parent_id(res), res.get_depth(), res.get_children_count(), list(items_for_result(cl, res, form))
    else:
        for res in cl.result_list:
            yield res.id, parent_id(res), res.get_depth(), res.get_children_count(), list(items_for_result(cl, res, None))


def check_empty_dict(GET_dict):
    """
    Returns True if the GET querstring contains on values, but it can contain empty
    keys.
    This is better than doing not bool(request.GET) as an empty key will return
    True
    """
    empty = True
    for k, v in GET_dict.items():
        # Don't disable on p(age) or 'all' GET param
        if v and k != 'p' and k != 'all': 
            empty = False
    return empty



@register.inclusion_tag('admin/tree_change_list_results.html')
def result_tree(cl, request):
    """
    Added 'filtered' param, so the template's js knows whether the results have
    been affected by a GET param or not. Only when the results are not filtered
    you can drag and sort the tree
    """

    # Here I'm adding an extra col on pos 2 for the drag handlers
    headers = list(result_headers(cl))
    headers.insert(1, {
        'text': '+',
        'sortable': True,
        'url': request.path,
        'tooltip': u'Return to ordered Tree',
        })
    return {
        'filtered': not check_empty_dict(request.GET),
        'result_hidden_fields': list(result_hidden_fields(cl)),
        'result_headers': headers,
        'results': list(results(cl)),
    }

@register.simple_tag
def treebeard_css():
    """
    Template tag to print out the proper <link/> tag to include a custom .css
    """
    path = getattr(settings, 'STATIC_URL', None)
    if not path:
        path = getattr(settings, 'MEDIA_URL', None)
    LINK_HTML = """<link rel="stylesheet" type="text/css" href="%s"/>"""
    css_file = join(path, 'treebeard', 'treebeard-admin.css')
    return LINK_HTML % css_file

@register.simple_tag
def treebeard_js():
    """
    Template tag to print out the proper <script/> tag to include a custom .js
    """
    path = getattr(settings, 'STATIC_URL', None)
    if not path:
        path = getattr(settings, 'MEDIA_URL', None)
    SCRIPT_HTML = """<script type="text/javascript" src="%s"></script>"""
    js_file = join(path, 'treebeard', 'treebeard-admin.js')

    # Jquery UI is needed to call disableSelection() on drag and drop so
    # text selections arent marked while dragging a table row
    # http://www.lokkju.com/blog/archives/143 
    JQUERY_UI = """
    <script>(function($){jQuery = $.noConflict(true);})(django.jQuery);</script>
    <script type="text/javascript" src="%s"></script>
    """
    jquery_ui = join(path, 'treebeard', 'jquery-ui-1.8.5.custom.min.js')

    scripts = [SCRIPT_HTML % js_file, JQUERY_UI % jquery_ui]
    return ''.join(scripts)

