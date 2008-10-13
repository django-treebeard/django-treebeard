# -*- coding: utf-8 -*-
"""

    treebeard.ns_tree
    -----------------
"""

import operator

from django.db.models import Q
from django.core import serializers
from django.db import models, transaction, connection

from treebeard.models import Node, InvalidMoveToDescendant, PathOverflow


class NS_NodeQuerySet(models.query.QuerySet):
    """
    Custom queryset for the tree node manager.

    Needed only for the customized delete method.
    """


    def delete(self, removed_ranges=None):
        """
        Custom delete method, will remove all descendant nodes to ensure a
        consistent tree (no orphans)

        :returns: ``None``
        """
        if removed_ranges is not None:
            # we already know the children, let's call the default django
            # delete method and let it handle the removal of the user's
            # foreign keys...
            super(NS_NodeQuerySet, self).delete()
            cursor = connection.cursor()

            # Now closing the gap (Celko's trees book, page 62):
            # We do this for every gap that was left in the tree when the nodes
            # were removed.  If many nodes were removed, we're going to update
            # the same nodes over and over again. This would be probably
            # cheaper precalculating the gapsize per intervals, or just do a
            # complete reordering of the tree (uses COUNT)...
            for tree_id, drop_lft, drop_rgt in sorted(removed_ranges, reverse=True):
                sql = 'UPDATE %(table)s ' \
                      ' SET lft = CASE ' \
                      '           WHEN lft > %(drop_lft)d ' \
                      '           THEN lft - %(gapsize)d ' \
                      '           ELSE lft END, ' \
                      '     rgt = CASE ' \
                      '           WHEN rgt > %(drop_lft)d ' \
                      '           THEN rgt - %(gapsize)d ' \
                      '           ELSE rgt END ' \
                      ' WHERE (lft > %(drop_lft)d ' \
                      '     OR rgt > %(drop_lft)d) AND '\
                      '     tree_id=%(tree_id)d' % {
                          'table': self.model._meta.db_table,
                          'gapsize': drop_rgt - drop_lft + 1,
                          'drop_lft': drop_lft,
                          'tree_id': tree_id
                      }
                cursor.execute(sql, [])
        else:
            # we'll have to manually run through all the nodes that are going
            # to be deleted and remove nodes from the list if an ancestor is
            # already getting removed, since that would be redundant
            removed = {}
            for node in self.order_by('tree_id', 'lft'):
                found = False
                for rid, rnode in removed.items():
                    if node.is_descendant_of(rnode):
                        found = True
                        break
                if not found:
                    removed[node.id] = node

            # ok, got the minimal list of nodes to remove...
            # we must also remove their descendants
            toremove = []
            ranges = []
            for id, node in removed.items():
                toremove.append(
                  Q(lft__range=(node.lft, node.rgt))&Q(tree_id=node.tree_id))
                ranges.append((node.tree_id, node.lft, node.rgt))
            if toremove:
                self.model.objects.filter(
                    reduce(operator.or_, toremove)).delete(removed_ranges=ranges)
        transaction.commit_unless_managed()



class NS_NodeManager(models.Manager):
    """ Custom manager for nodes.
    """

    def get_query_set(self):
        """
        Sets the custom queryset as the default.
        """
        return NS_NodeQuerySet(self.model)

class NS_Node(Node):
    node_order_by = []

    lft = models.PositiveIntegerField()
    rgt = models.PositiveIntegerField()
    tree_id = models.PositiveIntegerField()
    depth = models.PositiveIntegerField()

    objects = NS_NodeManager()

    @classmethod
    def add_root(cls, **kwargs):
        """
        Adds a root node to the tree.

        See: :meth:`treebeard.Node.add_root`
        """

        # do we have a root node already?
        last_root = cls.get_last_root_node()

        if last_root and last_root.node_order_by:
            # there are root nodes and node_order_by has been set
            # delegate sorted insertion to add_sibling
            return last_root.add_sibling('sorted-sibling', **kwargs)

        if last_root:
            # adding the new root node as the last one
            #newtree_id = last_root.tree_id + 100
            newtree_id = last_root.tree_id + 1
        else:
            # adding the first root node
            #newtree_id = 100
            newtree_id = 1

        # creating the new object
        newobj = cls(**kwargs)
        newobj.depth = 1
        newobj.tree_id = newtree_id
        newobj.lft = 1
        #newobj.rgt = 400000000
        newobj.rgt = 2
        # saving the instance before returning it
        newobj.save()
        transaction.commit_unless_managed()
        return newobj


    @classmethod
    def _find_next_node(cls, tree_id, lft1, lft2):
        last_lft = cls.objects.filter(tree_id=tree_id, lft__gte=lft1,
                 lft__lt=lft2).order_by('lft').reverse()[0].lft
        if lft2 - last_lft <= 2:
            interval = 10
        else:

            interval = (lft2 - last_lft) / 10

            if interval == 0:
                interval = 1

        return last_lft + 10, last_lft + 10 * 2

 
    @classmethod
    def _move_right(cls, tree_id, rgt, lftmove=False):
        if lftmove:
            lftop = '>='
        else:
            lftop = '>'
        sql = 'UPDATE %(table)s ' \
              ' SET lft = CASE WHEN lft %(lftop)s %(parent_rgt)d ' \
              '                THEN lft + 2 ' \
              '                ELSE lft END, ' \
              '     rgt = CASE WHEN rgt >= %(parent_rgt)d ' \
              '                THEN rgt + 2 ' \
              '                ELSE rgt END ' \
              ' WHERE rgt >= %(parent_rgt)d AND ' \
              '       tree_id = %(tree_id)s' % {
                  'table': cls._meta.db_table,
                  'parent_rgt': rgt,
                  'tree_id': tree_id,
                  'lftop': lftop}
        return sql, []



    def add_child(self, **kwargs):
        """
        Adds a child to the node.

        See: :meth:`treebeard.Node.add_child`
        """
        

        if not self.is_leaf():
            # there are child nodes, delegate insertion to add_sibling
            if self.node_order_by:
                pos = 'sorted-sibling'
            else:
                pos = 'last-sibling'
            last_child = self.get_last_child()
            last_child._cached_parent_obj = self
            return last_child.add_sibling(pos, **kwargs)

        # we're adding the first child of this node
        sql, params = self.__class__._move_right(self.tree_id, self.rgt, False)

        # creating a new object
        newobj = self.__class__(**kwargs)
        newobj.tree_id = self.tree_id
        newobj.depth = self.depth + 1
        newobj.lft = self.lft+1
        newobj.rgt = self.lft+2

        # this is just to update the cache
        self.rgt = self.rgt+2

        newobj._cached_parent_obj = self

        cursor = connection.cursor()
        cursor.execute(sql, params)

        # saving the instance before returning it
        newobj.save()
        transaction.commit_unless_managed()
        
        return newobj


    def add_sibling(self, pos=None, **kwargs):
        """
        Adds a new node as a sibling to the current node object.

        See: :meth:`treebeard.Node.add_sibling`
        """

        pos = self._fix_add_sibling_opts(pos)

        # creating a new object
        newobj = self.__class__(**kwargs)
        newobj.depth = self.depth

        if pos == 'sorted-sibling':
            raise NotImplemented
        sql = None

        if self.is_root():
            newobj.lft = 1
            newobj.rgt = 2
            last_root = self.__class__.get_last_root_node()
            if pos == 'last-sibling' \
                  or (pos == 'right' and self == last_root):
                newobj.tree_id = last_root.tree_id + 1
            else:
                newpos = {'first-sibling': 1,
                          'left': self.tree_id,
                          'right': self.tree_id + 1}[pos]
                sql = 'UPDATE %(table)s ' \
                      ' SET tree_id = tree_id+1 ' \
                      ' WHERE tree_id >= %(newpos)s' % {
                          'table': self.__class__._meta.db_table,
                          'newpos': newpos
                      }
                params = []

                newobj.tree_id = newpos
        else:
            newobj.tree_id = self.tree_id

            target = self

            if pos in ('left', 'right', 'first-sibling'):

                siblings = list(self.get_siblings())

                if pos == 'right':
                    if target == siblings[-1]:
                        pos = 'last-sibling'
                    else:
                        pos = 'left'
                        found = False
                        for node in siblings:
                            if found:
                                target = node
                                break
                            elif node == self:
                                found = True
                if pos == 'left':
                    if target == siblings[0]:
                        pos = 'first-sibling'
                if pos == 'first-sibling':
                    target = siblings[0]

            move_right = self.__class__._move_right

            if pos == 'last-sibling':
                newpos = target.get_parent().rgt
                sql, params = move_right(self.tree_id, newpos, False)
            elif pos == 'first-sibling':
                newpos = target.lft
                sql, params = move_right(self.tree_id, newpos-1, False)
            elif pos == 'left':
                newpos = target.lft
                sql, params = move_right(self.tree_id, newpos, True)

            newobj.lft = newpos
            newobj.rgt = newpos + 1

        # saving the instance before returning it
        if sql:
            cursor = connection.cursor()
            cursor.execute(sql, params)
        newobj.save()

        transaction.commit_unless_managed()
        
        return newobj


    def move(self, target, pos=None):
        """
        Moves the current node and all it's descendants to a new position
        relative to another node.

        See: :meth:`treebeard.Node.move`
        """

        pos = self._fix_move_opts(pos)


    @classmethod
    def load_bulk(cls, bulk_data, parent=None, keep_ids=False):
        """
        """

        # tree, iterative preorder
        added = []
        if parent:
            parent_id = parent.id
        else:
            parent_id = None
        # stack of nodes to analize
        stack = [(parent_id, node) for node in bulk_data[::-1]]
        while stack:
            parent_id, node_struct = stack.pop()
            # shallow copy of the data strucure so it doesn't persist...
            node_data = node_struct['data'].copy()
            if keep_ids:
                node_data['id'] = node_struct['id']
            if parent_id:
                parent = cls.objects.get(pk=parent_id)
                node_obj = parent.add_child(**node_data)
            else:
                node_obj = cls.add_root(**node_data)
            added.append(node_obj.id)
            if 'children' in node_struct:
                # extending the stack with the current node as the parent of
                # the new nodes
                stack.extend([(node_obj.id, node) \
                    for node in node_struct['children'][::-1]])
        transaction.commit_unless_managed()
        return added


    def get_children(self):
        """
        :returns: A queryset of all the node's children

        See: :meth:`treebeard.Node.get_children`
        """
        return self.get_descendants().filter(depth=self.depth+1)


    def get_depth(self):
        """
        :returns: the depth (level) of the node

        See: :meth:`treebeard.Node.get_depth`
        """
        return self.depth


    def is_leaf(self):
        """
        :returns: True if the node is a leaf node (else, returns False)

        See: :meth:`treebeard.Node.is_leaf`
        """
        return self.rgt - self.lft == 1


    def get_root(self):
        """
        :returns: the root node for the current node object.

        See: :meth:`treebeard.Node.get_root`
        """
        if self.lft == 1:
            return self
        return self.__class__.objects.get(tree_id=self.tree_id,
                                          lft=1)

    
    
    def get_siblings(self):
        """
        :returns: A queryset of all the node's siblings, including the node
            itself.

        See: :meth:`treebeard.Node.get_siblings`
        """
        if self.lft == 1:
            return self.get_root_nodes()
        return self.get_parent(True).get_children()


    @classmethod
    def dump_bulk(cls, parent=None, keep_ids=True):
        """
        Dumps a tree branch to a python data structure.

        See: :meth:`treebeard.Node.dump_bulk`
        """
        qset = cls.get_tree(parent)
        ret, lnk = [], {}
        for pyobj in qset:
            serobj = serializers.serialize('python', [pyobj])[0]
            # for serobj in serializers.serialize('python', qset):
            # django's serializer stores the attributes in 'fields'
            fields = serobj['fields']
            depth = fields['depth']
            lft = fields['lft']
            tree_id = fields['tree_id']
            # this will be useless in load_bulk
            del fields['lft']
            del fields['rgt']
            del fields['depth']
            del fields['tree_id']
            if 'id' in fields:
                # this happens immediately after a load_bulk
                del fields['id']

            newobj = {'data':fields}
            if keep_ids:
                newobj['id'] = serobj['pk']
            
            if (not parent and depth == 1) or \
                    (parent and depth == parent.depth):
                ret.append(newobj)
            else:
                parentobj = pyobj.get_parent()
                parentser = lnk[parentobj.id]
                if 'children' not in parentser:
                    parentser['children'] = []
                parentser['children'].append(newobj)
            lnk[pyobj.id] = newobj
        return ret




    @classmethod
    def get_tree(cls, parent=None):
        """
        :returns: A *queryset* of nodes ordered as DFS, including the parent. If
                  no parent is given, all trees are returned.

        See: :meth:`treebeard.Node.get_tree`

        .. note::

            This metod returns a queryset.
        """
        if parent is None:
            # return the entire tree
            return cls.objects.all()
        return cls.objects.filter(
            tree_id=parent.tree_id,
            lft__range=(parent.lft, parent.rgt-1))


    def get_descendants(self):
        """
        :returns: A queryset of all the node's descendants as DFS, doesn't
            include the node itself

        See: :meth:`treebeard.Node.get_descendants`
        """
        return self.__class__.get_tree(self).exclude(pk=self.id)


    def get_ancestors(self):
        """
        :returns: A queryset containing the current node object's ancestors,
            starting by the root node and descending to the parent.

        See: :meth:`treebeard.Node.get_ancestors`
        """
        if self.is_root():
            return self.__class__.objects.none()
        return self.__class__.objects.filter(
            tree_id=self.tree_id,
            lft__lt=self.lft,
            rgt__gt=self.rgt)


    def is_descendant_of(self, node):
        """
        :returns: ``True`` if the node if a descendant of another node given
            as an argument, else, returns ``False``

        See: :meth:`treebeard.Node.is_descendant_of`
        """
        return self.tree_id == node.tree_id and \
               self.lft > node.lft and \
               self.rgt < node.rgt


    def get_parent(self, update=False):
        """
        :returns: the parent node of the current node object.
            Caches the result in the object itself to help in loops.

        See: :meth:`treebeard.Node.get_parent`
        """
        if self.is_root():
            return
        try:
            if update:
                del self._cached_parent_obj
            else:
                return self._cached_parent_obj
        except AttributeError:
            pass
        # parent = our most direct ancestor
        self._cached_parent_obj = self.get_ancestors().reverse()[0]
        return self._cached_parent_obj
        

    @classmethod
    def get_root_nodes(cls):
        """
        :returns: A queryset containing the root nodes in the tree.

        Example::

           MyNodeModel.get_root_nodes()
        """
        return cls.objects.filter(lft=1)


    class Meta:
        """
        Abstract model.
        """
        abstract = True
        # By changing the ordering, assume that lots of things will break,
        # at least you'll want to check the first/last/prev/next methods.
        # This ordering assumes you want something... TREEISH
        # PROTIP: don't change this
        ordering = ['tree_id', 'lft']

        #unique_together = (('tree_id', 'lft'), ('tree_id', 'rgt'))

