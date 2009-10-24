# -*- coding: utf-8 -*-
"""

    treebeard.templatetags.admin_tree_list
    --------------------------------------

    result_tree template tag.

    :copyright: 2008-2009 by Gustavo Picon
    :license: Apache License 2.0

    Original contribution by aleh.fl

"""

from django.template import Library

register = Library()


def __line(node):
    return ('<input type="checkbox" class="action-select" value="%d" '
            'name="_selected_action" /><a href="%d/">%s</a>') % (node.id,
                                                                 node.id,
                                                                 str(node))


def __subtree(node):
    tree = ''
    for subnode in node.get_children():
        tree = tree + '<li>%s</li>' % __subtree(subnode)
    if tree:
        tree = '<ul>%s</ul>' % tree
    return __line(node) + tree


@register.simple_tag
def result_tree(cl):
    tree = ''
    for root_node in cl.model.get_root_nodes():
        tree = tree + '<li>%s</li>' % __subtree(root_node)
    return "<ul>%s</ul>" % tree
