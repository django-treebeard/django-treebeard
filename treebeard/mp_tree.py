"""Materialized Path Trees"""

import collections
import warnings
from functools import cache
from typing import Any

from django.core import serializers
from django.db import connections, models, router, transaction
from django.db.models import F, Func, OuterRef, Q, Subquery, Value
from django.db.models.functions import Concat, Greatest, Length, Substr
from django.dispatch import Signal
from django.utils.translation import gettext_noop as _

from treebeard.deprecation import RemovedInTreebeard7Warning
from treebeard.exceptions import InvalidMoveToDescendant, PathOverflow
from treebeard.models import Node, NodeManager
from treebeard.numconv import NumConv
from treebeard.utils import check_create_args, prepare_dumpdata_for_loading, save_m2m

path_updated = Signal()
nodes_deleted = Signal()


class MP_NodeQuerySet(models.query.QuerySet):
    """
    Custom queryset for the tree node manager.

    Needed only for the custom delete method.
    """

    def delete(self, *args, **kwargs):
        """
        Custom delete method, will remove all descendant nodes to ensure a
        consistent tree (no orphans)

        :returns: tuple of the number of objects deleted and a dictionary
                  with the number of deletions per object type
        """
        # we'll have to manually run through all the nodes that are going
        # to be deleted and remove nodes from the list if an ancestor is
        # already getting removed, since that would be redundant
        removed = {}
        for node in self.order_by("depth", "path").only("path", "depth", "numchild").prefetch_related(None).iterator():
            found = False
            for depth in range(1, int(len(node.path) / node.steplen)):
                path = node._get_basepath(node.path, depth)
                if path in removed:
                    # we are already removing an ancestor of this node, so skip it
                    found = True
                    break
            if not found:
                removed[node.path] = node

        # ok, got the minimal list of nodes to remove...
        # we must also remove their children
        # and update every parent node's numchild attribute
        parents = collections.Counter()  # Mapping of parent path to the number of children it has lost
        pks_to_remove = []
        paths_to_remove = []
        for path, node in removed.items():
            if parentpath := node._get_basepath(node.path, node.depth - 1):
                parents[parentpath] += 1

            if node.is_leaf():
                pks_to_remove.append(node.pk)  # More efficient than querying by path
            else:
                paths_to_remove.append(node.path)

        model = self.model.objects.tree_model

        # Save the updated numchild of all parents
        for path, num_lost in parents.items():
            model.objects.filter(path=path).update(numchild=Greatest(F("numchild") - num_lost, 0))

        # Django will handle this as a SELECT and then a DELETE of
        # ids, and will deal with removing related objects
        query = Q(pk__in=pks_to_remove)
        for path in paths_to_remove:
            query |= Q(path__startswith=path)
        count, deletion_map = super(MP_NodeQuerySet, model.objects.filter(query)).delete(*args, **kwargs)
        if count > 0:
            nodes_deleted.send(
                sender=model, pks_to_remove=pks_to_remove, paths_to_remove=paths_to_remove, using=self.db
            )
        return count, deletion_map

    delete.alters_data = True
    delete.queryset_only = True


class MP_NodeManager(NodeManager):
    """Custom manager for nodes in a Materialized Path tree."""

    def get_queryset(self):
        """Sets the custom queryset as the default."""
        return MP_NodeQuerySet(self.model, using=self._db).order_by("path")

    def get_tree(self, parent=None, max_depth: int | None = None):
        """
        :returns:

            A queryset of nodes ordered as DFS, including the parent. If
            no parent is given, the entire tree is returned.

            If max_depth is set then the tree is limited to the specified depth, relative
            to the parent (or the root if no parent is specified).
        """
        cls = self.tree_model

        if parent and parent.is_leaf():
            return cls.objects.filter(pk=parent.pk)

        filters = {}

        if parent:
            filters["path__startswith"] = parent.path
            filters["depth__gte"] = parent.depth

        if max_depth is not None:
            filters["depth__lte"] = max_depth + (parent.depth if parent else 0)

        return cls.objects.filter(**filters)

    def fix_tree(self, fix_paths=False, parent=None):
        """
        Solves some problems that can appear when transactions are not used and
        a piece of code breaks, leaving the tree in an inconsistent state.

        The problems this method solves are:

           1. Nodes with an incorrect ``depth`` or ``numchild`` values due to
              incorrect code and lack of database transactions.
           2. "Holes" in the tree. This is normal if you move/delete nodes a
              lot. Holes in a tree don't affect performance,
           3. Incorrect ordering of nodes when ``node_order_by`` is enabled.
              Ordering is enforced on *node insertion*, so if an attribute in
              ``node_order_by`` is modified after the node is inserted, the
              tree ordering will be inconsistent.

        :param fix_paths:

            A boolean value. If True, a slower, more complex fix_tree method
            will be attempted. If False (the default), it will use a safe (and
            fast!) fix approach, but it will only solve the ``depth`` and
            ``numchild`` nodes, it won't fix the tree holes or broken path
            ordering.

        :param parent:

            If provided, limits the operation to descendants of the given node.
            If not provided, the entire tree will be fixed.

            Fixing only part of a tree will only work if the parent itself is valid.
        """
        cls = self.tree_model

        qs = cls.objects.filter(path__startswith=parent.path) if parent else cls.objects.all()

        # fix the depth field; we need the exclude query to speed up postgres
        qs.exclude(depth=Length("path") / cls.steplen).update(depth=Length("path") / cls.steplen)

        # fix the numchild field
        self._fix_numchild(qs)

        if fix_paths:
            with transaction.atomic():
                # To fix holes and mis-orderings in paths, we consider each non-leaf node in turn
                # and ensure that its children's path values are consecutive (and in the order
                # given by node_order_by, if applicable). children_to_fix is a queue of child sets
                # that we know about but have not yet fixed, expressed as a tuple of
                # (parent_path, depth). Since we're updating paths as we go, we must take care to
                # only add items to this list after the corresponding parent node has been fixed
                # (and is thus not going to change).

                # Initially children_to_fix is the set of root nodes, i.e. ones with a path
                # starting with '' and depth 1.
                children_to_fix = [(parent.path, parent.depth + 1)] if parent else [("", 1)]

                while children_to_fix:
                    parent_path, depth = children_to_fix.pop(0)

                    children = cls.objects.filter(path__startswith=parent_path, depth=depth).values(
                        "pk", "path", "depth", "numchild"
                    )

                    desired_sequence = children.order_by(*(cls.node_order_by or ["path"]))

                    # mapping of current path position (converted to numeric) to item
                    actual_sequence = {}

                    # highest numeric path position currently in use
                    max_position = None

                    # loop over items to populate actual_sequence and max_position
                    for item in desired_sequence:
                        actual_position = cls._str2int(item["path"][-cls.steplen :])
                        actual_sequence[actual_position] = item
                        if max_position is None or actual_position > max_position:
                            max_position = actual_position

                    # loop over items to perform path adjustments
                    for i, item in enumerate(desired_sequence):
                        desired_position = i + 1  # positions are 1-indexed
                        actual_position = cls._str2int(item["path"][-cls.steplen :])
                        if actual_position == desired_position:
                            pass
                        else:
                            # if a node is already in the desired position, move that node
                            # to max_position + 1 to get it out of the way
                            occupant = actual_sequence.get(desired_position)
                            if occupant:
                                old_path = occupant["path"]
                                max_position += 1
                                new_path = cls._get_path(parent_path, depth, max_position)
                                if len(new_path) > len(old_path):
                                    previous_max_path = cls._get_path(parent_path, depth, max_position - 1)
                                    raise PathOverflow(_(f"Path Overflow from: '{previous_max_path}'"))

                                self._rewrite_node_path(old_path, new_path)
                                # update actual_sequence to reflect the new position
                                actual_sequence[max_position] = occupant
                                del actual_sequence[desired_position]
                                occupant["path"] = new_path

                            # move item into the (now vacated) desired position
                            old_path = item["path"]
                            new_path = cls._get_path(parent_path, depth, desired_position)
                            self._rewrite_node_path(old_path, new_path)
                            # update actual_sequence to reflect the new position
                            actual_sequence[desired_position] = item
                            del actual_sequence[actual_position]
                            item["path"] = new_path

                        if item["numchild"]:
                            # this item has children to process, and we have now moved the parent
                            # node into its final position, so it's safe to add to children_to_fix
                            children_to_fix.append((item["path"], depth + 1))

    def _rewrite_node_path(self, old_path, new_path):
        queryset = self.tree_model.objects.filter(path__startswith=old_path)
        update_count = queryset.update(path=Concat(Value(new_path), Substr("path", len(old_path) + 1)))
        if update_count > 0:
            path_updated.send(sender=self.tree_model, old_path=old_path, new_path=new_path, using=queryset.db)

    def _fix_numchild(self, qs):
        vendor = connections[router.db_for_write(self.tree_model)].vendor
        child_subquery = (
            self.tree_model.objects.alias(path_length=Length("path"))
            .order_by()
            .filter(path__startswith=OuterRef("path"), path_length=Length(OuterRef("path")) + self.model.steplen)
            .annotate(count=Func(F("pk"), function="Count"))
            .values("count")
        )
        qs = qs.annotate(real_numchild=Subquery(child_subquery, output_field=models.IntegerField())).exclude(
            numchild=F("real_numchild")
        )

        if vendor != "mysql":
            qs.update(numchild=F("real_numchild"))
        else:  # pragma: no cover
            # Our friend MySQL doesn't support update queries that use a select from the same table
            # So we have to update each object individually
            to_update = []
            for node in qs.iterator():
                node.numchild = node.real_numchild
                to_update.append(node)

            self.tree_model.objects.bulk_update(to_update, ["numchild"])

    def find_problems(self, parent=None):
        """
        Checks for problems in the tree structure, problems can occur when:

           1. your code breaks and you get incomplete transactions (always
              use transactions!)
           2. changing the ``steplen`` value in a model (you must
              :meth:`dump_bulk` first, change ``steplen`` and then
              :meth:`load_bulk`

        :param parent:

            If provided, limits the check to the descendants of this node.
            If not provided, the entire tree will be checked.

        :returns: A tuple of five lists:

                  1. a list of ids of nodes with characters not found in the
                     ``alphabet``
                  2. a list of ids of nodes when a wrong ``path`` length
                     according to ``steplen``
                  3. a list of ids of orphaned nodes
                  4. a list of ids of nodes with the wrong depth value for
                     their path
                  5. a list of ids nodes that report a wrong number of children
        """
        cls = self.tree_model

        if parent is not None:
            qs = cls.objects.filter(path__startswith=parent.path)
        else:
            qs = cls.objects.all()

        evil_chars, bad_steplen, orphans = [], [], []
        wrong_depth, wrong_numchild = [], []
        for node in qs.iterator():
            found_error = False
            for char in node.path:
                if char not in cls.alphabet:
                    evil_chars.append(node.pk)
                    found_error = True
                    break
            if found_error:
                continue
            if len(node.path) % cls.steplen:
                bad_steplen.append(node.pk)
                continue
            try:
                self.get_parent(node, update=True)
            except cls.DoesNotExist:
                orphans.append(node.pk)
                continue

            if node.depth != int(len(node.path) / cls.steplen):
                wrong_depth.append(node.pk)
                continue

            real_numchild = (
                cls.objects.alias(computed_depth=Length("path") / cls.steplen)
                .filter(path__range=cls._get_children_path_interval(node.path), computed_depth=node.depth + 1)
                .count()
            )
            if real_numchild != node.numchild:
                wrong_numchild.append(node.pk)
                continue

        return evil_chars, bad_steplen, orphans, wrong_depth, wrong_numchild

    @transaction.atomic
    @check_create_args
    def add_root(self, create_kwargs=None, *, instance=None):
        """
        Adds a root node to the tree.

        This method saves the node in database. The object is populated as if via:

        ```
        obj = self.model(**create_kwargs)
        ```

        if create_kwargs are supplied. If an unsaved model `instance` is supplied, it is used directly.

        :raise PathOverflow: when no more root objects can be added
        """
        # do we have a root node already?
        last_root = self.get_last_root_node()

        if last_root and last_root.node_order_by:
            # There are root nodes and node_order_by has been set.
            # Delegate sorted insertion to add_sibling.
            # We must pass an instance here to ensure that the right object is created for
            # models with multi-table inheritance.
            return self.add_sibling(
                last_root,
                "sorted-sibling",
                instance=instance or self.model(**create_kwargs),
            )

        if last_root:
            # adding the new root node as the last one
            newpath = last_root._inc_path()
        else:
            # adding the first root node
            newpath = self.model._get_path(None, 1, 1)

        newobj = instance or self.model(**create_kwargs)
        newobj.depth = 1
        newobj.path = newpath
        # saving the instance before returning it
        newobj.save(using=self._db)
        return newobj

    @transaction.atomic
    @check_create_args
    def add_child(self, target, create_kwargs=None, *, instance=None):
        """
        Adds a child to the node.

        This method saves the node in database. The object is populated as if via:

        ```
        obj = self.__class__(**create_kwargs)
        ```

        if `create_kwargs` are supplied. If an unsaved model `instance` is supplied, it is used directly.

        :raise PathOverflow: when no more child nodes can be added
        """
        # Lock the parent row
        node = self.select_for_update().get(pk=target.pk)
        if self.model.node_order_by and not node.is_leaf():
            # there are child nodes and node_order_by has been set
            # delegate sorted insertion to add_sibling
            target.numchild += 1
            return self.add_sibling(self.get_last_child(node), "sorted-sibling", create_kwargs, instance=instance)

        newobj = instance or self.model(**create_kwargs)
        newobj.depth = node.depth + 1

        if node.is_leaf():
            # the node had no children, adding the first child
            newobj.path = self.model._get_path(node.path, newobj.depth, 1)
            max_length = self.model._meta.get_field("path").max_length
            if len(newobj.path) > max_length:
                raise PathOverflow(
                    _(
                        "The new node is too deep in the tree, try"
                        " increasing the path.max_length property"
                        " and UPDATE your database"
                    )
                )
        else:
            # adding the new child as the last one
            newobj.path = self.get_last_child(node)._inc_path()

        # Increment numchild on the parent, and also update the object in memory in case the caller reuses it
        self.tree_model.objects.filter(pk=node.pk).update(numchild=F("numchild") + 1)
        target.numchild = node.numchild + 1

        # saving the instance before returning it
        newobj._cached_parent_obj = target
        newobj.save(using=self._db)

        return newobj

    @transaction.atomic
    @check_create_args
    def add_sibling(self, target, pos=None, create_kwargs=None, *, instance=None):
        """
        Adds a new node as a sibling to the current node object.

        This method saves the node in database. The object is populated as if via:

        ```
        obj = self.__class__(**create_kwargs)
        ```

        if `create_kwargs` are supplied. If an unsaved model `instance` is supplied, it is used directly.

        :raise PathOverflow: when the library can't make room for the
           node's new position
        """
        pos = self._prepare_pos_var_for_add_sibling(pos)

        newobj = instance or self.model(**create_kwargs)
        newobj.depth = target.depth

        if pos == "sorted-sibling":
            siblings = self.get_sorted_pos_queryset(self.get_siblings(target), newobj)
            first = siblings.first()
            newpos = first._get_lastpos_in_path() if first else None
            if newpos is None:
                pos = "last-sibling"
        else:
            newpos, siblings = None, []

        _, newpath = self._reorder_nodes_before_add_or_move(pos, newpos, target.depth, target, siblings, None, False)

        parentpath = target._get_basepath(newpath, target.depth - 1)

        if parentpath:
            self._increment_numchild(parentpath)

        # saving the instance before returning it
        newobj.path = newpath
        newobj.save(using=self._db)

        return newobj

    @transaction.atomic
    def move(self, node, target, pos=None):
        """
        Moves node and all its descendants to a new position
        relative to another node.

        :raise PathOverflow: when the library can't make room for the
           node's new position
        """
        pos = self._prepare_pos_var_for_move(pos)

        # initialize variables and if moving to a child, updates "move to
        # child" to become a "move to sibling" if possible (if it can't
        # be done, it means that we are  adding the first child)
        target, newdepth, siblings, newpos, pos = self.update_move_to_child_vars(node=node, target=target, pos=pos)

        if target.is_descendant_of(node):
            raise InvalidMoveToDescendant(_("Can't move node to a descendant."))

        if pos == "sorted-sibling":
            siblings = self.get_sorted_pos_queryset(self.get_siblings(target), node)
            if first := siblings.first():
                newpos = first._get_lastpos_in_path()
                if node._get_lastpos_in_path() == newpos - 1:
                    # The node is already in the right place, nothing to do
                    return
            else:
                newpos = None
                pos = "last-sibling"

        # Handle special cases where nothing needs to be done
        if newdepth == node.get_depth():
            if pos == "first-sibling" and node == self.get_first_sibling(target):
                return

            if pos == "last-sibling" and node == self.get_last_sibling(target):
                return

        if node == target and (
            # Moving a node to left/right of itself is a noop
            pos == "left" or (pos in ("right", "last-sibling") and target == self.get_last_sibling(target))
        ):
            return

        # Move nodes
        oldpath, newpath = self._reorder_nodes_before_add_or_move(
            pos, newpos, newdepth, target, siblings, node.path, True
        )

        self.update_parent_counts_after_move(oldpath, newpath)
        node.refresh_from_db()  # Node path and depth will have changed
        target.refresh_from_db()

    def update_parent_counts_after_move(self, oldpath, newpath):
        """
        Update the numchild value of parent nodes after performing a move.
        """
        oldparentpath = self.model._get_parent_path_from_path(oldpath)
        newparentpath = self.model._get_parent_path_from_path(newpath)
        if oldparentpath != newparentpath:
            # node changed parent, updating counts
            if oldparentpath:
                self._decrement_numchild(oldparentpath)
            if newparentpath:
                self._increment_numchild(newparentpath)

    def update_move_to_child_vars(self, node, target, pos):
        """Update preliminary vars in :meth:`move` when moving to a child"""
        newdepth = target.depth
        newpos = None
        siblings = []
        if pos in ("first-child", "last-child", "sorted-child"):
            if target == node:
                raise InvalidMoveToDescendant(_("Can't move node to itself."))

            # moving to a child
            parent = target
            newdepth += 1
            if target.is_leaf():
                # moving as a target's first child
                newpos = 1
                pos = "first-sibling"
                siblings = self.tree_model.objects.none()
            else:
                target = self.get_last_child(target)
                pos = {
                    "first-child": "first-sibling",
                    "last-child": "last-sibling",
                    "sorted-child": "sorted-sibling",
                }[pos]

            # this is not for save(), since if needed, will be handled with a
            # custom UPDATE, this is only here to update django's object,
            # should be useful in loops
            parent.numchild += 1

        return target, newdepth, siblings, newpos, pos

    def get_root_nodes(self):
        """:returns: A queryset containing the root nodes in the tree."""
        return self.tree_model.objects.filter(depth=1).order_by("path")

    def get_descendants_group_count(self, parent=None):
        """
        Helper for a very common case: get a group of siblings and the number
        of *descendants* (not only children) in every sibling.

        :param parent:

            The parent of the siblings to return. If no parent is given, the
            root nodes will be returned.

        :returns:

            A Queryset of node objects with an extra attribute: `descendants_count`.
        """
        cls = self.tree_model

        qs = self.get_children(parent) if parent else cls.objects.get_root_nodes()
        subquery = (
            cls.objects.filter(path__startswith=OuterRef("path"))
            .order_by()
            .annotate(count=Func(F("pk"), function="Count"))
            .values("count")
        )
        qs = qs.annotate(
            descendants_count=Subquery(subquery, output_field=models.IntegerField()) - 1
        )  # Subtract the parent node from the count
        return qs

    @transaction.atomic
    def load_bulk(
        self,
        bulk_data,
        parent=None,
        keep_ids=False,
        bulk_create=False,
        batch_size=1000,
    ) -> list:
        """
        Loads a list/dictionary structure to the tree.

        :param bulk_data:

            The data that will be loaded, the structure is a list of
            dictionaries with 2 keys:

            - ``data``: will store arguments that will be passed for object
                creation, and

            - ``children``: a list of dictionaries, each one has it's own
                ``data`` and ``children`` keys (a recursive structure)

        :param parent:

            The node that will receive the structure as children, if not
            specified the first level of the structure will be loaded as root
            nodes

        :param keep_ids:

            If enabled, loads the nodes with the same primary keys that are
            given in the structure. Will error if there are nodes without
            primary key info or if the primary keys are already used.

        :param bulk_create:

            Whether to bulk create objects using Django's ``bulk_create()`` method. Only works
            for models without multi-table inheritance. Also does not work with
            MySQL and MSSQL database backends.

        :param batch_size:

            The batch size for ``bulk_create()`` when creating descendant nodes.
            Default is 1000.

        :returns: A list of the added node ids.

        The ordering of nodes in the loaded data is preserved. If this
        needs to be corrected (e.g., to cater for a new `node_order_by`)
        then `fix_tree()` can be run separately on the imported subtree.
        """

        if not bulk_create:
            return super().load_bulk(bulk_data, parent=parent, keep_ids=keep_ids)

        conn = connections[router.db_for_write(self.model)]
        if not conn.features.can_return_rows_from_bulk_insert or conn.vendor == "microsoft":
            raise ValueError("Database backend does not support bulk load. Use load_bulk without bulk_create=True.")

        added = []
        bulk_data = prepare_dumpdata_for_loading(self.model, data=bulk_data, keep_ids=keep_ids)
        children_to_create = []

        def _build_children(parent_node, children) -> None:
            child_depth = parent_node.depth + 1

            for i, child in enumerate(children):
                child.object.depth = child_depth
                child.object.numchild = len(child.children)
                child.object.path = self.model._get_path(parent_node.path, child_depth, i + 1)

                children_to_create.append(child)

                # Recursively process grandchildren
                _build_children(child.object, child.children)

        # Create first level of the bulk data using standard operations, since there may be existing siblings
        for deserialized_obj in bulk_data:
            deserialized_obj.object.numchild = len(deserialized_obj.children)  # Set numchild manually
            node_obj = (
                self.add_child(parent, instance=deserialized_obj.object)
                if parent
                else self.add_root(instance=deserialized_obj.object)
            )
            save_m2m(node_obj, deserialized_obj)
            added.append(node_obj.pk)
            _build_children(node_obj, deserialized_obj.children)

        # Bulk create descendants
        created = self.bulk_create([obj.object for obj in children_to_create], batch_size=batch_size)

        # Save m2m relationships
        for obj, source in zip(created, children_to_create):
            save_m2m(obj, source)

        added.extend([obj.pk for obj in created])

        return added

    def dump_bulk(self, parent=None, keep_ids=True):
        """Dumps a tree branch to a python data structure."""

        cls = self.tree_model

        # Because of fix_tree, this method assumes that the depth
        # and numchild properties in the nodes can be incorrect,
        # so no helper methods are used
        qset = cls.objects.all().order_by("depth", "path")
        if parent:
            qset = qset.filter(path__startswith=parent.path)
        ret, lnk = [], {}
        pk_field = cls._meta.pk.attname
        for pyobj in serializers.serialize("python", qset.iterator()):
            # django's serializer stores the attributes in 'fields'
            fields = pyobj["fields"]
            path = fields["path"]
            depth = int(len(path) / cls.steplen)
            # this will be useless in load_bulk
            del fields["depth"]
            del fields["path"]
            del fields["numchild"]
            fields.pop(pk_field, None)  # this happens immediately after a load_bulk

            newobj = {"data": fields}
            if keep_ids:
                newobj[pk_field] = pyobj["pk"]

            if (not parent and depth == 1) or (parent and len(path) == len(parent.path)):
                ret.append(newobj)
            else:
                parentpath = cls._get_basepath(path, depth - 1)
                parentobj = lnk[parentpath]
                if "children" not in parentobj:
                    parentobj["children"] = []
                parentobj["children"].append(newobj)
            lnk[path] = newobj
        return ret

    def _increment_numchild(self, path):
        self.tree_model.objects.filter(path=path).update(numchild=F("numchild") + 1)

    def _decrement_numchild(self, path):
        self.tree_model.objects.filter(path=path).update(numchild=F("numchild") - 1)

    def _reorder_nodes_before_add_or_move(
        self, pos, newpos, newdepth, target, siblings, oldpath=None, movebranch=False
    ):
        """
        Handles the reordering of nodes and branches when adding/moving
        nodes.

        :returns: A tuple containing the old path and the new path.
        """
        if (pos == "last-sibling") or (pos == "right" and target == self.get_last_sibling(target)):
            # easy, the last node
            last = self.get_last_sibling(target)
            newpath = last._inc_path()
            if movebranch:
                self._set_newpath_in_branches(oldpath, newpath)
            return oldpath, newpath

        if newpos is None:
            siblings = self.get_siblings(target)
            siblings = {
                "left": siblings.filter(path__gte=target.path),
                "right": siblings.filter(path__gt=target.path),
                "first-sibling": siblings,
            }[pos]
            basenum = target._get_lastpos_in_path()
            newpos = {"first-sibling": 1, "left": basenum, "right": basenum + 1}[pos]

        newpath = self.model._get_path(target.path, newdepth, newpos)

        # If the move is amongst siblings and is to the left and there
        # are siblings to the right of its new position then to be on
        # the safe side we temporarily dump it on the end of the list
        tempnewpath = None
        if movebranch and len(oldpath) == len(newpath):
            parentoldpath = self.model._get_basepath(oldpath, int(len(oldpath) / self.model.steplen) - 1)
            parentnewpath = self.model._get_basepath(newpath, newdepth - 1)
            if parentoldpath == parentnewpath and siblings and newpath < oldpath:
                last = self.get_last_sibling(target)
                basenum = last._get_lastpos_in_path()
                tempnewpath = self.model._get_path(newpath, newdepth, basenum + 2)
                self._set_newpath_in_branches(oldpath, tempnewpath)

        # Optimisation to only move siblings which need moving
        # (i.e. if we've got holes, allow them to compress)
        movesiblings = []
        priorpath = newpath
        for node in siblings:
            # If the path of the node is already greater than the path
            # of the previous node it doesn't need shifting
            if node.path > priorpath:
                break
            # It does need shifting, so add to the list
            movesiblings.append(node)
            # Calculate the path that it would be moved to, as that's
            # the next "priorpath"
            priorpath = node._inc_path()
        movesiblings.reverse()

        for node in movesiblings:
            # moving the siblings (and their branches) at the right of the
            # related position one step to the right
            _inc_path = node._inc_path()
            self._set_newpath_in_branches(node.path, node._inc_path())

            if movebranch:
                if oldpath.startswith(node.path):
                    # if moving to a parent, update oldpath since we just
                    # increased the path of the entire branch
                    oldpath = _inc_path + oldpath[len(_inc_path) :]
                if target.path.startswith(node.path):
                    # and if we moved the target, update the object
                    # django made for us, since the update won't do it
                    # maybe useful in loops
                    target.path = _inc_path + target.path[len(_inc_path) :]
        if movebranch:
            # node to move
            self._set_newpath_in_branches(tempnewpath or oldpath, newpath)
        return oldpath, newpath

    def _set_newpath_in_branches(self, oldpath, newpath):
        """
        .. note::

           The query will only update depth values if needed.

        """

        new_path_value = Concat(Value(newpath), Substr("path", len(oldpath) + 1))
        update_kwargs = {}

        # Warning: MySQL processes multiple assigments left to right, using the updated value
        # for any column that is referenced in a subsequent assignment. This behavior differs from standard SQL.
        # See https://dev.mysql.com/doc/refman/8.4/en/update.html
        # For a table with schema name (VARCHAR), length (INT) and row (name="bob", length=3), the query:
        # `UPDATE table SET name='alice', length=LENGTH(name);`
        # would set `length` to 5 in MySQL, but 3 on other databases, because they use the original source value.
        # To avoid having to special case for MySQL, we need to supply the depth as the first parameter to
        # update_kwargs.

        if len(oldpath) != len(newpath):
            update_kwargs["depth"] = Length(new_path_value) / self.model.steplen
        update_kwargs["path"] = new_path_value

        model = self.tree_model
        queryset = model.objects.filter(path__startswith=oldpath)
        update_count = queryset.update(**update_kwargs)
        if update_count > 0:
            path_updated.send(sender=model, old_path=oldpath, new_path=newpath, using=queryset.db)

    def get_children(self, node):
        """:returns: A queryset of all the node's children"""
        if node.is_leaf():
            return self.tree_model.objects.none()

        # Using the path interval generates a more efficient database query than just specifying a path prefix
        return self.tree_model.objects.filter(
            depth=node.depth + 1, path__range=node._get_children_path_interval(node.path)
        ).order_by("path")

    def get_children_count(self, node):
        """
        :returns: The number the node's children, calculated in the most
        efficient possible way.
        """
        return node.numchild

    def get_siblings(self, node):
        """
        :returns: A queryset of all the node's siblings, including the node
            itself.
        """
        qset = self.tree_model.objects.filter(depth=node.depth).order_by("path")
        if node.depth > 1:
            # making sure the non-root nodes share a parent
            parentpath = node._get_basepath(node.path, node.depth - 1)
            qset = qset.filter(path__range=node._get_children_path_interval(parentpath))
        return qset

    def get_descendants(self, node, include_self=False, max_depth: int | None = None):
        """
        :returns: A queryset of all the node's descendants as DFS, doesn't
            include the node itself if `include_self` is False

            If max_depth is set then the tree is limited to the specified depth relative
            to the node.
        """
        manager = self.tree_model.objects
        if include_self:
            return manager.get_tree(node, max_depth=max_depth)
        if node.is_leaf():
            return manager.none()
        return manager.get_tree(node, max_depth=max_depth).exclude(pk=node.pk)

    def get_root(self, node):
        """:returns: the root node for the current node object."""
        if node.is_root():
            return node

        return self.tree_model.objects.get(path=node.path[0 : node.steplen])

    def get_parent(self, node, update=False):
        """
        :returns: the parent node of the current node object.
            Caches the result in the object itself to help in loops.
        """
        depth = int(len(node.path) / node.steplen)
        if depth <= 1:
            return
        try:
            if update:
                del node._cached_parent_obj
            else:
                return node._cached_parent_obj
        except AttributeError:
            pass
        parentpath = node._get_basepath(node.path, depth - 1)
        node._cached_parent_obj = self.tree_model.objects.get(path=parentpath)
        return node._cached_parent_obj

    def get_ancestors(self, node):
        """
        :returns: A queryset containing the current node object's ancestors,
            starting by the root node and descending to the parent.
        """
        if node.is_root():
            return self.tree_model.objects.none()

        # This is necessary to ensure the index is used as opposed to a table scan
        paths = [node.path[0:pos] for pos in range(0, len(node.path), node.steplen)[1:]]
        return self.tree_model.objects.filter(path__in=paths).order_by("depth")

    def get_next_sibling(self, node):
        """
        :returns: The node's next sibling, or None if it was the rightmost
            sibling.
        """
        return self.get_siblings(node).filter(path__gt=node.path).first()

    def get_prev_sibling(self, node):
        """
        :returns: The node's previous sibling, or None if it was the leftmost
            sibling.
        """
        return self.get_siblings(node).filter(path__lt=node.path).last()


class MP_AddRootHandler:
    def __init__(self, cls, **kwargs):
        warnings.warn(
            "MP_AddRootHandler is deprecated. Use Node.objects.add_root() instead.",
            RemovedInTreebeard7Warning,
            stacklevel=2,
        )
        self.cls = cls
        self.kwargs = kwargs

    def process(self):
        instance = self.kwargs.pop("instance", None)
        return self.cls.objects.add_root(self.kwargs, instance=instance)


class MP_AddChildHandler:
    def __init__(self, node, creation_kwargs: dict[str, Any]):
        warnings.warn(
            "MP_AddChildHandler is deprecated. Use Node.objects.add_child() instead.",
            RemovedInTreebeard7Warning,
            stacklevel=2,
        )
        self.node = node
        self.kwargs = creation_kwargs

    def process(self):
        instance = self.kwargs.pop("instance", None)
        return self.node.__class__.objects.add_child(self.node, self.kwargs, instance=instance)


class MP_AddSiblingHandler:
    def __init__(self, node, pos, creation_kwargs: dict[str, Any]):
        warnings.warn(
            "MP_AddSiblingHandler is deprecated. Use Node.objects.add_child() instead.",
            RemovedInTreebeard7Warning,
            stacklevel=2,
        )
        self.node = node
        self.pos = pos
        self.kwargs = creation_kwargs

    def process(self):
        instance = self.kwargs.pop("instance", None)
        return self.node.__class__.objects.add_sibling(self.node, self.pos, self.kwargs, instance=instance)


class MP_MoveHandler:
    def __init__(self, node, target, pos=None):
        warnings.warn(
            "MP_MoveHandler is deprecated. Use Node.objects.move() instead.", RemovedInTreebeard7Warning, stacklevel=2
        )
        self.node = node
        self.node_cls = node.__class__
        self.target = target
        self.pos = pos

    def process(self):
        return self.node.__class__.objects.move(self.node, self.target, self.pos)


class MP_Node(Node):
    """Abstract model to create your own Materialized Path Trees."""

    steplen = 4
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    node_order_by = []
    path = models.CharField(max_length=255, unique=True)
    depth = models.PositiveIntegerField()
    numchild = models.PositiveIntegerField(default=0)

    TREEBEARD_IDENTIFYING_FIELD = "path"
    MOVENODE_FORM_EXCLUDED_FIELDS = ("path", "depth", "numchild")
    _DEFAULT_TREEBEARD_MANAGER = MP_NodeManager

    objects = MP_NodeManager()

    numconv_obj_ = None

    _cached_attributes = (
        *Node._cached_attributes,
        "_cached_parent_obj",
    )

    @classmethod
    def _int2str(cls, num):
        return cls.numconv_obj().int2str(num)

    @classmethod
    def _str2int(cls, num):
        return cls.numconv_obj().str2int(num)

    @classmethod
    @cache
    def numconv_obj(cls):
        return NumConv(cls.alphabet)

    def get_depth(self):
        """:returns: the depth (level) of the node"""
        return self.depth

    def is_sibling_of(self, node):
        """
        :returns: ``True`` if the node is a sibling of another node given as an
            argument, else, returns ``False``
        """
        if self.depth != node.depth:
            return False

        if self.depth == 1:
            return True  # Root nodes are always siblings

        # making sure the non-root nodes share a parent
        return node.path.startswith(self._get_basepath(self.path, self.depth - 1))

    def is_child_of(self, node):
        """
        :returns: ``True`` is the node if a child of another node given as an
            argument, else, returns ``False``
        """
        return self.path.startswith(node.path) and self.depth == node.depth + 1

    def is_descendant_of(self, node):
        """
        :returns: ``True`` if the node is a descendant of another node given
            as an argument, else, returns ``False``
        """
        return self.path.startswith(node.path) and self.depth > node.depth

    def is_root(self):
        """:returns: True if the node is a root node (else, returns False)"""
        return self.depth == 1

    def is_leaf(self):
        """:returns: True if the node is a leaf node (else, returns False)"""
        return self.numchild == 0

    @classmethod
    def _get_basepath(cls, path, depth):
        """:returns: The base path of another path up to a given depth"""
        if path:
            return path[0 : depth * cls.steplen]
        return ""

    @classmethod
    def _get_path(cls, path, depth, newstep):
        """
        Builds a path given some values

        :param path: the base path
        :param depth: the depth of the  node
        :param newstep: the value (integer) of the new step
        """
        parentpath = cls._get_basepath(path, depth - 1)
        key = cls._int2str(newstep)
        return f"{parentpath}{cls.alphabet[0] * (cls.steplen - len(key))}{key}"

    def _inc_path(self):
        """:returns: The path of the next sibling of a given node path."""
        newpos = self._str2int(self.path[-self.steplen :]) + 1
        key = self._int2str(newpos)
        if len(key) > self.steplen:
            raise PathOverflow(_(f"Path Overflow from: '{self.path}'"))
        return f"{self.path[: -self.steplen]}{self.alphabet[0] * (self.steplen - len(key))}{key}"

    def _get_lastpos_in_path(self):
        """:returns: The integer value of the last step in a path."""
        return self._str2int(self.path[-self.steplen :])

    @classmethod
    def _get_parent_path_from_path(cls, path):
        """:returns: The parent path for a given path"""
        if path:
            return path[0 : len(path) - cls.steplen]
        return ""

    @classmethod
    def _get_children_path_interval(cls, path):
        """:returns: An interval of all possible children paths for a node."""
        return (path + cls.alphabet[0] * cls.steplen, path + cls.alphabet[-1] * cls.steplen)

    class Meta:
        """Abstract model."""

        abstract = True
