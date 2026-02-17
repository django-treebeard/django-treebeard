"""Nested Sets"""

import operator
from functools import reduce
from itertools import groupby

from django.core import serializers
from django.db import models, transaction
from django.db.models import Case, F, Q, When
from django.dispatch import Signal
from django.utils.translation import gettext_noop as _

from treebeard.exceptions import InvalidMoveToDescendant
from treebeard.models import Node, NodeManager
from treebeard.utils import check_create_args

gap_altered = Signal()
tree_ids_incremented = Signal()
subtree_moved = Signal()
nodes_deleted = Signal()


class NS_NodeQuerySet(models.query.QuerySet):
    """
    Custom queryset for the tree node manager.

    Needed only for the customized delete method.
    """

    def delete(self, *args, **kwargs):
        """
        Custom delete method, will remove all descendant nodes to ensure a
        consistent tree (no orphans)

        :returns: tuple of the number of objects deleted and a dictionary
                  with the number of deletions per object type
        """
        model = self.model.objects.tree_model

        last_node = None
        toremove = []
        ranges = []
        for node in self.order_by("tree_id", "lft").values("tree_id", "lft", "rgt").prefetch_related(None).iterator():
            if (
                last_node
                and last_node["tree_id"] == node["tree_id"]
                and last_node["lft"] <= node["lft"]
                and last_node["rgt"] >= node["rgt"]
            ):
                # This node is a descendant of the last node, which is already getting removed, so we can skip it
                continue
            last_node = node
            # Remove this node and its descendants
            toremove.append(Q(lft__range=(node["lft"], node["rgt"])) & Q(tree_id=node["tree_id"]))
            ranges.append((node["tree_id"], node["lft"], node["rgt"]))

        if not toremove:
            return (0, {})

        # call the default django delete method with the full set of nodes and descendants to delete,
        # and let it handle the removal of the user's foreign keys
        result = super(NS_NodeQuerySet, model.objects.filter(reduce(operator.or_, toremove))).delete(*args, **kwargs)
        nodes_deleted.send(sender=model, removed_ranges=ranges, using=self.db)

        # Now closing the gap (Celko's trees book, page 62)
        # We do this for every gap that was left in the tree when the nodes
        # were removed.  If many nodes were removed, we're going to update
        # the same nodes over and over again. This would be probably
        # cheaper precalculating the gapsize per intervals, or just do a
        # complete reordering of the tree (uses COUNT)...
        for tree_id, drop_lft, drop_rgt in sorted(ranges, reverse=True):
            model.objects._close_gap(drop_lft, drop_rgt, tree_id)
        return result

    delete.alters_data = True
    delete.queryset_only = True


class NS_NodeManager(NodeManager):
    """Custom manager for nodes in a Nested Sets tree."""

    def get_queryset(self):
        """Sets the custom queryset as the default."""
        return NS_NodeQuerySet(self.model, using=self._db).order_by("tree_id", "lft")

    def get_tree(self, parent=None):
        """
        :returns:

            A *queryset* of nodes ordered as DFS, including the parent.
            If no parent is given, all trees are returned.
        """
        cls = self.tree_model

        if parent is None:
            # return the entire tree
            return cls.objects.all()
        if parent.is_leaf():
            return cls.objects.filter(pk=parent.pk)
        return cls.objects.filter(tree_id=parent.tree_id, lft__range=(parent.lft, parent.rgt - 1))

    @transaction.atomic
    @check_create_args
    def add_root(self, create_kwargs=None, *, instance=None):
        """Adds a root node to the tree."""

        # do we have a root node already?
        last_root = self.get_last_root_node()

        if last_root and last_root.node_order_by:
            # there are root nodes and node_order_by has been set
            # delegate sorted insertion to add_sibling
            return self.add_sibling(last_root, "sorted-sibling", create_kwargs=create_kwargs, instance=instance)

        if last_root:
            # adding the new root node as the last one
            newtree_id = last_root.tree_id + 1
        else:
            # adding the first root node
            newtree_id = 1

        newobj = instance or self.tree_model(**create_kwargs)
        newobj.depth = 1
        newobj.tree_id = newtree_id
        newobj.lft = 1
        newobj.rgt = 2
        # saving the instance before returning it
        newobj.save(using=self._db)
        return newobj

    @transaction.atomic
    @check_create_args
    def add_child(self, target, create_kwargs=None, *, instance=None):
        """Adds a child to the target."""
        # Fetch the parent afresh from the database and lock the row
        # This guards against race conditions and state drift when adding multiple children,
        # and also ensures that we're working with the base tree model in the case of inherited models
        cls = self.tree_model
        node = self.filter(pk=target.pk).select_for_update().get()
        if not node.is_leaf():
            # there are child nodes, delegate insertion to add_sibling
            if node.node_order_by:
                pos = "sorted-sibling"
            else:
                pos = "last-sibling"
            last_child = self.get_last_child(node)
            last_child._cached_parent_obj = node
            new_sibling = self.add_sibling(last_child, pos, create_kwargs=create_kwargs, instance=instance)
            node.rgt += 2
            target.rgt = node.rgt + 2  # Update the rgt of the parent object, which may be used again in a loop
            return new_sibling

        # we're adding the first child of this node
        self._alter_gap(node.tree_id, node.rgt, 2)

        newobj = instance or cls(**create_kwargs)
        newobj.tree_id = node.tree_id
        newobj.depth = node.depth + 1
        newobj.lft = node.lft + 1
        newobj.rgt = node.lft + 2

        # this is just to update the cache
        target.rgt = node.rgt + 2

        newobj._cached_parent_obj = target

        # saving the instance before returning it
        newobj.save(using=self._db)

        return newobj

    @transaction.atomic
    @check_create_args
    def add_sibling(self, target, pos=None, create_kwargs=None, *, instance=None):
        """Adds a new node as a sibling to the target."""

        pos = self._prepare_pos_var_for_add_sibling(pos)
        cls = self.tree_model

        newobj = instance or cls(**create_kwargs)
        newobj.depth = target.depth

        if target.is_root():
            newobj.lft = 1
            newobj.rgt = 2
            if pos == "sorted-sibling":
                siblings = self.get_sorted_pos_queryset(self.get_siblings(target), newobj)
                if siblings.exists():
                    pos = "left"
                    target = siblings.first()
                else:
                    pos = "last-sibling"

            last_root = self.get_last_root_node()
            if (pos == "last-sibling") or (pos == "right" and target == last_root):
                newobj.tree_id = last_root.tree_id + 1
            else:
                newpos = {"first-sibling": 1, "left": target.tree_id, "right": target.tree_id + 1}[pos]
                self._move_tree_right(newpos)

                newobj.tree_id = newpos
        else:
            newobj.tree_id = target.tree_id

            if pos == "sorted-sibling":
                siblings = self.get_sorted_pos_queryset(self.get_siblings(target), newobj)
                if siblings.exists():
                    pos = "left"
                    target = siblings.first()
                else:
                    pos = "last-sibling"

            if pos in ("left", "right", "first-sibling"):
                siblings = self.get_siblings(target)

                if pos == "right":
                    if target == siblings.last():
                        pos = "last-sibling"
                    else:
                        pos = "left"
                        found = False
                        for node in siblings:
                            if found:
                                target = node
                                break
                            elif node == target:
                                found = True
                if pos == "left":
                    if target == siblings.first():
                        pos = "first-sibling"
                if pos == "first-sibling":
                    target = siblings.first()

            if pos == "last-sibling":
                newpos = self.get_parent(target).rgt
                self._alter_gap(target.tree_id, newpos, 2)
            elif pos == "first-sibling" or pos == "left":
                newpos = target.lft
                self._alter_gap(target.tree_id, newpos, 2)

            newobj.lft = newpos
            newobj.rgt = newpos + 1

        # saving the instance before returning it
        newobj.save(using=self._db)

        return newobj

    @transaction.atomic
    def move(self, node, target, pos=None):
        """
        Moves the current node and all it's descendants to a new position
        relative to another node.
        """

        pos = self._prepare_pos_var_for_move(pos)
        cls = self.tree_model
        original_target = target

        parent = None

        if pos in ("first-child", "last-child", "sorted-child"):
            if node == target:
                raise InvalidMoveToDescendant(_("Can't move node to itself."))

            # moving to a child
            if target.is_leaf():
                parent = target
                pos = "last-child"
            else:
                target = self.get_last_child(target)
                pos = {"first-child": "first-sibling", "last-child": "last-sibling", "sorted-child": "sorted-sibling"}[
                    pos
                ]

        if target.is_descendant_of(node):
            raise InvalidMoveToDescendant(_("Can't move node to a descendant."))

        if node == target and (
            (pos == "left")
            or (pos in ("right", "last-sibling") and target == self.get_last_sibling(target))
            or (pos == "first-sibling" and target == self.get_first_sibling(target))
        ):
            # special cases, not actually moving the node so nothing to do
            return

        if pos == "sorted-sibling":
            siblings = self.get_sorted_pos_queryset(self.get_siblings(target), node)
            if siblings.exists():
                pos = "left"
                target = siblings.first()
            else:
                pos = "last-sibling"
        if pos in ("left", "right", "first-sibling"):
            siblings = self.get_siblings(target)

            if pos == "right":
                if target == siblings.last():
                    pos = "last-sibling"
                else:
                    pos = "left"
                    found = False
                    for sib in siblings:
                        if found:
                            target = sib
                            break
                        elif sib == target:
                            found = True
            if pos == "left":
                if target == siblings.first():
                    pos = "first-sibling"
            if pos == "first-sibling":
                target = siblings.first()

        # ok let's move this
        gap = node.rgt - node.lft + 1
        target_tree = target.tree_id

        # first make a hole
        if pos == "last-child":
            newpos = parent.rgt
            self._alter_gap(target.tree_id, newpos, gap)
        elif target.is_root():
            newpos = 1
            if pos == "last-sibling":
                target_tree = self.get_siblings(target).reverse()[0].tree_id + 1
            elif pos == "first-sibling":
                target_tree = 1
                self._move_tree_right(1)
            elif pos == "left":
                self._move_tree_right(target.tree_id)
        else:
            if pos == "last-sibling":
                newpos = self.get_parent(target).rgt
                self._alter_gap(target.tree_id, newpos, gap)
            elif pos == "first-sibling" or pos == "left":
                newpos = target.lft
                self._alter_gap(target.tree_id, newpos, gap)

        # we refresh 'self' because lft/rgt may have changed
        node.refresh_from_db()

        depthdiff = target.depth - node.depth
        if parent:
            depthdiff += 1

        # move the tree to the hole
        jump = newpos - node.lft
        queryset = cls.objects.filter(tree_id=node.tree_id, lft__range=(node.lft, node.rgt))
        update_count = queryset.update(
            tree_id=target_tree,
            lft=F("lft") + jump,
            rgt=F("rgt") + jump,
            depth=F("depth") + depthdiff,
        )
        if update_count > 0:
            subtree_moved.send(
                sender=cls,
                tree_id=node.tree_id,
                lft=node.lft,
                rgt=node.rgt,
                target_tree_id=target_tree,
                index_offset=jump,
                depth_offset=depthdiff,
                using=queryset.db,
            )

        # close the gap
        self._close_gap(node.lft, node.rgt, node.tree_id)
        node.refresh_from_db()  # Tree params will have changed
        original_target.refresh_from_db()

    def get_root_nodes(self):
        """:returns: A queryset containing the root nodes in the tree."""
        return self.tree_model.objects.filter(lft=1)

    def dump_bulk(self, parent=None, keep_ids=True):
        """Dumps a tree branch to a python data structure."""
        qset = self.get_tree(parent)
        ret, lnk = [], {}
        pk_field = self.model._meta.pk.attname
        for pyobj in qset.iterator():
            serobj = serializers.serialize("python", [pyobj])[0]
            # django's serializer stores the attributes in 'fields'
            fields = serobj["fields"]
            depth = fields["depth"]
            # this will be useless in load_bulk
            del fields["lft"]
            del fields["rgt"]
            del fields["depth"]
            del fields["tree_id"]
            if pk_field in fields:
                # this happens immediately after a load_bulk
                del fields[pk_field]

            newobj = {"data": fields}
            if keep_ids:
                newobj[pk_field] = serobj["pk"]

            if (not parent and depth == 1) or (parent and depth == parent.depth):
                ret.append(newobj)
            else:
                parentobj = self.model.objects.get_parent(pyobj)
                parentser = lnk[parentobj.pk]
                if "children" not in parentser:
                    parentser["children"] = []
                parentser["children"].append(newobj)
            lnk[pyobj.pk] = newobj
        return ret

    def find_problems(self, parent=None):
        """
        Checks for inconsistencies in the tree structure.

        :param parent:

            If provided, limits the check to the descendants of this node.
            If not provided, the entire tree will be checked.

        :returns: A tuple of four lists:

                  1. a list of ids of nodes where ``rgt`` is not strictly
                     greater than ``lft``
                  2. a list of ids of nodes where the ``lft`` and ``rgt``
                     values partially overlap with another node (i.e. they are
                     not properly nested)
                  3. a list of ids of root-level nodes that have the same
                     ``tree_id`` as another root-level node
                  4. a list of ids of nodes with the wrong depth value for
                     their nesting level as defined by ``lft`` and ``rgt``
        """
        cls = self.tree_model

        if parent is not None:
            qs = cls.objects.filter(tree_id=parent.tree_id, lft__gte=parent.lft, rgt__lte=parent.rgt)
            initial_depth = self.get_ancestors(parent).count()
        else:
            qs = cls.objects.all()
            initial_depth = 0

        reversed_lft_rgt, overlapping_nodes, duplicate_tree_ids, wrong_depth = [], [], [], []

        # Iterate over the nodes in order of tree_id and lft
        qs = qs.order_by("tree_id", "lft").values("pk", "tree_id", "lft", "rgt", "depth").iterator()

        # Consider each tree individually
        for tree_id, nodes in groupby(qs, operator.itemgetter("tree_id")):
            stack = []
            has_seen_root_node = False

            for node in nodes:
                if node["rgt"] <= node["lft"]:
                    reversed_lft_rgt.append(node["pk"])
                    continue

                # pop any nodes from the stack that are strictly to the left of the current node
                while stack and stack[-1]["rgt"] < node["lft"]:
                    stack.pop()

                if not stack:
                    # this is a root node
                    if has_seen_root_node:
                        # we've already seen a root node with this tree_id, so this is a duplicate
                        duplicate_tree_ids.append(node["pk"])
                        # add this to stack so that we can check subsequent nodes,
                        # but skip further checks for this node
                        stack.append(node)
                        continue
                    else:
                        has_seen_root_node = True
                        stack.append(node)
                else:
                    # this is a child node; check that it is properly nested within its parent
                    if node["lft"] <= stack[-1]["lft"] or stack[-1]["rgt"] <= node["rgt"]:
                        overlapping_nodes.append(node["pk"])
                        continue

                    stack.append(node)

                expected_depth = initial_depth + len(stack)
                if node["depth"] != expected_depth:
                    wrong_depth.append(node["pk"])

        return reversed_lft_rgt, overlapping_nodes, duplicate_tree_ids, wrong_depth

    def get_children(self, node):
        """:returns: A queryset of all the node's children"""
        return self.get_descendants(node).filter(depth=node.depth + 1)

    def get_siblings(self, node):
        """
        :returns: A queryset of all the node's siblings, including the node
            itself.
        """
        if node.lft == 1:
            return self.get_root_nodes()
        return self.get_children(self.get_parent(node, True))

    def get_descendant_count(self, node):
        """:returns: the number of descendants of a node."""
        return (node.rgt - node.lft - 1) / 2

    def get_root(self, node):
        """:returns: the root node for the supplied node object."""
        if node.lft == 1:
            return node
        return self.tree_model.objects.get(tree_id=node.tree_id, lft=1)

    def get_parent(self, node, update=False):
        """
        :returns: the parent node of the supplied node object.
            Caches the result in the object itself to help in loops.
        """
        if node.is_root():
            return
        try:
            if update:
                del node._cached_parent_obj
            else:
                return node._cached_parent_obj
        except AttributeError:
            pass
        # parent = our most direct ancestor
        node._cached_parent_obj = self.get_ancestors(node).reverse()[0]
        return node._cached_parent_obj

    def get_ancestors(self, node):
        """
        :returns: A queryset containing the node's ancestors,
            starting by the root node and descending to the parent.
        """
        if node.is_root():
            return self.tree_model.objects.none()
        return self.tree_model.objects.filter(tree_id=node.tree_id, lft__lt=node.lft, rgt__gt=node.rgt)

    def get_descendants(self, node, include_self=False):
        """
        :returns: A queryset of all the node's descendants as DFS, doesn't
            include the node itself if `include_self` is `False`
        """
        manager = self.tree_model.objects
        if include_self:
            return manager.get_tree(node)
        if node.is_leaf():
            return manager.none()
        return manager.get_tree(node).exclude(pk=node.pk)

    def _alter_gap(self, tree_id, start_index, offset):
        """
        Open or close a gap in the lft/rgt sequence by changing all lft/rgt values greater than or equal to
        start_index within the given tree by the given offset.
        """
        output_field = models.PositiveIntegerField()
        queryset = self.tree_model.objects.filter(rgt__gte=start_index, tree_id=tree_id)
        update_count = queryset.update(
            lft=Case(When(lft__gte=start_index, then=F("lft") + offset), default=F("lft"), output_field=output_field),
            rgt=F("rgt") + offset,
        )
        if update_count > 0:
            gap_altered.send(
                sender=self.tree_model, tree_id=tree_id, start_index=start_index, offset=offset, using=queryset.db
            )

    def _move_tree_right(self, tree_id):
        queryset = self.tree_model.objects.filter(tree_id__gte=tree_id)
        update_count = queryset.update(tree_id=F("tree_id") + 1)
        if update_count > 0:
            tree_ids_incremented.send(sender=self.tree_model, min_tree_id=tree_id, using=queryset.db)

    def _close_gap(self, drop_lft, drop_rgt, tree_id):
        gapsize = drop_rgt - drop_lft + 1
        self._alter_gap(tree_id, drop_lft, -gapsize)


class NS_Node(Node):
    """Abstract model to create your own Nested Sets Trees."""

    node_order_by = []

    lft = models.PositiveIntegerField(db_index=True)
    rgt = models.PositiveIntegerField(db_index=True)
    tree_id = models.PositiveIntegerField(db_index=True)
    depth = models.PositiveIntegerField(db_index=True)

    TREEBEARD_IDENTIFYING_FIELD = "lft"
    MOVENODE_FORM_EXCLUDED_FIELDS = ("depth", "lft", "rgt", "tree_id")
    _DEFAULT_TREEBEARD_MANAGER = NS_NodeManager

    objects = NS_NodeManager()

    _cached_attributes = (
        *Node._cached_attributes,
        "_cached_parent_obj",
    )

    def get_depth(self):
        """:returns: the depth (level) of the node"""
        return self.depth

    def is_leaf(self):
        """:returns: True if the node is a leaf node (else, returns False)"""
        return self.rgt - self.lft == 1

    def is_root(self):
        """:returns: True if the node is a root node (else, returns False)"""
        return self.lft == 1

    def is_descendant_of(self, node):
        """
        :returns: ``True`` if the node if a descendant of another node given
            as an argument, else, returns ``False``
        """
        return self.tree_id == node.tree_id and self.lft > node.lft and self.rgt < node.rgt

    class Meta:
        """Abstract model."""

        abstract = True
