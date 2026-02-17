"""Models and base API"""

import operator
import warnings
from contextlib import suppress
from functools import reduce

from django.core import checks
from django.db import models, transaction
from django.db.models import Q
from django.utils.functional import cached_property

from treebeard.deprecation import RemovedInTreebeard7Warning, get_moved_manager_classmethod, get_moved_manager_method
from treebeard.exceptions import InvalidPosition, MissingNodeOrderBy
from treebeard.utils import prepare_dumpdata_for_loading, save_m2m


class Node(models.Model):
    """Node class"""

    # Subclasses must override this to provide the name of a field
    # that identifies the model.
    TREEBEARD_IDENTIFYING_FIELD = None
    # Fields to be excluded from MoveNodeForm
    MOVENODE_FORM_EXCLUDED_FIELDS = ()
    _cached_attributes = ()

    def get_depth(self):  # pragma: no cover
        """:returns: the depth (level) of the node"""
        raise NotImplementedError

    def is_root(self):
        """:returns: True if the node is a root node (else, returns False)"""
        raise NotImplementedError

    def is_leaf(self):
        """:returns: True if the node is a leaf node (else, returns False)"""
        return not self.__class__.objects.get_children(self).exists()

    def is_sibling_of(self, node):
        """
        :returns: ``True`` if the node is a sibling of the supplied node, otherwise ``False``
        """
        return self.__class__.objects.get_siblings(self).filter(pk=node.pk).exists()

    def is_child_of(self, node):
        """
        :returns: ``True`` if the node is a child of the supplied node, otherwise ``False``
        """
        return self.__class__.objects.get_children(node).filter(pk=self.pk).exists()

    def is_descendant_of(self, node):  # pragma: no cover
        """
        :returns: ``True`` if the node is a descendant of the supplied node, otherwise ``False``
        """
        raise NotImplementedError

    @classmethod
    def add_root(cls, **kwargs):
        warnings.warn(
            f"Using {cls.__name__}.add_root() is deprecated. Use {cls.__name__}.objects.add_root() instead.",
            RemovedInTreebeard7Warning,
            stacklevel=2,
        )
        instance = kwargs.pop("instance", None)
        return cls.objects.add_root(create_kwargs=kwargs, instance=instance)

    def add_child(self, **kwargs):
        cls = self.__class__
        warnings.warn(
            f"Using {cls.__name__}.add_child() is deprecated. Use {cls.__name__}.objects.add_child(target) instead.",
            RemovedInTreebeard7Warning,
            stacklevel=2,
        )
        instance = kwargs.pop("instance", None)
        return self.__class__.objects.add_child(self, create_kwargs=kwargs, instance=instance)

    def add_sibling(self, pos=None, **kwargs):  # pragma: no cover
        cls = self.__class__
        warnings.warn(
            f"Using {cls.__name__}.add_sibling() is deprecated. Use {cls.__name__}.objects.add_sibling() instead.",
            RemovedInTreebeard7Warning,
            stacklevel=2,
        )
        instance = kwargs.pop("instance", None)
        return self.__class__.objects.add_sibling(self, pos, create_kwargs=kwargs, instance=instance)

    def move(self, target, pos=None):  # pragma: no cover
        cls = self.__class__
        warnings.warn(
            f"Using {cls.__name__}.move() is deprecated. Use {cls.__name__}.objects.move() instead.",
            RemovedInTreebeard7Warning,
            stacklevel=2,
        )
        return cls.objects.move(self, target, pos)

    def delete(self, *args, **kwargs):
        """Removes a node and all it's descendants."""
        # Call the queryset delete method, which handles deletion of descendants
        return self.__class__.objects.filter(pk=self.pk).delete(*args, **kwargs)

    delete.alters_data = True
    delete.queryset_only = True

    def _clear_cached_attributes(self):
        for attr in self._cached_attributes:
            with suppress(AttributeError):
                delattr(self, attr)

    def refresh_from_db(self, *args, **kwargs):
        super().refresh_from_db(*args, **kwargs)
        self._clear_cached_attributes()

    @classmethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)
        manager_cls = cls._default_manager.__class__
        # Raise an error if the default manager for the model doesn't subclass Treebeard's manager
        if not issubclass(manager_cls, cls._DEFAULT_TREEBEARD_MANAGER):
            errors.append(
                checks.Error(
                    f"{manager_cls.__module__}.{manager_cls.__name__} does not subclass "
                    f"{cls._DEFAULT_TREEBEARD_MANAGER.__module__}.{cls._DEFAULT_TREEBEARD_MANAGER.__name__}.",
                    obj=manager_cls,
                    id="treebeard.E001",
                )
            )
        return errors

    class Meta:
        """Abstract model."""

        abstract = True


# Deprecated class methods that have moved to the model manager. Will be removed in Treebeard 7
def _inject_moved_method_back_compat():
    moved_classmethods = [
        "load_bulk",
        "dump_bulk",
        "get_root_nodes",
        "get_first_root_node",
        "get_last_root_node",
        "find_problems",
        "fix_tree",
        "get_tree",
        "get_descendants_group_count",
        "get_annotated_list_qs",
        "get_annotated_list",
    ]

    for method in moved_classmethods:
        setattr(Node, method, get_moved_manager_classmethod(method))

    moved_methods = [
        "get_children",
        "get_children_count",
        "get_siblings",
        "get_descendants",
        "get_descendant_count",
        "get_first_child",
        "get_last_child",
        "get_first_sibling",
        "get_last_sibling",
        "get_prev_sibling",
        "get_next_sibling",
        "get_root",
        "get_parent",
        "get_ancestors",
    ]

    for method in moved_methods:
        setattr(Node, method, get_moved_manager_method(method))


_inject_moved_method_back_compat()


class NodeManager(models.Manager):
    @cached_property
    def tree_model(self):
        """
        Determine what class we should use for the
        nodes returned by its tree methods (such as get_children).

        Usually this will be trivially the same as the initial model class,
        but there are special cases when model inheritance is in use:

        * If the model extends another via multi-table inheritance, we need to
        use whichever ancestor originally implemented the tree behaviour (i.e.
        the one which defines the fields used by Treebeard). We can't use the
        subclass, because it's not guaranteed that the other nodes reachable
        from the current one will be instances of the same subclass.

        * If the model is a proxy model, the returned nodes should also use
        the proxy class.
        """
        cls = self.model
        base_class = cls._meta.get_field(cls.TREEBEARD_IDENTIFYING_FIELD).model
        if cls._meta.proxy_for_model == base_class:
            return cls

        return base_class

    def get_tree(self, parent=None):  # pragma: no cover
        """
        :returns:

            A list of nodes ordered as DFS, including the parent. If
            no parent is given, the entire tree is returned.
        """
        raise NotImplementedError

    def add_root(self, create_kwargs=None, *, instance=None):  # pragma: no cover
        """
        Adds a root node to the tree. The new root node will be the new
        rightmost root node. If you want to insert a root node at a specific
        position, use :meth:`add_sibling` in an already existing root node
        instead.

        :param `create_kwargs`: dictionary of values to set on the model object.
        :param instance: Instead of passing `create_kwargs`, you can
            pass an already-constructed (but not yet saved) model instance to
            be inserted into the tree.

        :returns: the created node object. It will be save()d by this method.

        :raise NodeAlreadySaved: when the passed ``instance`` already exists
            in the database
        """
        raise NotImplementedError

    def add_child(self, target, create_kwargs=None, *, instance=None):  # pragma: no cover
        """
        Adds a child to the node. The new node will be the new rightmost
        child. If you want to insert a node at a specific position,
        use the :meth:`add_sibling` method of an already existing
        child node instead.

        :param `create_kwargs`: dictionary of values to set on the model object.
        :param instance: Instead of passing object creation data, you can
            pass an already-constructed (but not yet saved) model instance to
            be inserted into the tree.

        :returns: The created node object. It will be save()d by this method.

        :raise NodeAlreadySaved: when the passed ``instance`` already exists
            in the database
        """
        raise NotImplementedError

    def add_sibling(self, target, pos=None, create_kwargs=None, *, instance=None):  # pragma: no cover
        """
        Adds a new node as a sibling to the current node object.

        :param pos:
            The position, relative to the current node object, where the
            new node will be inserted, can be one of:

            - ``first-sibling``: the new node will be the new leftmost sibling
            - ``left``: the new node will take the node's place, which will be
              moved to the right 1 position
            - ``right``: the new node will be inserted at the right of the node
            - ``last-sibling``: the new node will be the new rightmost sibling
            - ``sorted-sibling``: the new node will be at the right position
              according to the value of node_order_by

        :param `create_kwargs`: dictionary of values to set on the model object.
        :param instance: Instead of passing object creation data, you can
            pass an already-constructed (but not yet saved) model instance to
            be inserted into the tree.

        :returns:

            The created node object. It will be saved by this method.

        :raise InvalidPosition: when passing an invalid ``pos`` parm
        :raise InvalidPosition: when :attr:`node_order_by` is enabled and the
           ``pos`` parm wasn't ``sorted-sibling``
        :raise MissingNodeOrderBy: when passing ``sorted-sibling`` as ``pos``
           and the :attr:`node_order_by` attribute is missing
        :raise NodeAlreadySaved: when the passed ``instance`` already exists
            in the database
        """
        raise NotImplementedError

    def move(self, node, target, pos=None):  # pragma: no cover
        """
        Moves a node and all it's descendants to a new position relative to another node.

        :param node:

            The node to move.

        :param target:

            The node that will be used as a relative child/sibling when moving

        :param pos:

            The position, relative to the target node, where the
            current node object will be moved to, can be one of:

            - ``first-child``: the node will be the new leftmost child of the
              ``target`` node
            - ``last-child``: the node will be the new rightmost child of the
              ``target`` node
            - ``sorted-child``: the new node will be moved as a child of the
              ``target`` node according to the value of :attr:`node_order_by`
            - ``first-sibling``: the node will be the new leftmost sibling of
              the ``target`` node
            - ``left``: the node will take the ``target`` node's place, which
              will be moved to the right 1 position
            - ``right``: the node will be moved to the right of the ``target``
              node
            - ``last-sibling``: the node will be the new rightmost sibling of
              the ``target`` node
            - ``sorted-sibling``: the new node will be moved as a sibling of
              the ``target`` node according to the value of
              :attr:`node_order_by`

            .. note::

               If no ``pos`` is given the library will use ``last-sibling``,
               or ``sorted-sibling`` if :attr:`node_order_by` is enabled.

        :returns: None

        :raise InvalidPosition: when passing an invalid ``pos`` parm
        :raise InvalidPosition: when :attr:`node_order_by` is enabled and the
           ``pos`` parm wasn't ``sorted-sibling`` or ``sorted-child``
        :raise InvalidMoveToDescendant: when trying to move a node to one of
           it's own descendants
        :raise PathOverflow: when the library can't make room for the
           node's new position
        :raise MissingNodeOrderBy: when passing ``sorted-sibling`` or
           ``sorted-child`` as ``pos`` and the :attr:`node_order_by`
           attribute is missing
        """
        raise NotImplementedError

    def get_root_nodes(self):  # pragma: no cover
        """:returns: A queryset containing the root nodes in the tree."""
        raise NotImplementedError

    def get_first_root_node(self):
        """
        :returns:

            The first root node in the tree or ``None`` if it is empty.
        """
        return self.get_root_nodes().first()

    def get_last_root_node(self):
        """
        :returns:

            The last root node in the tree or ``None`` if it is empty.
        """
        return self.get_root_nodes().last()

    def get_descendants_group_count(self, parent=None):
        """
        Helper for a very common case: get a group of siblings and the number
        of *descendants* (not only children) in every sibling.

        :param parent:

            The parent of the siblings to return. If no parent is given, the
            root nodes will be returned.

        :returns:

            A `list` (**NOT** a Queryset) of node objects with an extra
            attribute: `descendants_count`.
        """
        if parent is None:
            qset = self.get_root_nodes()
        else:
            qset = self.get_children(parent)
        nodes = list(qset)
        for node in nodes:
            node.descendants_count = self.get_descendant_count(node)
        return nodes

    def get_annotated_list_qs(self, qs):
        """
        Efficiently generates an annotated list from a queryset.

        The queryset MUST be ordered by path, otherwise it will yield
        incorrect results. The queryset must also represent the entirety of
        a branch of a tree: excluded objects will not be fetched and will
        result in gaps in the tree.
        """
        result, info = [], {}
        start_depth, prev_depth = (None, None)
        for node in qs:
            depth = node.get_depth()
            if start_depth is None:
                start_depth = depth
            open = depth and (prev_depth is None or depth > prev_depth)
            if prev_depth is not None and depth < prev_depth:
                info["close"] = list(range(0, prev_depth - depth))
            info = {"open": open, "close": [], "level": depth - start_depth}
            result.append(
                (
                    node,
                    info,
                )
            )
            prev_depth = depth
        if start_depth and start_depth > 0:
            info["close"] = list(range(0, prev_depth - start_depth + 1))
        return result

    def get_annotated_list(self, parent=None, max_depth=None):
        """
        Gets an annotated list from a tree branch.

        :param parent:

            The node whose descendants will be annotated. The node itself
            will be included in the list. If not given, the entire tree
            will be annotated.

        :param max_depth:

            Optionally limit to specified depth
        """
        qs = self.get_tree(parent)
        if max_depth:
            qs = qs.filter(depth__lte=max_depth)
        return self.get_annotated_list_qs(qs)

    @transaction.atomic
    def load_bulk(self, bulk_data, parent=None, keep_ids=False):
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

        :returns: A list of the added node PKs.
        """

        # tree, iterative preorder
        added = []
        bulk_data = prepare_dumpdata_for_loading(self.model, data=bulk_data, keep_ids=keep_ids)
        # stack of nodes to analyze
        stack = [(parent, deserialized_obj) for deserialized_obj in bulk_data[::-1]]

        while stack:
            parent, deserialized_obj = stack.pop()
            node_obj = deserialized_obj.object = (
                self.add_child(parent, instance=deserialized_obj.object)
                if parent
                else self.add_root(instance=deserialized_obj.object)
            )
            save_m2m(node_obj, deserialized_obj)
            added.append(node_obj.pk)
            # extending the stack with the current node as the parent of the new nodes
            stack.extend([(node_obj, child) for child in deserialized_obj.children[::-1]])
        return added

    def dump_bulk(self, parent=None, keep_ids=True):  # pragma: no cover
        """
        Dumps a tree branch to a python data structure.

        :param parent:

            The node whose descendants will be dumped. The node itself will be
            included in the dump. If not given, the entire tree will be dumped.

        :param keep_ids:

            Stores the pk value (primary key) of every node. Enabled by
            default.

        :returns: A python data structure, described with detail in
                  :meth:`load_bulk`
        """
        raise NotImplementedError

    def get_children(self, node):  # pragma: no cover
        """:returns: A queryset of all the node's children"""
        raise NotImplementedError

    def get_children_count(self, node):
        """:returns: The number of the node's children"""
        return self.get_children(node).count()

    def get_siblings(self, node):  # pragma: no cover
        """
        :returns:

            A queryset of all the node's siblings, including the node
            itself.
        """
        raise NotImplementedError

    def get_descendants(self, node, include_self=False):
        """
        :returns:

            A queryset of all the node's descendants, doesn't
            include the node itself if include_self is False.
        """
        raise NotImplementedError

    def get_descendant_count(self, node):
        """:returns: the number of descendants of a node."""
        return self.get_descendants(node).count()

    def get_first_child(self, node):
        """
        :returns:

            The node's leftmost child, or None if it has no children.
        """
        return self.get_children(node).first()

    def get_last_child(self, node):
        """
        :returns:

            The node's rightmost child, or None if it has no children.
        """
        return self.get_children(node).last()

    def get_first_sibling(self, node):
        """
        :returns:

            The node's leftmost sibling. Can return the node itself if
            it was the leftmost sibling.
        """
        return self.get_siblings(node).first()

    def get_last_sibling(self, node):
        """
        :returns:

            The rightmost node's sibling, can return the node itself if
            it was the rightmost sibling.
        """
        return self.get_siblings(node).last()

    def get_prev_sibling(self, node):
        """
        :returns:

            The node's previous sibling, or None if it was the leftmost
            sibling.
        """
        ids = list(self.get_siblings(node).values_list("pk", flat=True))
        idx = ids.index(node.pk)
        if idx > 0:
            return self.get_siblings(node).get(pk=ids[idx - 1])

    def get_next_sibling(self, node):
        """
        :returns:

            The next node's sibling, or None if it was the rightmost
            sibling.
        """
        ids = list(self.get_siblings(node).values_list("pk", flat=True))
        idx = ids.index(node.pk)
        if idx < len(ids) - 1:
            return self.get_siblings(node).get(pk=ids[idx + 1])

    def get_root(self, node):  # pragma: no cover
        """:returns: the root node for supplied node object."""
        raise NotImplementedError

    def get_parent(self, node, update=False):  # pragma: no cover
        """
        :returns: the parent node of the supplied node object.
            Caches the result in the object itself to help in loops.

        :param update: Updates the cached value.
        """
        raise NotImplementedError

    def get_ancestors(self, node):  # pragma: no cover
        """
        :returns:

            A queryset containing the node's ancestors,
            starting by the root node and descending to the parent.
            (some subclasses may return a list)
        """
        raise NotImplementedError

    def _prepare_pos_var(self, pos, method_name, valid_pos, valid_sorted_pos):
        if pos is None:
            if self.model.node_order_by:
                pos = "sorted-sibling"
            else:
                pos = "last-sibling"
        if pos not in valid_pos:
            raise InvalidPosition(f"Invalid relative position: {pos}")
        if self.model.node_order_by and pos not in valid_sorted_pos:
            raise InvalidPosition(
                f"Must use {' or '.join(valid_sorted_pos)} in {method_name} when node_order_by is enabled"
            )
        if pos in valid_sorted_pos and not self.model.node_order_by:
            raise MissingNodeOrderBy("Missing node_order_by attribute.")
        return pos

    _valid_pos_for_add_sibling = ("first-sibling", "left", "right", "last-sibling", "sorted-sibling")
    _valid_pos_for_sorted_add_sibling = ("sorted-sibling",)

    def _prepare_pos_var_for_add_sibling(self, pos):
        return self._prepare_pos_var(
            pos, "add_sibling", self._valid_pos_for_add_sibling, self._valid_pos_for_sorted_add_sibling
        )

    _valid_pos_for_move = _valid_pos_for_add_sibling + ("first-child", "last-child", "sorted-child")
    _valid_pos_for_sorted_move = _valid_pos_for_sorted_add_sibling + ("sorted-child",)

    def _prepare_pos_var_for_move(self, pos):
        return self._prepare_pos_var(pos, "move", self._valid_pos_for_move, self._valid_pos_for_sorted_move)

    def get_sorted_pos_queryset(self, siblings, newobj):
        """
        :returns:

            A queryset of the nodes that must be moved to the right.
            Called only for Node models with :attr:`node_order_by`

        This function is based on _insertion_target_filters from django-mptt
        (MIT licensed) by Jonathan Buchanan:
        https://github.com/django-mptt/django-mptt/blob/0.3.0/mptt/signals.py

        See LICENSE-THIRD-PARTY
        """

        fields, filters = [], []
        for field in self.model.node_order_by:
            comparator = "gt"
            if field.startswith("-"):
                field = field[1:]
                comparator = "lt"

            value = getattr(newobj, field)
            if value is None:
                warnings.warn(
                    f"Received a null value for field '{field}', which is used "
                    f"by '{self.model.__name__}.node_order_by'. "
                    "This field will be ignored when sorting the object.",
                    category=RuntimeWarning,
                )
                continue

            filters.append(Q(*[Q(**{f: v}) for f, v in fields] + [Q(**{f"{field}__{comparator}": value})]))
            fields.append((field, value))

        if not filters:
            return siblings

        return siblings.filter(reduce(operator.or_, filters))
