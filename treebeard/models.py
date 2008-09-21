# -*- coding: utf-8 -*-
"""

    treebeard.models
    ----------------

    :copyright: 2008 by Gustavo Picon
    :license: Apache License 2.0

"""

import operator
from django.db import models, transaction, connection
from django.db.models import Q
from django.conf import settings
from numconv import int2str, str2int

FIRSTC, LASTC, FIRSTS, LEFTS, RIGHTS, LASTS, SORTEDC, SORTEDS = ('first-child',
    'last-child', 'first-sibling', 'left', 'right', 'last-sibling',
    'sorted-child', 'sorted-sibling')


class NodeQuerySet(models.query.QuerySet):
    """
    Custom queryset for the tree node manager.

    Needed only for the customized delete method.
    """


    def delete(self, known_children=False):
        """
        Custom delete method, will remove all descendant nodes to ensure a
        consistent tree (no orphans)
        """
        if known_children:
            # we already know the children, let's call the default django
            # delete method and let it handle the removal of the user's
            # foreign keys...
            super(NodeQuerySet, self).delete()
        else:
            # we'll have to manually run through all the nodes that are going
            # to be deleted and remove nodes from the list if an ancestor is
            # already getting removed, since that would be redundant
            removed = {}
            for node in self.order_by('depth', 'path'):
                for depth in range(1, len(node.path)/node.steplen):
                    path = node._get_basepath(node.path, depth)
                    if path in removed:
                        # we are already removing a parent of this node
                        # skip
                        continue
                removed[node.path] = node

            # ok, got the minimal list of nodes to remove...
            # we must also remove their children
            # and update every parent node's childnum attribute
            # LOTS OF FUN HERE!
            parents = {}
            toremove = []
            for path, node in removed.items():
                parentpath = node._get_basepath(node.path, node.depth-1)
                if parentpath:
                    if parentpath not in parents:
                        parents[parentpath] = node.get_parent(True)
                    parent = parents[parentpath]
                    if parent:
                        parent.numchild -= 1
                        parent.save()
                if node.numchild:
                    toremove.append(Q(path__startswith=node.path))
                else:
                    toremove.append(Q(path=node.path))
            # uh, django will handle this as a SELECT and then a DELETE of
            # ids..
            # status: NOT SURE IF WANT, maybe add custom sql here
            if toremove:
                self.model.objects.filter(
                    reduce(operator.or_, toremove)).delete(known_children=True)
        transaction.commit_unless_managed()



class NodeManager(models.Manager):
    """ Custom manager for nodes.
    """

    def get_query_set(self):
        """
        Sets the custom queryset as the default.
        """
        return NodeQuerySet(self.model)


class Node(models.Model):
    """ Node class.

    Right now there is only one class that inherits from Node: MPNode for
    Materialized Path trees.
    """
    class Meta:
        """
        Abstract model.
        """
        abstract = True


class MPNode(Node):
    """
    Abstract Materialized Path Node model.

    Abstract model to create your own tree models. By default it
    defines 3 attributes and 3 database fields:

    .. attribute:: steplen
       
       Attribute that defines the length of each step in the path of
       a node. By default BASE36 encoding is used for each step since it's
       the most optimal possible encoding that is portable between the
       supported databases The default value of *4* allows a maximum of
       *1679615* childs per node. Increase this value if you plan to store
       large trees (a steplen of *5* allows more than *60M* childs per node).
       Note that increasing this value, while increasing the number of childs
       per node, will decrease the max depth of the tree (by default:
       *63*). To increase the max depth, increase the max_length attribute of
       the path field in your Node model.

    .. attribute:: alphabet

       Attribute: the alphabet that will be used in base conversions
       when encoding the path steps into strings.

    .. attribute:: node_order_by

       Attribute: a list of model fields that will be used for node
       ordering. When enabled, all tree operations will assume this ordering.
       Currently there is **NO WAY** to reorder a tree, so once you set the
       ordering, you shouldn't change it.

          Example::

             node_order_by = ['field1', 'field2', 'field3']

    .. attribute:: path
        
       ``CharField``, stores the full materialized path for each node. The
       default value of it's max_length, *255*, is the max efficient and
       portable value for a ``varchar``. Increase it to allow deeper trees (max
       depth by default: *63*)

    .. attribute:: depth

       ``PositiveIntegerField``, depth of a node in the tree. A root node
       has a depth of *1*.

    .. attribute:: numchild

       ``PositiveIntegerField``, the number of children of the node.


    
    .. note::
       
       treebeard uses **numconv** for path encoding:
       http://code.google.com/p/numconv/
    """

    steplen = 4
    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    node_order_by = []

    path = models.CharField(max_length=255,
                            unique=True,
                            db_index=True)
    depth = models.PositiveIntegerField()
    numchild = models.PositiveIntegerField(default=0)

    objects = NodeManager()


    @classmethod
    def add_root(cls, **kwargs):
        """
        Adds a root node to the tree. The new root node will be the new
        rightmost root node. If you want to insert a root node at a specific
        position, use :meth:`add_sibling` in an already existing root node
        instead.

        :param \*\*kwargs: object creation data that will be passed to the inherited
            Node model

        :returns: the created node object. It will be save()d by this method.
        """

        # do we have a root node already?
        last_root = cls.get_last_root_node()

        if last_root and last_root.node_order_by:
            # there are root nodes and node_order_by has been set
            # delegate sorted insertion to add_sibling
            return last_root.add_sibling(SORTEDS, **kwargs)

        # creating the new object
        newobj = cls(**kwargs)
        newobj.depth = 1
        if last_root:
            # adding the new root node as the last one
            newobj.path = cls._inc_path(last_root.path)
        else:
            # adding the first root node
            newobj.path = cls._get_path(None, 1, 1)
        # saving the instance before returning it
        newobj.save()
        transaction.commit_unless_managed()
        return newobj


    @classmethod
    def load_bulk(cls, bulk_data, parent=None):
        """
        Loads a list/dictionary structure to the tree.


        :param bulk_data:
        
            The data that will be loaded, the structure is a list of
            dictionaries with 2 keys:

            - ``data``: will store arguments that will be passed for object
              creation, and

            - ``children``: a list of dictionaries, each one has it's own
              ``data`` and ``children`` keys (a recursive structure)

            For instance, this structure::

                [{'data':{'foo':'bar'}},
                 {'data':{'foo':'baz'}, 'children':[
                     {'data':{'foo':'qux'}},
                     {'data':{'foo':'quux'}},
                 ]},
                 {'data':{'foo':'quuux'}}
                ]

            Will create::

                 |------------|-----------|
                bar          baz         quuux
                              |
                        |-----------|
                       qux         quux
            

        :param parent:
            
            The node that will receive the structure as children, if not
            specified the first level of the structure will be loaded as root
            nodes

        :returns: A list of the added node paths.

        .. note::

            Any internal data that you may have stored in your
            nodes' data (:attr:`path`, :attr:`depth`) will be
            ignored.

        .. note::

            If your node model has :attr:`node_order_by` enabled, it will
            take precedence over the order in the structure.

        """

        # tree, iterative preorder
        added = []
        # stack of nodes to analize
        stack = [(parent, node) for node in bulk_data[::-1]]
        while stack:
            parent, node_struct = stack.pop()
            node_data = node_struct['data']
            if parent:
                node_obj = parent.add_child(**node_data)
            else:
                node_obj = cls.add_root(**node_data)
            added.append(node_obj.path)
            if 'children' in node_struct:
                # extending the stack with the current node as the parent of
                # the new nodes
                stack.extend([(node_obj, node) \
                    for node in node_struct['children'][::-1]])
        transaction.commit_unless_managed()
        return added


    @classmethod
    def get_root_nodes(cls):
        """
        :returns: A queryset containing the root nodes in the tree.
        """
        return cls.objects.filter(depth=1)
    

    @classmethod
    def get_first_root_node(cls):
        """
        :returns: The first root node in the tree or None if it is empty
        """
        try:
            return cls.get_root_nodes()[0]
        except IndexError:
            return None


    @classmethod
    def get_last_root_node(cls):
        """
        :returns: The last root node in the tree or None if it is empty
        """
        try:
            return cls.get_root_nodes().reverse()[0]
        except IndexError:
            return None


    def get_siblings(self):
        """
        :returns: A queryset of all the node's siblings, including the node
            itself.
        """
        qset = self.__class__.objects.filter(depth=self.depth)
        if self.depth > 1:
            # making sure the non-root nodes share a parent
            parentpath = self._get_basepath(self.path, self.depth-1)
            qset = qset.filter(
                path__range=self._get_children_path_interval(parentpath))
        return qset


    def get_children(self):
        """
        :returns: A queryset of all the node's children
        """
        if self.numchild:
            return self.__class__.objects.filter(depth=self.depth+1,
                path__range=self._get_children_path_interval(self.path))
        return self.__class__.objects.none()


    def get_descendants(self):
        """
        :returns: A queryset of all the node's descendants as DFS, doesn't
            include the node itself
        """
        if self.numchild:
            return self.__class__.objects.filter(path__startswith=self.path,
                                             depth__gt=self.depth)
        return self.__class__.objects.none()


    def get_first_child(self):
        """
        :returns: The leftmost node's child, or None if it has no children.
        """
        try:
            return self.get_children()[0]
        except IndexError:
            return None


    def get_last_child(self):
        """
        :returns: The rightmost node's child, or None if it has no children.
        """
        try:
            return self.get_children().reverse()[0]
        except IndexError:
            return None


    def get_first_sibling(self):
        """
        :returns: The leftmost node's sibling, can return the node itself if it
            was the leftmost sibling.
        """
        return self.get_siblings()[0]


    def get_last_sibling(self):
        """
        :returns: The rightmost node's sibling, can return the node itself if it
            was the rightmost sibling.
        """
        return self.get_siblings().reverse()[0]


    def get_prev_sibling(self):
        """
        :returns: The previous node's sibling, or None if it was the leftmost
            sibling.
        """
        try:
            return self.get_siblings().filter(path__lt=self.path).reverse()[0]
        except IndexError:
            return None


    def get_next_sibling(self):
        """
        :returns: The next node's sibling, or None if it was the rightmost
            sibling.
        """
        try:
            return self.get_siblings().filter(path__gt=self.path)[0]
        except IndexError:
            return None


    def is_sibling_of(self, node):
        """
        :returns: ``True`` if the node if a sibling of another node given as an
            argument, else, returns ``False``

        :param node:
        
            The node that will be checked as a sibling
        """
        aux = self.depth == node.depth
        if self.depth > 1:
            # making sure the non-root nodes share a parent
            parentpath = self._get_basepath(self.path, self.depth-1)
            return aux and node.path.startswith(parentpath)
        return aux


    def is_child_of(self, node):
        """
        :returns: ``True`` if the node if a child of another node given as an
            argument, else, returns ``False``

        :param node:

            The node that will be checked as a parent
        """
        return self.path.startswith(node.path) and self.depth == node.depth+1


    def is_descendant_of(self, node):
        """
        :returns: ``True`` if the node if a descendant of another node given
            as an argument, else, returns ``False``

        :param node:

            The node that will be checked as an ancestor
        """
        return self.path.startswith(node.path) and self.depth > node.depth


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

        """

        if self.numchild and self.node_order_by:
            # there are child nodes and node_order_by has been set
            # delegate sorted insertion to add_sibling
            return self.get_last_child().add_sibling(SORTEDS, **kwargs)

        # creating a new object
        newobj = self.__class__(**kwargs)
        newobj.depth = self.depth + 1
        if self.numchild:
            # adding the new child as the last one
            newobj.path = self._inc_path(self.get_last_child().path)
        else:
            # the node had no children, adding the first child
            newobj.path = self._get_path(self.path, newobj.depth, 1)
        # saving the instance before returning it
        newobj.save()
        newobj._parent_obj = self
        self.numchild += 1
        self.save()
        return newobj


    def _get_sorted_pos_queryset(self, siblings, newobj):
        """
        :returns: The position a new node will be inserted related to the
        current node, and also a queryset of the nodes that must be moved
        to the right. Called only for Node models with :attr:`node_order_by`

        This function was taken from django-mptt (BSD licensed) by Jonathan Buchanan:
        http://code.google.com/p/django-mptt/source/browse/trunk/mptt/signals.py?spec=svn100&r=100#12
        """

        fields, filters = [], []
        for field in self.node_order_by:
            value = getattr(newobj, field)
            filters.append(Q(*
                [Q(**{f: v}) for f, v in fields] +
                [Q(**{'%s__gt' % field: value})]))
            fields.append((field, value))
        siblings = siblings.filter(reduce(operator.or_, filters))
        try:
            newpos = self._get_lastpos_in_path(siblings.all()[0].path)
        except IndexError:
            newpos, siblings = None, []
        return newpos, siblings


    def add_sibling(self, pos=None, **kwargs):
        """
        Adds a new node as a sibling to the current node object.


        :param pos:
            The position, relative to the current node object, where the
            new node will be inserted, can be one of:

            - first-sibling: the new node will be the new leftmost sibling
            - left: the new node will take the node's place, which will be
              moved to the right 1 position
            - right: the new node will be inserted at the right of the node
            - last-sibling: the new node will be the new rightmost sibling
            - sorted-sibling: the new node will be at the right position
              according to the value of node_order_by

        :param \*\*kwargs: 
        
            Object creation data that will be passed to the inherited
            Node model

        :returns:
            
            The created node object. It will be saved by this method.

        """

        if pos is None:
            if self.node_order_by:
                pos = SORTEDS
            else:
                pos = LASTS
        if pos not in (FIRSTS, LEFTS, RIGHTS, LASTS, SORTEDS):
            raise InvalidPosition('Invalid relative position: %s' % (pos,))
        if self.node_order_by and pos != SORTEDS:
            raise InvalidPosition('Must use %s in add_sibling when'
                                  ' node_order_by is enabled' % (SORTEDS,))

        # creating a new object
        newobj = self.__class__(**kwargs)
        newobj.depth = self.depth
        
        if pos == SORTEDS:
            newpos, siblings = self._get_sorted_pos_queryset(
                self.get_siblings(), newobj)
            if newpos is None:
                pos = LASTS
        else:
            newpos, siblings = None, []

        stmts = []
        _, newpath = self._move_add_sibling_aux(pos, newpos,
            self.depth, self, siblings, stmts, None, False)

        parentpath = self._get_basepath(newpath, self.depth-1)
        if parentpath:
            stmts.append(self._get_sql_update_numchild(parentpath, 'inc'))

        cursor = connection.cursor()
        for sql, vals in stmts:
            cursor.execute(sql, vals)

        # saving the instance before returning it
        newobj.path = newpath
        newobj.save()

        transaction.commit_unless_managed()
        return newobj


    def get_root(self):
        """
        :returns: the root node for the current node object.
        """
        return self.__class__.objects.get(path=self.path[0:self.steplen])


    def get_ancestors(self):
        """
        :returns: A queryset containing the current node object's ancestors,
            starting by the root node and descending to the parent.
        """
        paths = [self.path[0:pos] 
            for pos in range(0, len(self.path), self.steplen)[1:]]
        return self.__class__.objects.filter(path__in=paths).order_by('depth')


    def get_parent(self, update=False):
        """
        :returns: the parent node of the current node object.
            Caches the result in the object itself to help in loops.
        
        :param update: Updates de cached value.

        """
        if self.depth <= 1:
            return
        try:
            if update:
                del self._parent_obj
            else:
                return self._parent_obj
        except AttributeError:
            pass
        parentpath = self._get_basepath(self.path, self.depth-1)
        self._parent_obj = self.__class__.objects.get(path=parentpath)
        return self._parent_obj



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

            - `first-child`: the node will be the new leftmost child of the
              `target` node
            - `last-child`: the node will be the new rightmost child of the
              `target` node
            - `sorted-child`: the new node will be moved as a child of the
              `target` node according to the value of :attr:`node_order_by`
            - `first-sibling`: the node will be the new leftmost sibling of the
              `target` node
            - `left`: the node will take the `target` node's place, which will be
              moved to the right 1 position
            - `right`: the node will be moved to the right of the `target` node
            - `last-sibling`: the node will be the new rightmost sibling of the
              `target node`
            - `sorted-sibling`: the new node will be moved as a sibling of the
              `target` node according to the value of :attr:`node_order_by`

            .. note:: If no `pos` is given the library will use
                     `last-sibling`, or `sorted-sibling` if
                     :attr:`node_order_by` is enabled.
        """
        if pos is None:
            if self.node_order_by:
                pos = SORTEDS
            else:
                pos = LASTS
        if pos not in (FIRSTS, LEFTS, RIGHTS, LASTS, SORTEDS,
                       FIRSTC, LASTC, SORTEDC):
            raise InvalidPosition('Invalid relative position: %s' % (pos,))
        if self.node_order_by and pos not in (SORTEDC, SORTEDS):
            raise InvalidPosition('Must use %s or %s in add_sibling when'
                                  ' node_order_by is enabled' % (SORTEDS,
                                  SORTEDC))
        oldpath = self.path

        # initialize variables and if moving to a child, updates "move to
        # child" to become a "move to sibling" if possible (if it can't
        # be done, it means that we are  adding the first child)
        pos, target, newdepth, siblings, newpos = self._fix_move_to_child(pos,
            target, target.depth)

        if target.is_descendant_of(self):
            raise InvalidMoveToDescendant("Can't move node to a descendant.")

        if oldpath == target.path and (
              (pos == LEFTS) or \
              (pos in (RIGHTS, LASTS) and \
                target.path == target.get_last_sibling().path) or \
              (pos == FIRSTS and \
                target.path == target.get_first_sibling().path)):
            # special cases, not actually moving the node so no need to UPDATE
            return
        
        if pos == SORTEDS:
            newpos, siblings = self._get_sorted_pos_queryset(
                target.get_siblings(), self)
            if newpos is None:
                pos = LASTS

        stmts = []
        # generate the sql that will do the actual moving of nodes
        oldpath, newpath = self._move_add_sibling_aux(pos, newpos, newdepth,
            target, siblings, stmts, oldpath, True)
        # updates needed for mysql and children count in parents
        self._updates_after_move(oldpath, newpath, stmts)

        cursor = connection.cursor()
        for sql, vals in stmts:
            cursor.execute(sql, vals)
        transaction.commit_unless_managed()


    def delete(self):
        """
        Removes a node and all it's descendants.
        """
        # call our queryset's delete to handle children removal and updating
        # the parent's numchild
        self.__class__.objects.filter(
            path=self.path).delete()



    @classmethod
    def _get_basepath(cls, path, depth):
        """
        :returns: The base path of another path up to a given depth
        """
        if path:
            return path[0:(depth)*cls.steplen]
        return ''


    @classmethod
    def _get_path(cls, path, depth, newstep):
        """
        Builds a path given some values

        :param path: the base path
        :param depth: the depth of the parent node
        :param newstep: the value (integer) of the new step
        """
        parentpath = cls._get_basepath(path, depth-1)
        key = int2str(newstep, len(cls.alphabet), cls.alphabet)
        return '%s%s%s' % (parentpath, '0'*(cls.steplen-len(key)), key)


    @classmethod
    def _inc_path(cls, path):
        """
        :returns: The path of the next sibling of a given node path.
        """
        base = len(cls.alphabet)
        key = int2str(str2int(path[-cls.steplen:], base, cls.alphabet)+1, base,
                      cls.alphabet)
        return '%s%s%s' % (path[:-cls.steplen], '0'*(cls.steplen-len(key)), key)


    @classmethod
    def _get_lastpos_in_path(cls, path):
        """
        :returns: The integer value of the last step in a path.
        """
        return str2int(path[-cls.steplen:], len(cls.alphabet), cls.alphabet)


    @classmethod
    def _get_parent_path_from_path(cls, path):
        """
        :returns: The parent path for a given path
        """
        if path:
            return path[0:len(path)-cls.steplen]
        return ''


    @classmethod
    def _get_children_path_interval(cls, path):
        """
        :returns: An interval of all possible children paths for a node.
        """
        return (path+cls.alphabet[0]*cls.steplen,
                path+cls.alphabet[-1]*cls.steplen)

    
    @classmethod
    def _move_add_sibling_aux(cls, pos, newpos, newdepth, target, siblings,
                              stmts, oldpath=None, movebranch=False):
        """
        Handles the reordering of nodes and branches when adding/moving
        nodes.

        :returns: A tuple containing the old path and the new path.
        """
        if pos == LASTS \
                or (pos == RIGHTS and target == target.get_last_sibling()):
            # easy, the last node
            last = target.get_last_sibling()
            newpath = cls._inc_path(last.path)
            if movebranch:
                stmts.append(cls._get_sql_newpath_in_branches(oldpath, newpath))
        else:
            # do the UPDATE dance

            if newpos is None:
                siblings = target.get_siblings()
                siblings = {LEFTS:siblings.filter(path__gte=target.path),
                            RIGHTS:siblings.filter(path__gt=target.path),
                            FIRSTS:siblings}[pos]
                basenum = cls._get_lastpos_in_path(target.path)
                newpos = {FIRSTS:1, LEFTS:basenum, RIGHTS:basenum+1}[pos]

            newpath = cls._get_path(target.path, newdepth, newpos)

            for node in siblings.reverse():
                # moving the siblings (and their branches) at the right of the
                # related position one step to the right
                sql, vals = cls._get_sql_inc_path_in_branches(node.path)
                stmts.append((sql, vals))

                if movebranch:
                    if oldpath.startswith(node.path):
                        # if moving to a parent, update oldpath since we just
                        # increased the path of the entire branch
                        oldpath = vals[0] + oldpath[len(vals[0]):]
                    if target.path.startswith(node.path):
                        # and if we moved the target, update the object
                        # django made for us, since the update won't do it
                        # maybe useful in loops
                        target.path = vals[0] + target.path[len(vals[0]):]
            if movebranch:
                # node to move
                stmts.append(cls._get_sql_newpath_in_branches(oldpath,
                                                               newpath))
        return oldpath, newpath


    def _fix_move_to_child(self, pos, target, newdepth):
        """
        Update preliminar vars in :meth:`move` when moving to a child
        """
        newdepth = target.depth
        parent = None
        newpos = None
        siblings = []
        if pos in (FIRSTC, LASTC, SORTEDC):
            # moving to a child
            parent = target
            newdepth += 1
            if target.numchild:
                target = target.get_last_child()
                pos = {FIRSTC:FIRSTS, LASTC:LASTS, SORTEDC:SORTEDS}[pos]
            else:
                # moving as a target's first child
                newpos = 1
                pos = FIRSTS
                siblings = self.__class__.objects.none()
            # this is not for save(), since if needed, will be handled with a
            # custom UPDATE, this is only here to update django's object,
            # should be useful in loops
            parent.numchild += 1
            parent = None

        return pos, target, newdepth, siblings, newpos


    @classmethod
    def _updates_after_move(cls, oldpath, newpath, stmts):
        """
        
        Updates the list of sql statements needed after moving nodes.

        1. :attr:`depth` updates *ONLY* needed by mysql databases (*sigh*)
        2. update the number of children of parent nodes
        """
        if settings.DATABASE_ENGINE == 'mysql' and len(oldpath) != len(newpath):
            # no words can describe how dumb mysql is
            # we must update the depth of the branch in a different query
            stmts.append(cls._get_sql_update_depth_in_branch(newpath))

        oldparentpath = cls._get_parent_path_from_path(oldpath)
        newparentpath = cls._get_parent_path_from_path(newpath)
        if (not oldparentpath and newparentpath) or \
               (oldparentpath and not newparentpath) or \
               (oldparentpath != newparentpath):
            # node changed parent, updating count
            if oldparentpath:
                stmts.append(cls._get_sql_update_numchild(oldparentpath,
                                                           'dec'))
            if newparentpath:
                stmts.append(cls._get_sql_update_numchild(newparentpath,
                                                           'inc'))


    @classmethod
    def _get_sql_newpath_in_branches(cls, oldpath, newpath):
        """
        :returns" The sql needed to move a branch to another position.

        .. note::

           The generated sql will only update the depth values if needed.

        """
        
        sql1 = "UPDATE %s SET" % (cls._meta.db_table,)

        # <3 "standard" sql
        if settings.DATABASE_ENGINE == 'sqlite3':
            # I know that the third argument in SUBSTR (LENGTH(path)) is
            # awful, but sqlite fails without it:
            # OperationalError: wrong number of arguments to function substr()
            # even when the documentation says that 2 arguments are valid:
            # http://www.sqlite.org/lang_corefunc.html
            sqlpath = "%s||SUBSTR(path, %s, LENGTH(path))"
        elif settings.DATABASE_ENGINE == 'mysql':
            # hooray for mysql ignoring standards in their default
            # configuration!
            # to make || work as it should, enable ansi mode
            # http://dev.mysql.com/doc/refman/5.0/en/ansi-mode.html
            sqlpath = "CONCAT(%s, SUBSTR(path, %s))"
        else:
            sqlpath = "%s||SUBSTR(path, %s)"

        sql2 = ["path=%s" % (sqlpath,)]
        vals = [newpath, len(oldpath)+1]
        if len(oldpath) != len(newpath) and settings.DATABASE_ENGINE != 'mysql':
            # when using mysql, this won't update the depth and it has to be
            # done in another query
            # doesn't even work with sql_mode='ANSI,TRADITIONAL'
            # TODO: FIND OUT WHY?!?? right now I'm just blaming mysql
            sql2.append("depth=LENGTH(%s)/%%s" % (sqlpath,))
            vals.extend([newpath, len(oldpath)+1, cls.steplen])
        sql3 = "WHERE path LIKE %s"   
        vals.extend([oldpath+'%'])
        sql = '%s %s %s' % (sql1, ', '.join(sql2), sql3)
        return sql, vals


    @classmethod
    def _get_sql_inc_path_in_branches(cls, oldpath):
        """
        :returns: The sql needed to move a branch 1 position to the right.
        """
        newpath = cls._inc_path(oldpath)
        return cls._get_sql_newpath_in_branches(oldpath, newpath)


    @classmethod
    def _get_sql_update_depth_in_branch(cls, path):
        """
        :returns: The sql needed to update the depth of all the nodes in a
                  branch.
        """

        # Right now this is only used by *sigh* mysql.
        sql = "UPDATE %s SET depth=LENGTH(path)/%%s" \
              " WHERE path LIKE %%s" % (cls._meta.db_table,)
        vals = [cls.steplen, path+'%']
        return sql, vals

    
    @classmethod
    def _get_sql_update_numchild(cls, path, incdec='inc'):
        """
        :returns: The sql needed the numchild value of a node
        """
        sql = "UPDATE %s SET numchild=numchild%s1" \
              " WHERE path=%%s" % (cls._meta.db_table,
                                   {'inc':'+', 'dec':'-'}[incdec])
        vals = [path]
        return sql, vals




    class Meta:
        """
        Abstract model.
        """
        abstract = True
        # By changing the ordering, assume that lots of things will break,
        # at least you'll want to check the first/last/prev/next methods.
        # This ordering assumes you want something... TREEISH
        # PROTIP: don't change this
        ordering = ['path']


class InvalidPosition(Exception):
    """
    Raised when passing an invalid pos value (first, last, prev, next)
    """

class InvalidMoveToDescendant(Exception):
    """
    Raised when attemping to move a node to one of it's descendants.
    """



#~
