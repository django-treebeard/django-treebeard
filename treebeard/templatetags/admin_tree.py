from functools import cache

from django.db.models import Case, Exists, F, OuterRef, QuerySet, Value, When
from django.template import Library

register = Library()

_TREEBEARD_CLASSES = ("MP_Node", "NS_Node", "AL_Node", "LT_Node")


@cache
def _get_treebeard_base(model):
    """
    Determine which Treebeard base class this model uses.

    We use string inspection to avoid importing all of Treebeard's modules.
    """
    classes = [cls.__name__ for cls in model.mro()]
    for cls in _TREEBEARD_CLASSES:
        if cls in classes:
            return cls


def _get_annotated_context_queryset(cl) -> QuerySet:
    """
    Annotated the result list with a treebeard_has_children property for efficient rendering
    of the list.
    """
    qs = cl.result_list
    base = _get_treebeard_base(cl.model)
    if base == "MP_Node":
        return qs.annotate(treebeard_has_children=Case(When(numchild__gt=0, then=Value(True)), default=Value(False)))
    if base == "NS_Node":
        return qs.alias(num_descs=F("rgt") - F("lft")).annotate(
            treebeard_has_children=Case(When(num_descs__gt=1, then=Value(True)), default=Value(False))
        )
    if base == "AL_Node":
        return qs.annotate(treebeard_has_children=Exists(cl.model.objects.filter(parent=OuterRef("pk"))))
    if base == "LT_Node":
        return qs.annotate(
            treebeard_has_children=Exists(
                cl.model.objects.filter(path__descendants=OuterRef("path")).exclude(pk=OuterRef("pk"))
            )
        )

    raise ValueError(f"Unsupported model {cl.model}")


@register.simple_tag
def tree_context(cl, request):
    """
    Generate a list containing additional context for each row in the list, for use
    by the frontend. It is assumed that the template renders the items in the same order
    as the `result_list` iterator.
    """
    qs = _get_annotated_context_queryset(cl)
    depth = request._treebeard_parent.get_depth() + 1 if request._treebeard_parent else 1
    return [
        {
            "node-id": str(obj.pk),
            "parent-id": str(request._treebeard_parent.pk if request._treebeard_parent else 0),
            "level": depth,
            "has-children": int(obj.treebeard_has_children),
            "can-change": int(cl.model_admin.has_change_permission(request, obj)),
        }
        for obj in qs
    ]
