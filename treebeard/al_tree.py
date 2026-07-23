"""Adjacency List"""

from django.core import serializers
from django.db import models, transaction
from django.db.models import Exists, Max, Min, OuterRef
from django.utils.translation import gettext_noop as _

from treebeard.exceptions import InvalidMoveToDescendant
from treebeard.models import Node, NodeManager
from treebeard.utils import check_create_args


class AL_NodeManager(NodeManager):
    """Custom manager for nodes in an Adjacency List tree."""

    def get_queryset(self):
        """Sets the custom queryset as the default."""
        if self.model.node_order_by:
            order_by = ["parent"] + list(self.model.node_order_by)
        else:
            order_by = ["parent", "sib_order"]
        return super().get_queryset().order_by(*order_by)

    def get_tree(self, parent=None, max_depth: int | None = None):
        """
        :returns:

            A list of nodes ordered as DFS, including the parent. If
            no parent is given, the entire tree is returned.

            If max_depth is set then the tree is limited to the specified depth, relative
            to the parent (or the root if no parent is specified).
        """
        if parent:
            depth = parent.get_depth() + 1
            parent.node_has_children = self.get_children(parent).exists()
            results = [parent]
            if max_depth:
                max_depth += parent.get_depth()
        else:
            depth = 1
            results = []

        self._get_tree_recursively(results, parent, depth, max_depth=max_depth)
        return results

    def _get_tree_recursively(self, results, parent, depth, max_depth):
        if max_depth and depth > max_depth:
            return results

        if parent:
            qs = self.get_children(parent) if parent.node_has_children else self.none()
        else:
            qs = self.get_root_nodes()

        # Annotate nodes with `node_has_children`, so that we can avoid unnecessary
        # queries to fetch children on leaf nodes
        qs = qs.annotate(node_has_children=Exists(self.tree_model.objects.filter(parent=OuterRef("pk"))))
        for node in qs:
            node._cached_depth = depth
            results.append(node)
            self._get_tree_recursively(results, node, depth + 1, max_depth=max_depth)

    @transaction.atomic
    @check_create_args
    def add_root(self, create_kwargs=None, *, instance=None):
        """Adds a root node to the tree."""
        newobj = instance or self.model(**create_kwargs)
        newobj._cached_depth = 1
        if not self.model.node_order_by:
            max = self.tree_model.objects.filter(parent=None).aggregate(max=Max("sib_order"))["max"] or 0
            newobj.sib_order = max + 1
        newobj.save(using=self._db)
        return newobj

    @transaction.atomic
    @check_create_args
    def add_child(self, target, create_kwargs=None, *, instance=None):
        """Adds a child to the node."""
        cls = self.tree_model

        newobj = instance or cls(**create_kwargs)

        try:
            newobj._cached_depth = target._cached_depth + 1
        except AttributeError:
            pass
        if not cls.node_order_by:
            max = cls.objects.filter(parent=target).aggregate(max=Max("sib_order"))["max"] or 0
            newobj.sib_order = max + 1
        newobj.parent = target
        newobj.save(using=self._db)
        return newobj

    @transaction.atomic
    @check_create_args
    def add_sibling(self, target, pos=None, create_kwargs=None, instance=None):
        """Adds a new node as a sibling to the current node object."""
        pos = self._prepare_pos_var_for_add_sibling(pos)

        newobj = instance or self.tree_model(**create_kwargs)
        if not target.node_order_by:
            newobj.sib_order = self._get_new_sibling_order(pos, target)
        newobj.parent_id = target.parent_id
        newobj.save(using=self._db)
        return newobj

    @transaction.atomic
    def move(self, node, target, pos=None):
        """
        Moves the current node and all it's descendants to a new position
        relative to another node.
        """

        pos = self._prepare_pos_var_for_move(pos)

        sib_order = None
        parent = None

        if pos in ("first-child", "last-child", "sorted-child"):
            if node == target:
                raise InvalidMoveToDescendant(_("Can't move node to itself."))

            # moving to a child
            if not target.is_leaf():
                target = self.get_last_child(target)
                pos = {"first-child": "first-sibling", "last-child": "last-sibling", "sorted-child": "sorted-sibling"}[
                    pos
                ]
            else:
                parent = target
                if pos == "sorted-child":
                    pos = "sorted-sibling"
                else:
                    pos = "first-sibling"
                    sib_order = 1

        if target.is_descendant_of(node):
            raise InvalidMoveToDescendant(_("Can't move node to a descendant."))

        if node == target and (
            (pos == "left")
            or (pos in ("right", "last-sibling") and target == self.get_last_sibling(target))
            or (pos == "first-sibling" and target == self.get_first_sibling(target))
        ):
            # special cases, not actually moving the node, so nothing to do
            return

        node.parent = parent or target.parent
        if pos != "sorted-sibling":  # sorted-sibling delegates to node_order_by
            node.sib_order = sib_order or self._get_new_sibling_order(pos, target)

        node.save(using=self._db)

    def get_root_nodes(self):
        """:returns: A queryset containing the root nodes in the tree."""
        return self.tree_model.objects.filter(parent=None)

    def dump_bulk(self, parent=None, keep_ids=True):
        """Dumps a tree branch to a python data structure."""

        # a list of nodes: not really a queryset, but it works
        objs = self.get_tree(parent)

        ret, lnk = [], {}
        pk_field = self.model._meta.pk.attname
        for node, pyobj in zip(objs, serializers.serialize("python", objs)):
            depth = node.get_depth()
            # django's serializer stores the attributes in 'fields'
            fields = pyobj["fields"]
            del fields["parent"]

            # non-sorted trees have this
            if "sib_order" in fields:
                del fields["sib_order"]

            if pk_field in fields:
                del fields[pk_field]

            newobj = {"data": fields}
            if keep_ids:
                newobj[pk_field] = pyobj["pk"]

            if (not parent and depth == 1) or (parent and depth == parent.get_depth()):
                ret.append(newobj)
            else:
                parentobj = lnk[node.parent_id]
                if "children" not in parentobj:
                    parentobj["children"] = []
                parentobj["children"].append(newobj)
            lnk[node.pk] = newobj
        return ret

    def get_children(self, node):
        """:returns: A queryset of all the node's children"""
        return self.tree_model.objects.filter(parent=node)

    def get_siblings(self, node):
        """
        :returns: A queryset of all the node's siblings, including the node
            itself.
        """
        if node.parent_id:
            return self.tree_model.objects.filter(parent_id=node.parent_id)
        return self.get_root_nodes()

    def get_descendants(self, node, include_self=False, max_depth: int | None = None):
        """
        :returns: A *list* of all the node's descendants, doesn't
            include the node itself if `include_self` is False

            If max_depth is set then the tree is limited to the specified depth relative
            to the node.
        """
        tree = self.tree_model.objects.get_tree(node, max_depth=max_depth)
        return tree if include_self else tree[1:]

    def get_descendant_count(self, node, max_depth: int | None = None):
        """:returns: the number of descendants of a node

        If max_depth is set then the count is limited to the specified depth relative
        to the node.
        """
        return len(self.get_descendants(node, max_depth=max_depth))

    def get_prev_sibling(self, node):
        return self.get_siblings(node).filter(sib_order__lt=node.sib_order).last()

    def get_next_sibling(self, node):
        return self.get_siblings(node).filter(sib_order__gt=node.sib_order).first()

    def get_root(self, node):
        """:returns: the root node for the current node object."""
        if ancestors := self.get_ancestors(node):
            return ancestors[0]
        return node

    def get_parent(self, node, update=False):
        """:returns: the parent node of the supplied node object."""
        if self.model._meta.proxy_for_model:
            # the current node is a proxy model; the returned parent
            # should be the same proxy model, so we need to explicitly
            # fetch it as an instance of that model rather than simply
            # following the 'parent' relation
            if node.parent_id is None:
                return None

            return self.get(pk=node.parent_id)

        return node.parent

    def get_ancestors(self, node):
        """
        :returns: A *list* containing the current node object's ancestors,
            starting by the root node and descending to the parent.
        """
        ancestors = []
        # We use get_parent() instead of .parent because the method does handling of proxy models
        node = self.get_parent(node)
        while node:
            ancestors.insert(0, node)
            node = self.get_parent(node)
        return ancestors

    def _is_target_pos_the_last_sibling(self, pos, target):
        return pos == "last-sibling" or (pos == "right" and target == self.get_last_sibling(target))

    def _make_hole_and_get_sibling_order(self, pos, target_node):
        siblings = self.get_siblings(target_node)
        siblings = {
            "left": siblings.filter(sib_order__gte=target_node.sib_order),
            "right": siblings.filter(sib_order__gt=target_node.sib_order),
            "first-sibling": siblings,
        }[pos]
        sib_order = {"left": target_node.sib_order, "right": target_node.sib_order + 1, "first-sibling": 1}[pos]
        min = siblings.aggregate(min=Min("sib_order"))["min"] or 0
        if min:
            self.tree_model.objects.filter(sib_order__gte=min, parent_id=target_node.parent_id).update(
                sib_order=models.F("sib_order") + 1
            )
        return sib_order

    def _get_new_sibling_order(self, pos, target_node):
        if self._is_target_pos_the_last_sibling(pos, target_node):
            return self.get_last_sibling(target_node).sib_order + 1

        return self._make_hole_and_get_sibling_order(pos, target_node)


class AL_Node(Node):
    """Abstract model to create your own Adjacency List Trees."""

    objects = AL_NodeManager()
    node_order_by = None

    TREEBEARD_IDENTIFYING_FIELD = "parent"
    MOVENODE_FORM_EXCLUDED_FIELDS = ("sib_order", "parent")
    _DEFAULT_TREEBEARD_MANAGER = AL_NodeManager

    _cached_attributes = (
        *Node._cached_attributes,
        "_cached_depth",
    )

    def get_depth(self, update=False):
        """
        :returns: the depth (level) of the node
            Caches the result in the object itself to help in loops.

        :param update: Updates the cached value.
        """

        if self.parent_id is None:
            return 1

        try:
            if update:
                del self._cached_depth
            else:
                return self._cached_depth
        except AttributeError:
            pass

        depth = 0
        node = self
        while node:
            node = node.parent
            depth += 1
        self._cached_depth = depth
        return depth

    def is_root(self):
        return self.parent_id is None

    def is_sibling_of(self, node):
        return self.parent_id == node.parent_id

    def is_child_of(self, node):
        return self.parent_id == node.pk

    def is_descendant_of(self, node):
        """
        :returns: ``True`` if the node if a descendant of another node given
            as an argument, else, returns ``False``
        """
        return self.pk in (obj.pk for obj in node.__class__.objects.get_descendants(node))

    class Meta:
        """Abstract model."""

        abstract = True
