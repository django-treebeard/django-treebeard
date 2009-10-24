# -*- coding: utf-8 -*-
"""

    treebeard.models
    ----------------

    Django models.

    :copyright: 2008-2009 by Gustavo Picon
    :license: Apache License 2.0

"""

import operator

from django.db.models import Q
from django.db import models, transaction

from treebeard.exceptions import InvalidPosition, InvalidMoveToDescendant, \
    PathOverflow, MissingNodeOrderBy


class Node(models.Model):
    """ Node class.

    This is the base class that defines the API of all tree models in this
    library:

        - :class:`mp_tree.MP_Node` (materialized path)
        - :class:`ns_tree.NS_Node` (nested sets)
        - :class:`al_tree.AL_Node` (adjacency list)

    """

    @classmethod
    def add_root(cls, **kwargs):
        """
        Adds a root node to the tree. The new root node will be the new
        rightmost root node. If you want to insert a root node at a specific
        position, use :meth:`add_sibling` in an already existing root node
        instead.

        :param \*\*kwargs: object creation data that will be passed to the
            inherited Node model

        :returns: the created node object. It will be save()d by this method.

        Example::

            MyNode.add_root(numval=1, strval='abcd')
            MyNode.add_root(**{'numval':1, 'strval':'abcd'})

        """
        raise NotImplementedError

    @classmethod
    def load_bulk(cls, bulk_data, parent=None, keep_ids=False):
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

            If enabled, lads the nodes with the same id that are given in the
            structure. Will error if there are nodes without id info or if the
            ids are already used.


        :returns: A list of the added node ids.

        .. note::

            Any internal data that you may have stored in your
            nodes' data (:attr:`path`, :attr:`depth`) will be
            ignored.

        .. note::

            If your node model has :attr:`node_order_by` enabled, it will
            take precedence over the order in the structure.

        Example::

            data = [{'data':{'desc':'1'}},
                    {'data':{'desc':'2'}, 'children':[
                      {'data':{'desc':'21'}},
                      {'data':{'desc':'22'}},
                      {'data':{'desc':'23'}, 'children':[
                        {'data':{'desc':'231'}},
                      ]},
                      {'data':{'desc':'24'}},
                    ]},
                    {'data':{'desc':'3'}},
                    {'data':{'desc':'4'}, 'children':[
                      {'data':{'desc':'41'}},
                    ]},
            ]
            # parent = None
            MyNodeModel.load_data(data, None)

        Will create:

            * 1
            * 2

              * 21
              * 22
              * 23

                * 231

              * 24

            * 3
            * 4

              * 41

        """

        # tree, iterative preorder
        added = []
        # stack of nodes to analize
        stack = [(parent, node) for node in bulk_data[::-1]]
        while stack:
            parent, node_struct = stack.pop()
            # shallow copy of the data strucure so it doesn't persist...
            node_data = node_struct['data'].copy()
            if keep_ids:
                node_data['id'] = node_struct['id']
            if parent:
                node_obj = parent.add_child(**node_data)
            else:
                node_obj = cls.add_root(**node_data)
            added.append(node_obj.id)
            if 'children' in node_struct:
                # extending the stack with the current node as the parent of
                # the new nodes
                stack.extend([(node_obj, node) \
                    for node in node_struct['children'][::-1]])
        transaction.commit_unless_managed()
        return added

    @classmethod
    def dump_bulk(cls, parent=None, keep_ids=True):
        """
        Dumps a tree branch to a python data structure.

        :param parent:

            The node whose descendants will be dumped. The node itself will be
            included in the dump. If not given, the entire tree will be dumped.

        :param keep_ids:

            Stores the id value (primary key) of every node. Enabled by
            default.

        :returns: A python data structure, describen with detail in
                  :meth:`load_bulk`

        Example::

           tree = MyNodeModel.dump_bulk()

           branch = MyNodeModel.dump_bulk(node_obj)

        """
        raise NotImplementedError

    @classmethod
    def get_root_nodes(cls):
        """
        :returns: A queryset containing the root nodes in the tree.

        Example::

           MyNodeModel.get_root_nodes()
        """
        raise NotImplementedError

    @classmethod
    def get_first_root_node(cls):
        """
        :returns: The first root node in the tree or ``None`` if it is empty

        Example::

           MyNodeModel.get_first_root_node()
        """
        try:
            return cls.get_root_nodes()[0]
        except IndexError:
            return None

    @classmethod
    def get_last_root_node(cls):
        """
        :returns: The last root node in the tree or ``None`` if it is empty

        Example::

           MyNodeModel.get_last_root_node()

        """
        try:
            return cls.get_root_nodes().reverse()[0]
        except IndexError:
            return None

    @classmethod
    def find_problems(cls):
        """
        Checks for problems in the tree structure.

        Read the documentation of this method on every tree class for details.
        """
        raise NotImplementedError

    @classmethod
    def fix_tree(cls):
        """
        Solves some problems that can appear when transactions are not used and
        a piece of code breaks, leaving the tree in an inconsistent state.

        Read the documentation of this method on every tree class for details.
        """
        raise NotImplementedError

    @classmethod
    def get_tree(cls, parent=None):
        """
        :returns: A list of nodes ordered as DFS, including the parent. If
                  no parent is given, the entire tree is returned.
        """
        raise NotImplementedError

    @classmethod
    def get_descendants_group_count(cls, parent=None):
        """
        Helper for a very common case: get a group of siblings and the number
        of *descendants* (not only children) in every sibling.

        :param parent:

            The parent of the siblings to return. If no parent is given, the
            root nodes will be returned.

        :returns:

            A `list` (**NOT** a Queryset) of node objects with an extra
            attribute: `descendants_count`.

        Example::

            # get a list of the root nodes
            root_nodes = MyModel.get_descendants_group_count()

            for node in root_nodes:
                print '%s by %s (%d replies)' % (node.comment, node.author,
                                                 node.descendants_count)
        """

        # this is the slowest possible implementation, subclasses should do
        # better
        if parent is None:
            qset = cls.get_root_nodes()
        else:
            qset = parent.get_children()
        nodes = list(qset)
        for node in nodes:
            node.descendants_count = node.get_descendant_count()
        return nodes

    def get_depth(self):
        """
        :returns: the depth (level) of the node

        Example::

           node.get_depth()
        """
        raise NotImplementedError

    def get_siblings(self):
        """
        :returns: A queryset of all the node's siblings, including the node
            itself.

        Example::

           node.get_siblings()
        """
        raise NotImplementedError

    def get_children(self):
        """
        :returns: A queryset of all the node's children

        Example::

           node.get_children()
        """
        raise NotImplementedError

    def get_children_count(self):
        """
        :returns: The number of the node's children

        Example::

            node.get_children_count()
        """

        # this is the last resort, subclasses of Node should implement this in
        # a efficient way.
        return self.get_children().count()

    def get_descendants(self):
        """
        :returns: A queryset of all the node's descendants, doesn't
            include the node itself (some subclasses may return a list).

        Example::

           node.get_descendants()
        """
        raise NotImplementedError

    def get_descendant_count(self):
        """
        :returns: the number of descendants of a node.

        Example::

           node.get_descendant_count()
        """
        return self.get_descendants().count()

    def get_first_child(self):
        """
        :returns: The leftmost node's child, or None if it has no children.

        Example::

           node.get_first_child()
        """
        try:
            return self.get_children()[0]
        except IndexError:
            return None

    def get_last_child(self):
        """
        :returns: The rightmost node's child, or None if it has no children.

        Example::

           node.get_last_child()
        """
        try:
            return self.get_children().reverse()[0]
        except IndexError:
            return None

    def get_first_sibling(self):
        """
        :returns: The leftmost node's sibling, can return the node itself if it
            was the leftmost sibling.

        Example::

           node.get_first_sibling()
        """
        return self.get_siblings()[0]

    def get_last_sibling(self):
        """
        :returns: The rightmost node's sibling, can return the node itself if
            it was the rightmost sibling.

        Example::

            node.get_last_sibling()
        """
        return self.get_siblings().reverse()[0]

    def get_prev_sibling(self):
        """
        :returns: The previous node's sibling, or None if it was the leftmost
            sibling.

        Example::

           node.get_prev_sibling()
        """

        siblings = self.get_siblings()
        ids = [obj.pk for obj in siblings]
        if self.pk in ids:
            idx = ids.index(self.pk)
            if idx > 0:
                return siblings[idx-1]

    def get_next_sibling(self):
        """
        :returns: The next node's sibling, or None if it was the rightmost
            sibling.

        Example::

           node.get_next_sibling()
        """
        siblings = self.get_siblings()
        ids = [obj.pk for obj in siblings]
        if self.pk in ids:
            idx = ids.index(self.pk)
            if idx < len(siblings)-1:
                return siblings[idx+1]

    def is_sibling_of(self, node):
        """
        :returns: ``True`` if the node if a sibling of another node given as an
            argument, else, returns ``False``

        :param node:

            The node that will be checked as a sibling

        Example::

           node.is_sibling_of(node2)
        """
        return len(self.get_siblings().filter(pk__in=[node.pk])) > 0

    def is_child_of(self, node):
        """
        :returns: ``True`` if the node is a child of another node given as an
            argument, else, returns ``False``

        :param node:

            The node that will be checked as a parent

        Example::

           node.is_child_of(node2)
        """
        return len(node.get_children().filter(pk__in=[self.pk])) > 0

    def is_descendant_of(self, node):
        """
        :returns: ``True`` if the node if a descendant of another node given
            as an argument, else, returns ``False``

        :param node:

            The node that will be checked as an ancestor

        Example::

           node.is_descendant_of(node2)
        """
        raise NotImplementedError

    def add_child(self, **kwargs):
        """
        Adds a child to the node. The new node will be the new rightmost
        child. If you want to insert a node at a specific position,
        use the :meth:`add_sibling` method of an already existing
        child node instead.

        :param \*\*kwargs:

            Object creation data that will be passed to the inherited Node
            model

        :returns: The created node object. It will be save()d by this method.

        Example::

           node.add_child(numval=1, strval='abcd')
           node.add_child(**{'numval': 1, 'strval': 'abcd'})

        """
        raise NotImplementedError

    def add_sibling(self, pos=None, **kwargs):
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

        :param \*\*kwargs:

            Object creation data that will be passed to the inherited
            Node model

        :returns:

            The created node object. It will be saved by this method.

        :raise InvalidPosition: when passing an invalid ``pos`` parm
        :raise InvalidPosition: when :attr:`node_order_by` is enabled and the
           ``pos`` parm wasn't ``sorted-sibling``
        :raise MissingNodeOrderBy: when passing ``sorted-sibling`` as ``pos``
           and the :attr:`node_order_by` attribute is missing



        Examples::

           node.add_sibling('sorted-sibling', numval=1, strval='abc')
           node.add_sibling('sorted-sibling', **{'numval': 1, 'strval': 'abc'})
        """
        raise NotImplementedError

    def get_root(self):
        """
        :returns: the root node for the current node object.

        Example::

          node.get_root()
        """
        raise NotImplementedError

    def is_root(self):
        """
        :returns: True if the node is a root node (else, returns False)

        Example::

           node.is_root()
        """
        return self.get_root() == self

    def is_leaf(self):
        """
        :returns: True if the node is a leaf node (else, returns False)

        Example::

           node.is_leaf()
        """
        return self.get_children_count() == 0

    def get_ancestors(self):
        """
        :returns: A queryset containing the current node object's ancestors,
            starting by the root node and descending to the parent.
            (some subclasses may return a list)

        Example::

           node.get_ancestors()
        """
        raise NotImplementedError

    def get_parent(self, update=False):
        """
        :returns: the parent node of the current node object.
            Caches the result in the object itself to help in loops.

        :param update: Updates de cached value.

        Example::

           node.get_parent()

        """
        raise NotImplementedError

    def move(self, target, pos=None):
        """
        Moves the current node and all it's descendants to a new position
        relative to another node.

        .. note:: The node can be moved under another root node.


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

            .. note:: If no ``pos`` is given the library will use
                     ``last-sibling``, or ``sorted-sibling`` if
                     :attr:`node_order_by` is enabled.

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

        Examples::

           node.move(node2, 'sorted-child')

           node.move(node2, 'prev-sibling')

        """
        raise NotImplementedError

    def delete(self):
        """
        Removes a node and all it's descendants.

        .. note::

           Call our queryset's delete to handle children removal. Subclasses
           will handle extra maintenance.
        """
        self.__class__.objects.filter(id=self.id).delete()

    def _fix_add_sibling_opts(self, pos):
        """
        prepare the pos variable for the add_sibling method
        """
        if pos is None:
            if self.node_order_by:
                pos = 'sorted-sibling'
            else:
                pos = 'last-sibling'
        if pos not in ('first-sibling', 'left', 'right', 'last-sibling',
                       'sorted-sibling'):
            raise InvalidPosition('Invalid relative position: %s' % (pos, ))
        if self.node_order_by and pos != 'sorted-sibling':
            raise InvalidPosition('Must use %s in add_sibling when'
                                  ' node_order_by is enabled' % (
                                  'sorted-sibling', ))
        if pos == 'sorted-sibling' and not self.node_order_by:
            raise MissingNodeOrderBy('Missing node_order_by attribute.')
        return pos

    def _fix_move_opts(self, pos):
        """
        prepare the pos var for the move method
        """
        if pos is None:
            if self.node_order_by:
                pos = 'sorted-sibling'
            else:
                pos = 'last-sibling'
        if pos not in ('first-sibling', 'left', 'right', 'last-sibling',
                       'sorted-sibling', 'first-child', 'last-child',
                       'sorted-child'):
            raise InvalidPosition('Invalid relative position: %s' % (pos, ))
        if self.node_order_by and pos not in ('sorted-child',
                                              'sorted-sibling'):
            raise InvalidPosition('Must use %s or %s in add_sibling when'
                                  ' node_order_by is enabled' % (
                                  'sorted-sibling', 'sorted-child'))
        if pos in ('sorted-child', 'sorted-sibling') and \
                not self.node_order_by:
            raise MissingNodeOrderBy('Missing node_order_by attribute.')
        return pos

    def get_sorted_pos_queryset(self, siblings, newobj):
        """
        :returns: A queryset of the nodes that must be moved
        to the right. Called only for Node models with :attr:`node_order_by`

        This function was taken from django-mptt (BSD licensed) by Jonathan
        Buchanan:
        http://code.google.com/p/django-mptt/source/browse/trunk/mptt/signals.py?spec=svn100&r=100#12
        """

        fields, filters = [], []
        for field in self.node_order_by:
            value = getattr(newobj, field)
            filters.append(Q(*
                [Q(**{f: v}) for f, v in fields] +
                [Q(**{'%s__gt' % field: value})]))
            fields.append((field, value))
        return siblings.filter(reduce(operator.or_, filters))

    class Meta:
        """
        Abstract model.
        """
        abstract = True
