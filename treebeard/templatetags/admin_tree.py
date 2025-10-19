from django.contrib.admin.templatetags.admin_list import result_list
from django.template import Library

register = Library()


def _get_parent_id(node):
    """Return the node's parent id or 0 if node is a root node."""
    if node.is_root():
        return 0
    return node.get_parent().pk


@register.inclusion_tag("admin/change_list_results.html")
def result_tree(cl):
    return result_list(cl)


@register.simple_tag
def tree_context(cl):
    """
    Generate a list containing additional context for each row in the list, for use
    by the frontend. It is assumed that the order of items in cl.result_list is deterministic.
    """
    return [
        {
            "node-id": str(obj.pk),
            "parent-id": _get_parent_id(obj),
            "level": obj.get_depth(),
            "children-num": obj.get_children_count(),
        }
        for obj in cl.result_list
    ]
