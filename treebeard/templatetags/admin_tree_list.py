# -*- coding: utf-8 -*-
"""

    treebeard.templatetags.admin_tree_list
    --------------------------------------

    result_tree template tag.

    :copyright: 2008-2010 by Gustavo Picon
    :license: Apache License 2.0

    Original contribution by aleh.fl

    Additional hack added to allow raw_id_fields
    by Larry Chan
"""

from django.template import Library


register = Library()


def __line(node, request):
    if 't' in request.GET and request.GET['t'] == 'id':
        raw_id_fields = """
        onclick="opener.dismissRelatedLookupPopup(window, '%d'); return false;"
        """ % (node.id,)
    else:
        raw_id_fields = ''

    return ('<input type="checkbox" class="action-select" value="%d" '
            'name="_selected_action" /><a href="%d/" %s>%s</a>') % (node.id,
                                                                 node.id,
                                                                 raw_id_fields,
                                                                 str(node),)


def __subtree(node, request):
    tree = ''
    for subnode in node.get_children():
        tree = tree + '<li>%s</li>' % __subtree(subnode, request)
    if tree:
        tree = '<ul>%s</ul>' % tree
    return __line(node, request) + tree


@register.simple_tag
def result_tree(cl, request):
    tree = ''
    for root_node in cl.model.get_root_nodes():
        tree = tree + '<li>%s</li>' % __subtree(root_node, request)
    return "<ul>%s</ul>" % tree
