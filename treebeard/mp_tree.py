# -*- coding: utf-8 -*-
"""

    treebeard.mp_tree
    -----------------

    Materialized Path Tree.

    :copyright: 2008 by Gustavo Picon
    :license: Apache License 2.0

    This is an efficient implementation of Materialized Path
    trees for Django 1.0+, as described by `Vadim Tropashko`_ in `SQL Design
    Patterns`_. Materialized Path is probably the fastest way of working with
    trees in SQL without the need of extra work in the database, like Oracle's
    ``CONNECT BY`` or sprocs and triggers for nested intervals.

    In a materialized path approach, every node in the tree will have a
    :attr:`~MPNode.path` attribute, where the full path from the root
    to the node will be stored. This has the advantage of needing very simple
    and fast queries, at the risk of inconsistency because of the
    denormalization of ``parent``/``child`` foreign keys. This can be prevented
    with transactions (and of course you are already using them, right?).

    ``django-treebeard`` uses a particular approach: every step in the path has
    a fixed width and has no separators. This makes queries predictable and
    faster at the cost of using more characters to store a step. To attack this
    problem, every step number is encoded.

    Also, two extra fields are stored in every node:
    :attr:`~MPNode.depth` and :attr:`~MPNode.numchild`.
    This makes the read operations faster, at the cost of a little more
    maintenance on tree updates/inserts/deletes. Don't worry, even with these
    extra steps, materialized path is more efficient than other approaches.

    .. note::
       
       The materialized path approach makes heavy use of ``LIKE`` in your
       database, with clauses like ``WHERE path LIKE '002003%'``. If you think
       that ``LIKE`` is too slow, you're right, but in this case the
       :attr:`~MPNode.path` field is indexed in the database, and all
       ``LIKE`` clauses that don't **start** with a ``%`` character will use the
       index. This is what makes the materialized path approach so fast.


    .. _`Vadim Tropashko`: http://vadimtropashko.wordpress.com/
    .. _`Sql Design Patterns`:
       http://www.rampant-books.com/book_2006_1_sql_coding_styles.htm
    .. _`Django Model Inheritance with abstract classes`:
      http://docs.djangoproject.com/en/dev/topics/db/models/#abstract-base-classes
"""

import operator
import numconv

from django.core import serializers
from django.db import models, transaction, connection
from django.db.models import Q
from django.conf import settings

from treebeard import Node, InvalidPosition, InvalidMoveToDescendant, \
    PathOverflow, MissingNodeOrderBy


class MPNodeQuerySet(models.query.QuerySet):
    """
    Custom queryset for the tree node manager.

    Needed only for the customized delete method.
    """


    def delete(self, known_children=False):
        """
        Custom delete method, will remove all descendant nodes to ensure a
        consistent tree (no orphans)

        :returns: ``None``
        """
        if known_children:
            # we already know the children, let's call the default django
            # delete method and let it handle the removal of the user's
            # foreign keys...
            super(MPNodeQuerySet, self).delete()
        else:
            # we'll have to manually run through all the nodes that are going
            # to be deleted and remove nodes from the list if an ancestor is
            # already getting removed, since that would be redundant
            removed = {}
            for node in self.order_by('depth', 'path'):
                found = False
                for depth in range(1, len(node.path)/node.steplen):
                    path = node._get_basepath(node.path, depth)
                    if path in removed:
                        # we are already removing a parent of this node
                        # skip
                        found = True
                        break
                if not found:
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
                    if parent and parent.numchild > 0:
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



class MPNodeManager(models.Manager):
    """ Custom manager for nodes.
    """

    def get_query_set(self):
        """
        Sets the custom queryset as the default.
        """
        return MPNodeQuerySet(self.model)


class MPNode(Node):
    """
    Abstract model to create your own tree models.

    .. attribute:: steplen
       
       Attribute that defines the length of each step in the :attr:`path` of
       a node.  The default value of *4* allows a maximum of
       *1679615* children per node. Increase this value if you plan to store
       large trees (a ``steplen`` of *5* allows more than *60M* children per
       node). Note that increasing this value, while increasing the number of
       children per node, will decrease the max :attr:`depth` of the tree (by
       default: *63*). To increase the max :attr:`depth`, increase the
       max_length attribute of the :attr:`path` field in your model.

    .. attribute:: alphabet

       Attribute: the alphabet that will be used in base conversions
       when encoding the path steps into strings. The default value,
       ``0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ`` is the most optimal possible
       value that is portable between the supported databases (which means:
       their default collation will order the :attr:`path` field correctly).

       .. note::

          In case you know what you are doing, there is a test that is disabled
          by default that can tell you the optimal default alphabet in your
          enviroment. To run the test you must enable the
          :envvar:`TREEBEARD_TEST_ALPHABET` enviroment variable::
       
             $ TREEBEARD_TEST_ALPHABET=1 python manage.py test treebeard.TestTreeAlphabet

          On my Ubuntu 8.04.1 system, these are the optimal values for the three
          supported databases in their *default* configuration:

           ================ ==============================================================
           Database         Optimal Alphabet
           ================ ==============================================================
           MySQL 5.0.51     0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ
           PostgreSQL 8.2.7 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ
           Sqlite3          0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz
           ================ ==============================================================

    .. attribute:: node_order_by

       Attribute: a list of model fields that will be used for node
       ordering. When enabled, all tree operations will assume this ordering.

       Example::

          node_order_by = ['field1', 'field2', 'field3']

    .. attribute:: path
        
       ``CharField``, stores the full materialized path for each node. The
       default value of it's max_length, *255*, is the max efficient and
       portable value for a ``varchar``. Increase it to allow deeper trees (max
       depth by default: *63*)

       .. note::
          
          `django-treebeard` uses Django's abstract model inheritance, so:

          1. To change the max_length value of the path in your model, you
             can't just define it since you'd get a django exception, you have
             to modify the already defined attribute::

               class MyNodeModel(MPNode):
                   pass

               MyNodeModel._meta.get_field('path').max_length = 1024
          2. You can't rely on Django's `auto_now` properties in date fields
             for sorting, you'll have to manually set the value before creating
             a node::

               
               class TestNodeSortedAutoNow(MPNode):
                   desc = models.CharField(max_length=255)
                   created = models.DateTimeField(auto_now_add=True)
                   node_order_by = ['created']

               TestNodeSortedAutoNow.add_root(desc='foo',
                                              created=datetime.datetime.now())

       .. note::

          For performance, and if your database allows it, you can safely
          define the path column as ASCII (not utf-8/unicode/iso8859-1/etc) to
          keep the index smaller (and faster). Also note that some databases
          (mysql) have a small index size limit. InnoDB for instance has a
          limit of 765 bytes per index, so that would be the limit if your path
          is ASCII encoded. If your path column in InnoDB is using unicode,
          the index limit will be 255 characters since in MySQL's indexes,
          unicode means 3 bytes.



       .. note::

          treebeard uses **numconv** for path encoding:
          http://code.google.com/p/numconv/

    .. attribute:: depth

       ``PositiveIntegerField``, depth of a node in the tree. A root node
       has a depth of *1*.

    .. attribute:: numchild

       ``PositiveIntegerField``, the number of children of the node.


    .. warning::
       
       Do not change the values of :attr:`path`, :attr:`depth` or
       :attr:`numchild` directly: use one of the included methods instead.
       Consider these values *read-only*.

    .. warning::

       Do not change the values of the :attr:`steplen`, :attr:`alphabet` or
       :attr:`node_order_by` after saving your first model. Doing so will
       corrupt the tree. If you *must* do it:
         
         1. Backup the tree with :meth:`dump_bulk`
         2. Empty your model's table
         3. Change :attr:`depth`, :attr:`alphabet` and/or
            :attr:`node_order_by` in your model
         4. Restore your backup using :meth:`load_bulk` with
            ``keep_ids=True`` to keep the same primary keys you had.

    Example::

       class SortedNode(MPNode):
          node_order_by = ['numval', 'strval']

          numval = models.IntegerField()
          strval = models.CharField(max_length=255)

    """

    steplen = 4
    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    node_order_by = []

    path = models.CharField(max_length=255,
                            unique=True)
    depth = models.PositiveIntegerField()
    numchild = models.PositiveIntegerField(default=0)

    objects = MPNodeManager()


    @classmethod
    def add_root(cls, **kwargs):
        """
        Adds a root node to the tree.

        See: :meth:`treebeard.Node.add_root`

        :raise PathOverflow: when no more root objects can be added
        """

        # do we have a root node already?
        last_root = cls.get_last_root_node()

        if last_root and last_root.node_order_by:
            # there are root nodes and node_order_by has been set
            # delegate sorted insertion to add_sibling
            return last_root.add_sibling('sorted-sibling', **kwargs)

        if last_root:
            # adding the new root node as the last one
            newpath = cls._inc_path(last_root.path)
        else:
            # adding the first root node
            newpath = cls._get_path(None, 1, 1)
        # creating the new object
        newobj = cls(**kwargs)
        newobj.depth = 1
        newobj.path = newpath
        # saving the instance before returning it
        newobj.save()
        transaction.commit_unless_managed()
        return newobj


    @classmethod
    def load_bulk(cls, bulk_data, parent=None, keep_ids=False):
        """
        Loads a list/dictionary structure to the tree.

        See: :meth:`treebeard.Node.load_bulk`
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

        See: :meth:`treebeard.Node.dump_bulk`
        """

        # Because of fix_tree, this method assumes that the depth
        # and numchild properties in the nodes can be incorrect,
        # so no helper methods are used
        if parent:
            qset = cls.objects.filter(path__startswith=parent.path)
        else:
            qset = cls.objects.all()
        ret, lnk = [], {}
        for pyobj in serializers.serialize('python', qset):
            # django's serializer stores the attributes in 'fields'
            fields = pyobj['fields']
            path = fields['path']
            depth = len(path)/cls.steplen
            # this will be useless in load_bulk
            del fields['depth']
            del fields['path']
            del fields['numchild']
            if 'id' in fields:
                # this happens immediately after a load_bulk
                del fields['id']

            newobj = {'data':fields}
            if keep_ids:
                newobj['id'] = pyobj['pk']

            if (not parent and depth == 1) or \
                    (parent and len(path) == len(parent.path)):
                ret.append(newobj)
            else:
                parentpath = cls._get_basepath(path, depth-1)
                parentobj = lnk[parentpath]
                if 'children' not in parentobj:
                    parentobj['children'] = []
                parentobj['children'].append(newobj)
            lnk[path] = newobj
        return ret


    @classmethod
    def find_problems(cls):
        """
        Checks for problems in the tree structure, problems can occur when:

           1. your code breaks and you get incomplete transactions (always
              use transactions!)
           2. changing the ``steplen`` value in a model (you must :meth:`dump_bulk`
              first, change ``steplen`` and then :meth:`load_bulk`

        :returns: A tuple of three lists:
                  
                  1. a list of ids of nodes with characters not found in the
                     ``alphabet``
                  2. a list of ids of nodes when a wrong ``path`` length
                     according to ``steplen``
                  3. a list of ids of orphaned nodes

        .. note::
           
           These problems can't be solved automatically.

        Example::

           MyNodeModel.find_problems()

        """
        evil_chars, bad_steplen, orphans = [], [], []
        for node in cls.objects.all():
            found_error = False
            for char in node.path:
                if char not in cls.alphabet:
                    evil_chars.append(node.id)
                    found_error = True
                    break
            if found_error:
                continue
            if len(node.path) % cls.steplen:
                bad_steplen.append(node.id)
                continue
            try:
                parent = node.get_parent(True)
            except cls.DoesNotExist:
                orphans.append(node.id)

        return evil_chars, bad_steplen, orphans


    @classmethod
    def fix_tree(cls):
        """
        Solves some problems that can appear when transactions are not used and
        a piece of code breaks, leaving the tree in an inconsistent state.

        The problems this method solves are:
        
           1. Nodes with an incorrect ``level`` or ``numchild`` values due to
              incorrect code and lack of database transactions.
           2. "Holes" in the tree. This is normal if you move/delete nodes a
              lot. Holes in a tree don't affect performance,
           3. Incorrect ordering of nodes when ``node_order_by`` is enabled.
              Ordering is enforced on *node insertion*, so if an attribute in
              ``node_order_by`` is modified after the node is inserted, the
              tree ordering will be inconsistent.

        If these problems don't apply to you, you'll never need to use this
        method.

        .. note::

           Currently what this method does is:

           1. Backup the tree with :meth:`dump_data`
           2. Remove all nodes in the tree.
           3. Restore the tree with :meth:`load_data`

           So, even when the primary keys of your nodes will be preserved, this
           method isn't foreign-key friendly. That needs complex in-place
           tree reordering, not available at the moment (hint: patches are
           welcome).

        Example::

           MyNodeModel.fix_tree()


        """
        dump = cls.dump_bulk(None, True)
        cls.objects.all().delete()
        cls.load_bulk(dump, None, True)



    @classmethod
    def get_descendants_group_count(cls, parent=None):
        """
        Helper for a very common case: get a group of siblings and the number
        of *descendants* in every sibling.

        See: :meth:`treebeard.Node.get_descendants_group_count`
        """

        #~
        # disclaimer: this is the FOURTH implementation I wrote for this
        # function. I really tried to make it return a queryset, but doing so
        # with a *single* query isn't trivial with Django's ORM.

        # ok, I DID manage to make Django's ORM return a queryset here,
        # defining two querysets, passing one subquery in the tables parameters
        # of .extra() of the second queryset, using the undocumented order_by
        # feature, and using a HORRIBLE hack to avoid django quoting the
        # subquery as a table, BUT (and there is always a but) the hack didn't
        # survive turning the QuerySet into a ValuesQuerySet, so I just used
        # good old SQL.
        # NOTE: in case there is interest, the hack to avoid django quoting the
        # subquery as a table, was adding the subquery to the alias cache of
        # the queryset's query object:
        # 
        #     qset.query.quote_cache[subquery] = subquery
        #
        # If there is a better way to do this in an UNMODIFIED django 1.0, let
        # me know.
        #~

        if parent:
            depth = parent.depth + 1
            params = cls._get_children_path_interval(parent.path)
            extrand = 'AND path BETWEEN %s AND %s'
        else:
            depth = 1
            params = []
            extrand = ''

        sql = 'SELECT * FROM %(table)s AS t1 INNER JOIN ' \
              ' (SELECT ' \
              '   SUBSTR(path, 1, %(subpathlen)s) AS subpath, ' \
              '   COUNT(1)-1 AS count ' \
              '   FROM %(table)s ' \
              '   WHERE depth >= %(depth)s %(extrand)s' \
              '   GROUP BY subpath) AS t2 ' \
              ' ON t1.path=t2.subpath ' \
              ' ORDER BY t1.path' % {'table': cls._meta.db_table,
                                     'subpathlen': depth*cls.steplen,
                                     'depth': depth,
                                     'extrand': extrand}
        cursor = connection.cursor()
        cursor.execute(sql, params)

        ret = []
        field_names = [field[0] for field in cursor.description]
        for node_data in cursor.fetchall():
            node = cls(**dict(zip(field_names, node_data[:-2])))
            node.descendants_count = node_data[-1]
            ret.append(node)
        transaction.commit_unless_managed()
        return ret


    def get_siblings(self):
        """
        :returns: A queryset of all the node's siblings, including the node
            itself.

        See: :meth:`treebeard.Node.get_siblings`
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

        See: :meth:`treebeard.Node.get_children`
        """
        if self.numchild:
            return self.__class__.objects.filter(depth=self.depth+1,
                path__range=self._get_children_path_interval(self.path))
        return self.__class__.objects.none()


    def get_descendants(self):
        """
        :returns: A queryset of all the node's descendants as DFS, doesn't
            include the node itself

        See: :meth:`treebeard.Node.get_descendants`
        """
        if self.numchild:
            return self.__class__.objects.filter(path__startswith=self.path,
                                             depth__gt=self.depth)
        return self.__class__.objects.none()


    def get_prev_sibling(self):
        """
        :returns: The previous node's sibling, or None if it was the leftmost
            sibling.

        See: :meth:`treebeard.Node.get_prev_sibling`
        """
        try:
            return self.get_siblings().filter(path__lt=self.path).reverse()[0]
        except IndexError:
            return None


    def get_next_sibling(self):
        """
        :returns: The next node's sibling, or None if it was the rightmost
            sibling.

        See: :meth:`treebeard.Node.get_next_sibling`
        """
        try:
            return self.get_siblings().filter(path__gt=self.path)[0]
        except IndexError:
            return None


    def is_sibling_of(self, node):
        """
        :returns: ``True`` if the node if a sibling of another node given as an
            argument, else, returns ``False``

        See: :meth:`treebeard.Node.is_sibling_of`
        """
        aux = self.depth == node.depth
        if self.depth > 1:
            # making sure the non-root nodes share a parent
            parentpath = self._get_basepath(self.path, self.depth-1)
            return aux and node.path.startswith(parentpath)
        return aux


    def is_child_of(self, node):
        """
        :returns: ``True`` is the node if a child of another node given as an
            argument, else, returns ``False``

        See: :meth:`treebeard.Node.is_child_of`
        """
        return self.path.startswith(node.path) and self.depth == node.depth+1


    def is_descendant_of(self, node):
        """
        :returns: ``True`` if the node if a descendant of another node given
            as an argument, else, returns ``False``

        See: :meth:`treebeard.Node.is_descendant_of`
        """
        return self.path.startswith(node.path) and self.depth > node.depth


    def add_child(self, **kwargs):
        """
        Adds a child to the node.

        See: :meth:`treebeard.Node.add_child`

        :raise PathOverflow: when no more child nodes can be added
        """

        if self.numchild and self.node_order_by:
            # there are child nodes and node_order_by has been set
            # delegate sorted insertion to add_sibling
            return self.get_last_child().add_sibling('sorted-sibling', **kwargs)

        # creating a new object
        newobj = self.__class__(**kwargs)
        newobj.depth = self.depth + 1
        if self.numchild:
            # adding the new child as the last one
            newobj.path = self._inc_path(self.get_last_child().path)
        else:
            # the node had no children, adding the first child
            newobj.path = self._get_path(self.path, newobj.depth, 1)
            if len(newobj.path) > \
                    newobj.__class__._meta.get_field('path').max_length:
                raise PathOverflow('The new node is too deep in the tree, try'
                                   ' increasing the path.max_length property'
                                   ' and UPDATE your  database')
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

        See: :meth:`treebeard.Node.add_sibling`

        :raise PathOverflow: when the library can't make room for the
           node's new position
        """

        if pos is None:
            if self.node_order_by:
                pos = 'sorted-sibling'
            else:
                pos = 'last-sibling'
        if pos not in ('first-sibling', 'left', 'right', 'last-sibling', 'sorted-sibling'):
            raise InvalidPosition('Invalid relative position: %s' % (pos,))
        if self.node_order_by and pos != 'sorted-sibling':
            raise InvalidPosition('Must use %s in add_sibling when'
                                  ' node_order_by is enabled' % ('sorted-sibling',))
        if pos == 'sorted-sibling' and not self.node_order_by:
            raise MissingNodeOrderBy('Missing node_order_by attribute.')

        # creating a new object
        newobj = self.__class__(**kwargs)
        newobj.depth = self.depth
        
        if pos == 'sorted-sibling':
            newpos, siblings = self._get_sorted_pos_queryset(
                self.get_siblings(), newobj)
            if newpos is None:
                pos = 'last-sibling'
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

        See: :meth:`treebeard.Node.get_root`
        """
        return self.__class__.objects.get(path=self.path[0:self.steplen])


    def get_ancestors(self):
        """
        :returns: A queryset containing the current node object's ancestors,
            starting by the root node and descending to the parent.

        See: :meth:`treebeard.Node.get_ancestors`
        """
        paths = [self.path[0:pos] 
            for pos in range(0, len(self.path), self.steplen)[1:]]
        return self.__class__.objects.filter(path__in=paths).order_by('depth')


    def get_parent(self, update=False):
        """
        :returns: the parent node of the current node object.
            Caches the result in the object itself to help in loops.

        See: :meth:`treebeard.Node.get_parent`
        """
        depth = len(self.path)/self.steplen
        if depth <= 1:
            return
        try:
            if update:
                del self._parent_obj
            else:
                return self._parent_obj
        except AttributeError:
            pass
        parentpath = self._get_basepath(self.path, depth-1)
        self._parent_obj = self.__class__.objects.get(path=parentpath)
        return self._parent_obj



    def move(self, target, pos=None):
        """
        Moves the current node and all it's descendants to a new position
        relative to another node.

        See: :meth:`treebeard.Node.move`
        
        :raise PathOverflow: when the library can't make room for the
           node's new position
        """
        if pos is None:
            if self.node_order_by:
                pos = 'sorted-sibling'
            else:
                pos = 'last-sibling'
        if pos not in ('first-sibling', 'left', 'right', 'last-sibling', 'sorted-sibling',
                       'first-child', 'last-child', 'sorted-child'):
            raise InvalidPosition('Invalid relative position: %s' % (pos,))
        if self.node_order_by and pos not in ('sorted-child', 'sorted-sibling'):
            raise InvalidPosition('Must use %s or %s in add_sibling when'
                                  ' node_order_by is enabled' % ('sorted-sibling',
                                  'sorted-child'))
        if pos in ('sorted-child', 'sorted-sibling') and not self.node_order_by:
            raise MissingNodeOrderBy('Missing node_order_by attribute.')

        oldpath = self.path

        # initialize variables and if moving to a child, updates "move to
        # child" to become a "move to sibling" if possible (if it can't
        # be done, it means that we are  adding the first child)
        pos, target, newdepth, siblings, newpos = self._fix_move_to_child(pos,
            target, target.depth)

        if target.is_descendant_of(self):
            raise InvalidMoveToDescendant("Can't move node to a descendant.")

        if oldpath == target.path and (
              (pos == 'left') or \
              (pos in ('right', 'last-sibling') and \
                target.path == target.get_last_sibling().path) or \
              (pos == 'first-sibling' and \
                target.path == target.get_first_sibling().path)):
            # special cases, not actually moving the node so no need to UPDATE
            return
        
        if pos == 'sorted-sibling':
            newpos, siblings = self._get_sorted_pos_queryset(
                target.get_siblings(), self)
            if newpos is None:
                pos = 'last-sibling'

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
        :param depth: the depth of the  node
        :param newstep: the value (integer) of the new step
        """
        parentpath = cls._get_basepath(path, depth-1)
        key = numconv.int2str(newstep, len(cls.alphabet), cls.alphabet)
        return '%s%s%s' % (parentpath, '0'*(cls.steplen-len(key)), key)


    @classmethod
    def _inc_path(cls, path):
        """
        :returns: The path of the next sibling of a given node path.
        """
        base = len(cls.alphabet)
        newpos = numconv.str2int(path[-cls.steplen:], base, cls.alphabet) + 1
        key = numconv.int2str(newpos, base, cls.alphabet)
        if len(key) > cls.steplen:
            raise PathOverflow("Path Overflow from: '%s'" % (path,))
        return '%s%s%s' % (path[:-cls.steplen], '0'*(cls.steplen-len(key)),
                           key)


    @classmethod
    def _get_lastpos_in_path(cls, path):
        """
        :returns: The integer value of the last step in a path.
        """
        return numconv.str2int(path[-cls.steplen:], len(cls.alphabet),
                               cls.alphabet)


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
        if pos == 'last-sibling' \
                or (pos == 'right' and target == target.get_last_sibling()):
            # easy, the last node
            last = target.get_last_sibling()
            newpath = cls._inc_path(last.path)
            if movebranch:
                stmts.append(cls._get_sql_newpath_in_branches(oldpath, newpath))
        else:
            # do the UPDATE dance

            if newpos is None:
                siblings = target.get_siblings()
                siblings = {'left':siblings.filter(path__gte=target.path),
                            'right':siblings.filter(path__gt=target.path),
                            'first-sibling':siblings}[pos]
                basenum = cls._get_lastpos_in_path(target.path)
                newpos = {'first-sibling':1, 'left':basenum, 'right':basenum+1}[pos]

            newpath = cls._get_path(target.path, newdepth, newpos)

            for node in siblings.reverse():
                # moving the siblings (and their branches) at the right of the
                # related position one step to the right
                sql, vals = cls._get_sql_newpath_in_branches(node.path,
                    cls._inc_path(node.path))
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
        if pos in ('first-child', 'last-child', 'sorted-child'):
            # moving to a child
            parent = target
            newdepth += 1
            if target.numchild:
                target = target.get_last_child()
                pos = {'first-child':'first-sibling', 'last-child':'last-sibling', 'sorted-child':'sorted-sibling'}[pos]
            else:
                # moving as a target's first child
                newpos = 1
                pos = 'first-sibling'
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



#~
