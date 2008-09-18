# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------------
# django-treebeard
# Copyright (c) 2008 Gustavo Picon
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions 
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright 
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of django-treebeard nor the names of its
#    contributors may be used to endorse or promote products
#    derived from this software without specific prior written
#    permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------

"""

django-treebeard 1.0 - http://code.google.com/p/django-treebeard/

Efficient Materialized Path tree implementation for Django 1.0+

For examples on how to use this library, open the included tests.py file
or go to:
http://code.google.com/p/django-treebeard/source/browse/trunk/treebeard/tests.py
"""

import operator
from django.db import models, transaction, connection
from django.db.models import Q
from django.db.models.signals import post_init
from django.conf import settings
from numconv import int2str, str2int

PATH_FIELD_LENGTH = 255
BASE = 36
ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
FIRST, PREV, NEXT, LAST, SORTED = 'first', 'prev', 'next', 'last', 'sorted'


class Tree(models.Model):
    """
    Abstract model for the Tree objects.

    The library needs that you define a related name of 'treebeard_nodes' from
    your Node models. Read the docs of Node for more info.

    By default it defines no data fields or variables.
    """


    def __init__(self, *args, **kwargs):
        super(Tree, self).__init__(*args, **kwargs)
        if not hasattr(self, 'treebeard_nodes'):
            raise NeedOneNodeRelationPerTree('One shall be the number of node' \
                ' models thou shalt relate to a tree, and the number of the' \
                'relations shall be one.')
            # Two shalt thou not relate, neither count thou zero, excepting that
            # thou then proceed to one. Three is right out. Once the number
            # one, being the first number, be reached, the instance will be
            # created without this "pythonic" exception :)


    @transaction.commit_on_success
    def add_root(self, **kwargs):
        """
        Adds a root node to a tree. The new root node will be the new rightmost
        root node. If you want to insert a root node at a specific position,
        use the add_sibling method of an already existing root node instead.
        
        Returns the created node object. It will be save()d by this
        method.


        **kwargs: object creation data that will be passed to the inherited
            Node model
        """

        # do we have a root node already?
        last_root = self.get_last_root_node()

        if last_root and last_root.node_order_by:
            # there are root nodes and node_order_by has been set
            # delegate sorted insertion to add_sibling
            return last_root.add_sibling(SORTED, **kwargs)

        # creating the new object
        newobj = self.treebeard_nodes.model(**kwargs)
        newobj.depth = 1
        newobj.tree = self
        if last_root:
            # adding the new root node as the last one
            newobj.path = Node._inc_path(last_root.path, newobj.steplen)
        else:
            # adding the first root node
            newobj.path = Node._get_path(None, 1, 1, newobj.steplen)
        # saving the instance before returning it
        newobj.save()
        return newobj


    @transaction.commit_on_success
    def load_bulk(self, bulk_data, parent=None):
        """
        Loads a list/dictionary structure to a tree.
        Returns a list of the added node paths.


        parent: the node that will receive the structure as children, if not
            specified the first level of the structure will be loaded as root
            nodes

        bulk_data: the data that will be loaded, the structure is a list of
            dictionaries with 2 keys:
            - data: will store arguments that will be passed for object
              creation, and
            - children: a list of dictionaries, each one has it's own data and
              children keys (a recursive structure)
            Note that any internal data that you may have stored in your nodes'
            data (tree, full path, depth) will be ignored.
            The porpuse of this structure is to make it JSON friendly.


        For instance, this structure:
          [{'data':{'foo':'bar'}},
           {'data':{'foo':'baz'}, 'children':[
             {'data':{'foo':'qux'}},
             {'data':{'foo':'quux'}},
           ]},
           {'data':{'foo':'quuux'}}
          ]

        Will create:

             |------------|-----------|
            bar          baz         quuux
                          |
                    |-----------|
                   qux         quux
        
        Note that if your node model has "node_order_by enabled", it will
        take precedence over the order in the structure.

        """

        if parent and self != parent.tree:
            # You confused the library! now it doesn't know what you
            # really want so it'll play safe and just fail
            raise WrongTreeParm(
                "The parent's tree doesn't match the tree.")

        # tree, iterative preorder
        added = []
        # stack of nodes to analize
        stack = [(parent, node) for node in bulk_data[::-1]]
        while stack:
            parent, node_struct = stack.pop()
            node_data = node_struct['data']
            node_data['tree'] = self
            # this can break things, and it shouldn't be here anyway
            if 'tree_id' in node_data:
                del node_data['tree_id']
            if parent:
                node_obj = parent.add_child(**node_data)
            else:
                node_obj = self.add_root(**node_data)
            added.append(node_obj.path)
            if 'children' in node_struct:
                # extending the stack with the current node as the parent of
                # the new nodes
                stack.extend([(node_obj, node) \
                    for node in node_struct['children'][::-1]])
        return added


    def get_root_nodes(self):
        """
        Returns a queryset containing the root nodes in a tree.
        """
        return self.treebeard_nodes.filter(depth=1)
    

    def get_first_root_node(self):
        """
        Returns the first root node in a tree or None if the tree is empty
        """
        try:
            return self.get_root_nodes()[0]
        except IndexError:
            return None


    def get_last_root_node(self):
        """
        Returns the last root node in a tree or None if the tree is empty
        """
        try:
            return self.get_root_nodes().reverse()[0]
        except IndexError:
            return None



    class Meta:
        """
        Abstract model.
        """
        abstract = True



class NodeQuerySet(models.query.QuerySet):
    """
    Custom queryset for the tree node manager.

    Needed only for the customized delete method.
    """


    @transaction.commit_on_success
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
            # to be deleted and make sure that we are removing the descendants
            for node in self:
                self.model.objects.filter(tree=node.tree,
                    path__startswith=node.path).delete(known_children=True)



class NodeManager(models.Manager):
    """
    Custom manager for nodes.
    """

    def get_query_set(self):
        """
        Sets the custom queryset as the default.
        """
        return NodeQuerySet(self.model)



class Node(models.Model):
    """
    Abstract Node model.

    Use this abstract model to create inherited Node models. By default it
    defines 2 data fields:

    path: database field, stores the materialized path for each node. The
        default value of it's max_length, 255, is the max efficient and
        portable value for a varchar. Increase it to allow deeper trees
        (max depth by default: 63)
    depth: helper value that stores the depth of a node in the tree. A root
        node has a depth of 1.
    steplen: class variable that defines the length of each step in the path of
        a node. django-treebeard uses BASE36 encoding for each step since it's
        the most optimal possible encoding that is portable between the
        supported databases The default value of 4 allows a maximum of
        1679615 childs per node. Increase this value if you plan to store large
        trees (a steplen of 5 allows more than 60M childs per node). Note that
        increasing this value, while increasing the number of childs per node,
        will decrease the max depth of the tree (by default: 63). To increase
        the max depth, increase the max_length attribute of the path field in
        your Node model.

    *** YOU'LL HAVE TO ADD A FOREIGN KEY TO YOUR TREE MODEL ***
    
    For instance, the TestNode class in the unit tests is:

        class TestNode(Node):
            desc = models.CharField(max_length=255)
            tree = models.ForeignKey(TestTree,
                                     related_name='treebeard_nodes')
         # where TestTree is an inherited model from Tree

    tree is a mandatory field, if you don't add it, nothing will work.
    Also, the field _MUST_ have a related_name attribute with the value of
    'treebeard_nodes'. This way the Tree model will know how to access the
    Node data, and a Tree model will be limited to one Node model.
    
    Note: django-treebeard uses numconv for path encoding:
          http://code.google.com/p/numconv/
    """

    steplen = 4
    node_order_by = []

    path = models.CharField(max_length=PATH_FIELD_LENGTH)
    depth = models.PositiveIntegerField()

    objects = NodeManager()


    def get_siblings(self):
        """
        Returns a queryset of all the node's siblings, including the node
        itself.
        """
        qset = self.tree.treebeard_nodes.filter(depth=self.depth)
        if self.depth > 1:
            # making sure the non-root nodes share a parent
            basepath = Node._get_basepath(self.path, self.depth, self.steplen)
            qset = qset.filter(path__startswith=basepath)
        return qset


    def get_children(self):
        """
        Returns a queryset of all the node's children
        """
        return self.tree.treebeard_nodes.filter(path__startswith=self.path,
                                   depth=self.depth+1)


    def get_descendants(self):
        """
        Returns a queryset of all the node's descendants as DFS, doesn't
        include the node itself
        """
        return self.tree.treebeard_nodes.filter(path__startswith=self.path,
                                   depth__gt=self.depth)


    def get_first_child(self):
        """
        Returns the leftmost node's child, or None if it has no children.
        """
        try:
            return self.get_children()[0]
        except IndexError:
            return None


    def get_last_child(self):
        """
        Returns the rightmost node's child, or None if it has no children.
        """
        try:
            return self.get_children().reverse()[0]
        except IndexError:
            return None


    def get_first_sibling(self):
        """
        Returns the leftmost node's sibling, can return the node itself if it
        was the leftmost sibling.
        """
        return self.get_siblings()[0]


    def get_last_sibling(self):
        """
        Returns the rightmost node's sibling, can return the node itself if it
        was the rightmost sibling.
        """
        return self.get_siblings().reverse()[0]


    def get_prev_sibling(self):
        """
        Returns the previous node's sibling, or None if it was the leftmost
        sibling.
        """
        try:
            return self.get_siblings().filter(path__lt=self.path).reverse()[0]
        except IndexError:
            return None


    def get_next_sibling(self):
        """
        Returns the next node's sibling, or None if it was the rightmost
        sibling.
        """
        try:
            return self.get_siblings().filter(path__gt=self.path)[0]
        except IndexError:
            return None


    def is_sibling_of(self, node):
        """
        Returns True if the node if a sibling of another node given as an
        argument, else, returns False

        node: the node that will be checked as a sibling
        """
        aux = self.tree_id == node.tree_id and self.depth == node.depth
        if self.depth > 1:
            # making sure the non-root nodes share a parent
            basepath = Node._get_basepath(self.path, self.depth, self.steplen)
            return aux and node.path.startswith(basepath)
        return aux


    def is_child_of(self, node):
        """
        Returns True if the node if a child of another node given as an
        argument, else, returns False

        node: the node that will be checked as a parent
        """
        return self.tree_id == node.tree_id and \
            self.path.startswith(node.path) and \
            self.depth == node.depth+1


    def is_descendant_of(self, node):
        """
        Returns True if the node if a descendant of another node given as an
        argument, else, returns False

        node: the node that will be checked as an ancestor
        """
        return self.tree_id == node.tree_id and \
            self.path.startswith(node.path) and \
            self.depth > node.depth


    def add_child(self, **kwargs):
        """
        Adds a child to the node. The new node will be the new rightmost
        child. If you want to insert a node at a specific position,
        use the add_sibling method of an already existing child node instead.

        Returns the created node object. It will be save()d by this
        method.


        **kwargs: object creation data that will be passed to the inherited
            Node model
        """

        # does the node have children?
        last_child = self.get_last_child()

        if last_child and last_child.node_order_by:
            # there are childs nodes and node_order_by has been set
            # delegate sorted insertion to add_sibling
            return last_child.add_sibling(SORTED, **kwargs)

        # creating a new object
        newobj = self.__class__(**kwargs)
        newobj.tree = self.tree
        newobj.depth = self.depth + 1
        if last_child:
            # adding the new child as the last one
            newobj.path = Node._inc_path(last_child.path, newobj.steplen)
        else:
            # the node had no children, adding the first child
            newobj.path = Node._get_path(self.path, newobj.depth, 1,
                                         newobj.steplen)
        # saving the instance before returning it
        newobj.save()
        return newobj


    def _get_sorted_pos_queryset(self, siblings, newobj):
        """
        Returns the position a new node will be inserted related to the current
        node, and also a queryset of the nodes that must be moved to the right.
        Called only for Node models with node_order_by

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
            newpos = Node._get_lastpos_in_path(siblings.all()[0].path,
                                               self.steplen)
        except IndexError:
            newpos, siblings = None, []
        return newpos, siblings


    @transaction.commit_on_success
    def add_sibling(self, pos, **kwargs):
        """
        Adds a new node as a sibling to the current node object.
        Returns the created node object. It will be saved by this method.


        pos: the position, relative to the current node object, where the
            new node will be inserted, can be one of:
            - first: the new node will be the new leftmost sibling
            - prev: the new node will take the node's place, which will be
              moved to the right 1 position
            - next: the new node will be inserted at the right of the node
            - last: the new node will be the new rightmost sibling
            - sorted: the new node will be at the right position according to
              the value of node_order_by
        **kwargs: object creation data that will be passed to the inherited
            Node model
        """

        if pos not in (FIRST, PREV, NEXT, LAST, SORTED):
            raise InvalidPosition('Invalid relative position: %s' % (pos,))
        if pos == SORTED and not self.node_order_by:
            raise InvalidPosition('Must set node_order_by to use the sorted' \
                                  ' pos in add_sibling')

        # creating a new object
        newobj = self.__class__(**kwargs)
        newobj.tree = self.tree
        newobj.depth = self.depth

        newpos = None
        siblings = []

        if pos == SORTED:
            newpos, siblings = self._get_sorted_pos_queryset(
                self.get_siblings(), newobj)
            if newpos is None:
                pos = LAST

        if pos == LAST or (pos == NEXT and self == self.get_last_sibling()):
            # easy, the last node, nothing to move
            last = self.get_last_sibling()
            newobj.path = Node._inc_path(last.path, newobj.steplen)
        else:

            # we must update the tree before inserting

            cursor = connection.cursor()
            sql_table = self.__class__._meta.db_table

            if newpos is None:
                siblings = self.get_siblings()
                siblings = {PREV:siblings.filter(path__gte=self.path),
                            NEXT:siblings.filter(path__gt=self.path),
                            FIRST:siblings}[pos]
                basenum = Node._get_lastpos_in_path(self.path, self.steplen)
                newpos = {FIRST:1, PREV:basenum, NEXT:basenum+1}[pos]

            newobj.path = Node._get_path(self.path, self.depth, newpos,
                                         self.steplen)

            for node in siblings.reverse():
                # moving the siblings (and their branches) at the right of the
                # inserted position one step to the right
                sql, vals = Node._get_sql_inc_path_in_branches(
                    sql_table, node.tree_id, node.path, self.steplen)
                cursor.execute(sql, vals)

        # saving the instance before returning it
        newobj.save()
        transaction.commit()
        return newobj


    def get_root(self):
        """
        Returns the root node for the current node object.
        """
        return self.tree.treebeard_nodes.get(path=self.path[0:self.steplen])


    def get_ancestors(self):
        """
        Returns a queryset containing the current node object's ancestors,
        starting by the root node and descending to the parent.
        """
        paths = [self.path[0:pos] 
            for pos in range(0, len(self.path), self.steplen)[1:]]
        return self.tree.treebeard_nodes.filter(path__in=paths).order_by('depth')


    @transaction.commit_on_success
    def move(self, target, pos):
        """
        Moves the current node and all it's descendants to a new position
        relative to another node.
        The node can be moved to another tree.


        target: the node that will be used for relative positioning, if the
            target node is in another tree, the branch will be removed from the
            original tree and moved to the target's tree
        pos: the position, relative to the target node, where the
            current node object will be moved to, can be one of:
            - first: the node will be the new leftmost sibling of the target
              node
            - prev: the node will take the target node's place, which will be
              moved to the right 1 position
            - next: the node will be moved to the right of the target node
            - last: the node will be the new rightmost sibling of the target
              node
        """
        if pos not in (FIRST, PREV, NEXT, LAST):
            raise InvalidPosition('Invalid relative position: %s' % (pos,))
        if target.is_descendant_of(self):
            raise InvalidMoveToDescendant("Can't move node to a descendant.")

        oldpath = self.path
        oldtree_id = self.tree_id

        if target.tree_id == oldtree_id and oldpath == target.path:
            # special cases, not actually moving the node so no need to UPDATE
            if pos == PREV:
                return
            if pos in (NEXT, LAST) and \
                    target.path == target.get_last_sibling().path:
                return
            if pos == FIRST and target.path == target.get_first_sibling().path:
                return

        cursor = connection.cursor()
        sql_table = self.__class__._meta.db_table

        if pos == LAST or (pos == NEXT and target == target.get_last_sibling()):
            # easy, just move the branch
            last = target.get_last_sibling()
            newpath = Node._inc_path(last.path, self.steplen)
            sql, vals = Node._get_sql_newpath_in_branches(sql_table,
                              oldtree_id, target.tree_id, self.path, newpath,
                              self.steplen)
            cursor.execute(sql, vals)
        else:
            # do the UPDATE dance

            basenum = Node._get_lastpos_in_path(target.path, self.steplen)

            siblings = target.get_siblings().reverse()
            siblings = {PREV:siblings.filter(path__gte=target.path),
                        NEXT:siblings.filter(path__gt=target.path),
                        FIRST:siblings}[pos]

            for node in siblings:
                # moving the siblings (and their branches) at the right of the
                # relative position one step to the right
                sql, vals = Node._get_sql_inc_path_in_branches(sql_table,
                    target.tree_id, node.path, self.steplen)
                cursor.execute(sql, vals)

                if oldtree_id == target.tree_id and \
                        oldpath.startswith(node.path):
                    # if moving to a parent, update oldpath since we just
                    # increased the path of the entire branch
                    oldpath = vals[0] + oldpath[len(vals[0]):]

            newpos = {FIRST:1, PREV:basenum, NEXT:basenum+1}[pos]
            newpath = Node._get_path(target.path, target.depth, newpos,
                                     self.steplen)

            # node to move
            sql, vals = Node._get_sql_newpath_in_branches(sql_table,
                oldtree_id, target.tree_id, oldpath, newpath, self.steplen)
            cursor.execute(sql, vals)

        if settings.DATABASE_ENGINE == 'mysql' and len(oldpath) != len(newpath):
            # no words can describe how dumb mysql is
            # we must update the depth of the branch in a different query
            sql, vals = Node._get_sql_update_depth_in_branch(sql_table,
                target.tree_id, newpath, self.steplen)
            cursor.execute(sql, vals)

        transaction.commit()



    def delete(self):
        """
        Removes a node and all it's descendants.
        """
        # the known_children parm is a message to the custom queryset to avoid
        # the analysis of every row, since we already know they all belong to
        # the same branch
        self.tree.treebeard_nodes.filter(
            path__startswith=self.path).delete(known_children=True)



    @staticmethod
    def _get_basepath(path, depth, steplen):
        """
        Returns the base path of another path up to a given depth
        """
        if path:
            return path[0:(depth-1)*steplen]
        return ''

    @staticmethod
    def _get_path(path, depth, newstep, steplen):
        """
        Builds a path given some values


        path: the base path
        depth: the depth of the parent node
        newstep: the value (integer) of the new step
        steplen: the length of the step as defined by the model
        """
        basepath = Node._get_basepath(path, depth, steplen)
        key = int2str(newstep, BASE, ALPHABET)
        return '%s%s%s' % (basepath, '0'*(steplen-len(key)), key)

    @staticmethod
    def _inc_path(path, steplen):
        """
        Returns the path of the next sibling of a given node path.
        """
        key = int2str(str2int(path[-steplen:], BASE, ALPHABET)+1, BASE,
                      ALPHABET)
        return '%s%s%s' % (path[:-steplen], '0'*(steplen-len(key)), key)


    @staticmethod
    def _get_lastpos_in_path(path, steplen):
        """
        Returns the integer value of the last step in a path.
        """
        return str2int(path[-steplen:], BASE, ALPHABET)


    @staticmethod
    def _get_sql_newpath_in_branches(sql_table, oldtree_id, newtree_id,
                                         oldpath, newpath, steplen):
        """
        Returns the sql needed to move a branch to another position. The new
        position can be in another tree.

        The generated sql will only update the tree_id/depth values if needed.
        """
        
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

        sql1 = "UPDATE %s SET" % (sql_table,)
        sql2 = ["path=%s" % (sqlpath,)]
        vals = [newpath, len(oldpath)+1]
        if oldtree_id != newtree_id:
            sql2.append("tree_id=%s")
            vals.append(newtree_id)
        if len(oldpath) != len(newpath) and settings.DATABASE_ENGINE != 'mysql':
            # when using mysql, this won't update the depth and it has to be
            # done in another query
            # doesn't even work with sql_mode='ANSI,TRADITIONAL'
            # TODO: FIND OUT WHY?!?? right now I'm just blaming mysql
            sql2.append("depth=LENGTH(%s)/%%s" % (sqlpath,))
            vals.extend([newpath, len(oldpath)+1, steplen])
        sql3 = "WHERE tree_id=%s AND path LIKE %s"   
        vals.extend([oldtree_id, oldpath+'%'])
        sql = '%s %s %s' % (sql1, ', '.join(sql2), sql3)
        return sql, vals


    @staticmethod
    def _get_sql_inc_path_in_branches(sql_table, tree_id, oldpath,
                                           steplen):
        """
        Returns the sql needed to move a branch 1 position to the right.
        """
        newpath = Node._inc_path(oldpath, steplen)
        return Node._get_sql_newpath_in_branches(sql_table, tree_id, tree_id,
                 oldpath, newpath, steplen)


    @staticmethod
    def _get_sql_update_depth_in_branch(sql_table, tree_id, path, steplen):
        """
        Returns the sql needed to update the depth of all the nodes in a
        branch.
        """

        # Right now this is only used by *sigh* mysql.
        sql = "UPDATE %s SET" \
              " depth=LENGTH(path)/%%s" \
              " WHERE tree_id=%%s AND path LIKE %%s" % (sql_table,)
        vals = [steplen, tree_id, path+'%']
        return sql, vals



    class Meta:
        """
        Abstract model.
        """
        abstract = True
        unique_together = [('tree', 'path')]
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

class WrongTreeParm(Exception):
    """
    Raised when a tree argument doesn't match a the tree value of a node
    agument
    """

class NeedOneNodeRelationPerTree(Exception):
    """
    Raised when a tree object is instanced and it has no related node models or
    more than one related node model.
    """


#~
