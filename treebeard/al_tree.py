"Adjacency List"

from django.core import serializers
from django.db import models, transaction, connection

from treebeard.models import Node
from treebeard.exceptions import InvalidMoveToDescendant


class AL_NodeManager(models.Manager):
    "Custom manager for nodes."

    def get_query_set(self):
        "Sets the custom queryset as the default."
        qset = super(AL_NodeManager, self).get_query_set()
        if self.model.node_order_by:
            order_by = ['parent'] + self.model.node_order_by
        else:
            order_by = ['parent', 'sib_order']
        return qset.order_by(*order_by)


class AL_Node(Node):
    "Abstract model to create your own Adjacency List Trees."

    objects = AL_NodeManager()
    node_order_by = None

    @classmethod
    def add_root(cls, **kwargs):
        "Adds a root node to the tree."
        newobj = cls(**kwargs)
        newobj._cached_depth = 1

        if not cls.node_order_by:
            try:
                max = cls.objects.filter(parent__isnull=True).order_by(
                        'sib_order').reverse()[0].sib_order
            except IndexError:
                max = 0
            newobj.sib_order = max + 1

        # saving the instance before returning it
        newobj.save()
        transaction.commit_unless_managed()
        return newobj

    @classmethod
    def get_root_nodes(cls):
        ":returns: A queryset containing the root nodes in the tree."
        return cls.objects.filter(parent__isnull=True)

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

    def get_children(self):
        ":returns: A queryset of all the node's children"
        return self.__class__.objects.filter(parent=self)

    def get_parent(self, update=False):
        ":returns: the parent node of the current node object."
        return self.parent

    def get_ancestors(self):
        """
        :returns: A *list* containing the current node object's ancestors,
            starting by the root node and descending to the parent.
        """
        ancestors = []
        node = self.parent
        while node:
            ancestors.append(node)
            node = node.parent
        ancestors.reverse()
        return ancestors

    def get_root(self):
        ":returns: the root node for the current node object."
        ancestors = self.get_ancestors()
        if ancestors:
            return ancestors[0]
        return self

    def is_descendant_of(self, node):
        """
        :returns: ``True`` if the node if a descendant of another node given
            as an argument, else, returns ``False``
        """
        return self.pk in [obj.pk for obj in node.get_descendants()]

    @classmethod
    def dump_bulk(cls, parent=None, keep_ids=True):
        "Dumps a tree branch to a python data structure."

        serializable_cls = cls._get_serializable_model()
        if parent and serializable_cls != cls and \
                parent.__class__ != serializable_cls:
            parent = serializable_cls.objects.get(pk=parent.pk)

        # a list of nodes: not really a queryset, but it works
        objs = serializable_cls.get_tree(parent)

        ret, lnk = [], {}
        for node, pyobj in zip(objs, serializers.serialize('python', objs)):
            depth = node.get_depth()
            # django's serializer stores the attributes in 'fields'
            fields = pyobj['fields']
            del fields['parent']

            # non-sorted trees have this
            if 'sib_order' in fields:
                del fields['sib_order']

            if 'id' in fields:
                del fields['id']

            newobj = {'data': fields}
            if keep_ids:
                newobj['id'] = pyobj['pk']

            if (not parent and depth == 1) or \
                    (parent and depth == parent.get_depth()):
                ret.append(newobj)
            else:
                parentobj = lnk[node.parent_id]
                if 'children' not in parentobj:
                    parentobj['children'] = []
                parentobj['children'].append(newobj)
            lnk[node.id] = newobj
        return ret

    def add_child(self, **kwargs):
        "Adds a child to the node."
        newobj = self.__class__(**kwargs)
        try:
            newobj._cached_depth = self._cached_depth + 1
        except AttributeError:
            pass

        if not self.__class__.node_order_by:
            try:
                max = self.__class__.objects.filter(parent=self).reverse(
                    )[0].sib_order
            except IndexError:
                max = 0
            newobj.sib_order = max + 1

        # saving the instance before returning it
        newobj.parent = self
        newobj.save()
        transaction.commit_unless_managed()
        return newobj

    @classmethod
    def _get_tree_recur(cls, ret, parent, depth):
        if parent:
            qset = cls.objects.filter(parent=parent)
        else:
            qset = cls.get_root_nodes()
        for node in qset:
            node._cached_depth = depth
            ret.append(node)
            cls._get_tree_recur(ret, node, depth + 1)

    @classmethod
    def get_tree(cls, parent=None):
        """
        :returns: A list of nodes ordered as DFS, including the parent. If
                  no parent is given, the entire tree is returned.
        """
        if parent:
            depth = parent.get_depth() + 1
            ret = [parent]
        else:
            depth = 1
            ret = []
        cls._get_tree_recur(ret, parent, depth)
        return ret

    def get_descendants(self):
        """
        :returns: A *list* of all the node's descendants, doesn't
            include the node itself
        """
        return self.__class__.get_tree(parent=self)[1:]

    def get_descendant_count(self):
        ":returns: the number of descendants of a nodee"
        return len(self.get_descendants())

    def get_siblings(self):
        """
        :returns: A queryset of all the node's siblings, including the node
            itself.
        """
        if self.parent:
            return self.__class__.objects.filter(parent=self.parent)
        return self.__class__.get_root_nodes()

    def add_sibling(self, pos=None, **kwargs):
        "Adds a new node as a sibling to the current node object."

        pos = self._fix_add_sibling_opts(pos)

        stmts = []

        # creating a new object
        newobj = self.__class__(**kwargs)

        if not self.node_order_by:
            newobj.sib_order = self.__class__._move_add_sibling_aux(pos,
                                   self, stmts)

        if self.parent_id:
            newobj.parent_id = self.parent_id

        cursor = connection.cursor()
        for sql, vals in stmts:
            cursor.execute(sql, vals)

        # saving the instance before returning it
        newobj.save()
        transaction.commit_unless_managed()
        return newobj

    @classmethod
    def _move_add_sibling_aux(cls, pos, target, stmts):
        """
        helper that makes a hole between siblings for a new node (only for not
        sorted trees)
        """

        sib_order = target.sib_order
        if pos == 'last-sibling' \
                or (pos == 'right' and target == target.get_last_sibling()):
            sib_order = target.get_last_sibling().sib_order + 1
        else:
            siblings = target.get_siblings()
            siblings = {'left': siblings.filter(
                                     sib_order__gte=target.sib_order),
                        'right': siblings.filter(
                                     sib_order__gt=target.sib_order),
                        'first-sibling': siblings}[pos]
            sib_order = {'left': sib_order,
                         'right': sib_order + 1,
                         'first-sibling': 1}[pos]
            try:
                min = siblings.order_by('sib_order')[0].sib_order
            except IndexError:
                min = 0
            if min:
                sql = 'UPDATE %(table)s' \
                      ' SET sib_order=sib_order+1' \
                      ' WHERE sib_order >= %%s' \
                      ' AND ' % {'table':
                                connection.ops.quote_name(cls._meta.db_table)}
                params = [min]
                if target.is_root():
                    sql += 'parent_id IS NULL'
                else:
                    sql += 'parent_id=%s'
                    params.append(target.parent_id)
                stmts.append((sql, params))
        return sib_order

    def move(self, target, pos=None):
        """
        Moves the current node and all it's descendants to a new position
        relative to another node.
        """

        pos = self._fix_move_opts(pos)

        stmts = []
        sib_order = None
        parent = None

        if pos in ('first-child', 'last-child', 'sorted-child'):
            # moving to a child
            if not target.is_leaf():
                target = target.get_last_child()
                pos = {'first-child': 'first-sibling',
                       'last-child': 'last-sibling',
                       'sorted-child': 'sorted-sibling'}[pos]
            else:
                parent = target
                if pos == 'sorted-child':
                    pos = 'sorted-sibling'
                else:
                    pos = 'first-sibling'
                    sib_order = 1

        if target.is_descendant_of(self):
            raise InvalidMoveToDescendant("Can't move node to a descendant.")

        if self == target and (
              (pos == 'left') or \
              (pos in ('right', 'last-sibling') and \
                target == target.get_last_sibling()) or \
              (pos == 'first-sibling' and \
                target == target.get_first_sibling())):
            # special cases, not actually moving the node so no need to UPDATE
            return

        if pos == 'sorted-sibling':
            # easy, just change the parent
            if parent:
                self.parent = parent
            else:
                self.parent = target.parent
        else:
            if sib_order:
                self.sib_order = sib_order
            else:
                self.sib_order = self.__class__._move_add_sibling_aux(pos,
                                        target, stmts)
            if parent:
                self.parent = parent
            else:
                self.parent = target.parent

        if stmts:
            cursor = connection.cursor()
            for sql, vals in stmts:
                cursor.execute(sql, vals)

        self.save()
        transaction.commit_unless_managed()

    class Meta:
        "Abstract model."
        abstract = True
