"Unit/Functional tests"

import functools
import os
from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from django.db import models, transaction
from django.contrib.auth.models import User
from django.db.models import Q
from django.conf import settings
from django import VERSION as DJANGO_VERSION

from treebeard import numconv
from treebeard.exceptions import InvalidPosition, InvalidMoveToDescendant, \
    PathOverflow, MissingNodeOrderBy
from treebeard.mp_tree import MP_Node
from treebeard.al_tree import AL_Node
from treebeard.ns_tree import NS_Node
from treebeard.forms import MoveNodeForm

# ghetto app detection, there is probably some introspection method,
# but meh, this works
HAS_DJANGO_AUTH = 'django.contrib.auth' in settings.INSTALLED_APPS

BASE_DATA = [
  {'data':{'desc':'1'}},
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


class MP_TestNode(MP_Node):
    steplen = 3

    desc = models.CharField(max_length=255)

    def __unicode__(self):  # pragma: no cover
        return 'Node %d' % self.id


class MP_TestNodeSomeDep(models.Model):
    node = models.ForeignKey(MP_TestNode)

    def __unicode__(self):  # pragma: no cover
        return 'Node %d' % self.id


class NS_TestNode(NS_Node):
    desc = models.CharField(max_length=255)

    def __unicode__(self):  # pragma: no cover
        return 'Node %d' % self.id


class NS_TestNodeSomeDep(models.Model):
    node = models.ForeignKey(NS_TestNode)

    def __unicode__(self):  # pragma: no cover
        return 'Node %d' % self.id


class AL_TestNode(AL_Node):
    parent = models.ForeignKey('self',
                               related_name='children_set',
                               null=True,
                               db_index=True)
    sib_order = models.PositiveIntegerField()
    desc = models.CharField(max_length=255)

    def __unicode__(self):  # pragma: no cover
        return 'Node %d' % self.id


class AL_TestNodeSomeDep(models.Model):
    node = models.ForeignKey(AL_TestNode)

    def __unicode__(self):  # pragma: no cover
        return 'Node %d' % self.id


class MP_TestNodeSorted(MP_Node):
    steplen = 1
    node_order_by = ['val1', 'val2', 'desc']
    val1 = models.IntegerField()
    val2 = models.IntegerField()
    desc = models.CharField(max_length=255)

    def __unicode__(self):  # pragma: no cover
        return 'Node %d' % self.id


class NS_TestNodeSorted(NS_Node):
    node_order_by = ['val1', 'val2', 'desc']
    val1 = models.IntegerField()
    val2 = models.IntegerField()
    desc = models.CharField(max_length=255)

    def __unicode__(self):  # pragma: no cover
        return 'Node %d' % self.id


class AL_TestNodeSorted(AL_Node):
    parent = models.ForeignKey('self',
                               related_name='children_set',
                               null=True,
                               db_index=True)
    node_order_by = ['val1', 'val2', 'desc']
    val1 = models.IntegerField()
    val2 = models.IntegerField()
    desc = models.CharField(max_length=255)

    def __unicode__(self):  # pragma: no cover
        return 'Node %d' % self.id


class MP_TestNodeAlphabet(MP_Node):
    steplen = 2

    numval = models.IntegerField()

    def __unicode__(self):  # pragma: no cover
        return 'Node %d' % self.id


class MP_TestNodeSmallStep(MP_Node):
    steplen = 1
    alphabet = '0123456789'

    def __unicode__(self):  # pragma: no cover
        return 'Node %d' % self.id


class MP_TestNodeSortedAutoNow(MP_Node):
    desc = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)

    node_order_by = ['created']

    def __unicode__(self):  # pragma: no cover
        return 'Node %d' % self.id


class MP_TestNodeShortPath(MP_Node):
    steplen = 1
    alphabet = '01234'
    desc = models.CharField(max_length=255)

    def __unicode__(self):  # pragma: no cover
        return 'Node %d' % self.id

# This is how you change the default fields defined in a Django abstract class
# (in this case, MP_Node), since Django doesn't allow overriding fields, only
# mehods and attributes
MP_TestNodeShortPath._meta.get_field('path').max_length = 4


if DJANGO_VERSION >= (1, 1):  # pragma: no cover

    class MP_TestNode_Proxy(MP_TestNode):
        class Meta:
            proxy = True


    class NS_TestNode_Proxy(NS_TestNode):
        class Meta:
            proxy = True


    class AL_TestNode_Proxy(AL_TestNode):
        class Meta:
            proxy = True


class MP_TestSortedNodeShortPath(MP_Node):
    steplen = 1
    alphabet = '01234'
    desc = models.CharField(max_length=255)

    node_order_by = ['desc']

    def __unicode__(self):  # pragma: no cover
        return 'Node %d' % self.id

MP_TestSortedNodeShortPath._meta.get_field('path').max_length = 4


if HAS_DJANGO_AUTH:

    class MP_TestIssue14(MP_Node):
        name = models.CharField(max_length=255)
        users = models.ManyToManyField(User)


def testtype(treetype, proxy):

    def decorator(f):

        @functools.wraps(f)
        def _testtype(self):
            {'MP': self.set_MP,
             'AL': self.set_AL,
             'NS': self.set_NS}[treetype](proxy)
            try:
                f(self)
            finally:
                transaction.rollback()
                self.model = None
                self.sorted_model = None
                self.dep_model = None
        return _testtype
    return decorator


def _load_test_methods(cls, proxy=True):
    if proxy and DJANGO_VERSION >= (1, 1):
        proxyopts = (False, True)
    else:
        proxyopts = (False,)
    for m in dir(cls):
        if not m.startswith('_multi_'):
            continue
        for t in ('MP', 'AL', 'NS'):
            for p in proxyopts:
                deco = testtype(t, p)
                name = 'test_%s%s_%s' % (t.lower(),
                                          '_proxy' if p else '',
                                          m.split('_', 2)[2])
                setattr(cls, name, deco(getattr(cls, m)))


class TestTreeBase(TestCase):

    def setUp(self):
        self.set_MP()
        self.unchanged = [(u'1', 1, 0),
                          (u'2', 1, 4),
                          (u'21', 2, 0),
                          (u'22', 2, 0),
                          (u'23', 2, 1),
                          (u'231', 3, 0),
                          (u'24', 2, 0),
                          (u'3', 1, 0),
                          (u'4', 1, 1),
                          (u'41', 2, 0)]

    def set_MP(self, proxy=False):
        if proxy and DJANGO_VERSION >= (1, 1):
            self.model = MP_TestNode_Proxy
        else:
            self.model = MP_TestNode
        self.sorted_model = MP_TestNodeSorted
        self.dep_model = MP_TestNodeSomeDep

    def set_NS(self, proxy=False):
        if proxy and DJANGO_VERSION >= (1, 1):
            self.model = NS_TestNode_Proxy
        else:
            self.model = NS_TestNode
        self.sorted_model = NS_TestNodeSorted
        self.dep_model = NS_TestNodeSomeDep

    def set_AL(self, proxy=False):
        if proxy and DJANGO_VERSION >= (1, 1):
            self.model = AL_TestNode_Proxy
        else:
            self.model = AL_TestNode
        self.sorted_model = AL_TestNodeSorted
        self.dep_model = AL_TestNodeSomeDep

    def got(self):
        nsmodels = [NS_TestNode]
        if DJANGO_VERSION >= (1, 1):
            nsmodels.append(NS_TestNode_Proxy)
        if self.model in nsmodels:
            # this slows down nested sets tests quite a bit, but it has the
            # advantage that we'll check the node edges are correct
            d = {}
            for tree_id, lft, rgt in self.model.objects.values_list('tree_id',
                                                                    'lft',
                                                                    'rgt'):
                d.setdefault(tree_id, []).extend([lft, rgt])
            for tree_id, got_edges in d.items():
                self.assertEqual(len(got_edges), max(got_edges))
                good_edges = range(1, len(got_edges) + 1)
                self.assertEqual(sorted(got_edges), good_edges)

        return [(o.desc, o.get_depth(), o.get_children_count())
                for o in self.model.get_tree()]

    def _assert_get_annotated_list(self, expected, parent=None):
        got = [
            (obj[0].desc, obj[1]['open'], obj[1]['close'], obj[1]['level'])
            for obj in self.model.get_annotated_list(parent)]
        self.assertEqual(expected, got)


class TestEmptyTree(TestTreeBase):

    def _multi_load_bulk_empty(self):
        ids = self.model.load_bulk(BASE_DATA)
        got_descs = [obj.desc
                     for obj in self.model.objects.filter(id__in=ids)]
        expected_descs = [x[0] for x in self.unchanged]
        self.assertEqual(sorted(got_descs), sorted(expected_descs))
        self.assertEqual(self.got(), self.unchanged)

    def _multi_dump_bulk_empty(self):
        self.assertEqual(self.model.dump_bulk(), [])

    def _multi_add_root_empty(self):
        self.model.add_root(desc='1')
        expected = [(u'1', 1, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_get_root_nodes_empty(self):
        got = self.model.get_root_nodes()
        expected = []
        self.assertEqual([node.desc for node in got], expected)

    def _multi_get_first_root_node_empty(self):
        got = self.model.get_first_root_node()
        self.assertEqual(got, None)

    def _multi_get_last_root_node_empty(self):
        got = self.model.get_last_root_node()
        self.assertEqual(got, None)

    def _multi_get_tree(self):
        got = list(self.model.get_tree())
        self.assertEqual(got, [])

    def _multi_get_annotated_list(self):
        expected = []
        self._assert_get_annotated_list(expected)


class TestNonEmptyTree(TestTreeBase):

    def setUp(self):
        super(TestNonEmptyTree, self).setUp()
        MP_TestNode.load_bulk(BASE_DATA)
        AL_TestNode.load_bulk(BASE_DATA)
        NS_TestNode.load_bulk(BASE_DATA)


class TestClassMethods(TestNonEmptyTree):

    def setUp(self):
        super(TestClassMethods, self).setUp()

    def _multi_load_bulk_existing(self):

        # inserting on an existing node

        node = self.model.objects.get(desc=u'231')
        ids = self.model.load_bulk(BASE_DATA, node)
        expected = [(u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 4),
                    (u'1', 4, 0),
                    (u'2', 4, 4),
                    (u'21', 5, 0),
                    (u'22', 5, 0),
                    (u'23', 5, 1),
                    (u'231', 6, 0),
                    (u'24', 5, 0),
                    (u'3', 4, 0),
                    (u'4', 4, 1),
                    (u'41', 5, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        expected_descs = [u'1', u'2', u'21', u'22', u'23', u'231', u'24',
                          u'3', u'4', u'41']
        got_descs = [obj.desc
                     for obj in self.model.objects.filter(id__in=ids)]
        self.assertEqual(sorted(got_descs), sorted(expected_descs))
        self.assertEqual(self.got(), expected)

    def _multi_get_tree_all(self):
        got = [(o.desc, o.get_depth(), o.get_children_count())
                for o in self.model.get_tree()]
        self.assertEqual(got, self.unchanged)

    def _multi_dump_bulk_all(self):
        self.assertEqual(self.model.dump_bulk(keep_ids=False), BASE_DATA)

    def _multi_get_tree_node(self):
        node = self.model.objects.get(desc=u'231')
        self.model.load_bulk(BASE_DATA, node)

        # the tree was modified by load_bulk, so we reload our node object
        node = self.model.objects.get(pk=node.id)

        got = [(o.desc, o.get_depth(), o.get_children_count())
                for o in self.model.get_tree(node)]
        expected = [(u'231', 3, 4),
                    (u'1', 4, 0),
                    (u'2', 4, 4),
                    (u'21', 5, 0),
                    (u'22', 5, 0),
                    (u'23', 5, 1),
                    (u'231', 6, 0),
                    (u'24', 5, 0),
                    (u'3', 4, 0),
                    (u'4', 4, 1),
                    (u'41', 5, 0)]
        self.assertEqual(got, expected)

    def _multi_get_tree_leaf(self):
        node = self.model.objects.get(desc=u'1')

        self.assertEqual(0, node.get_children_count())
        got = [(o.desc, o.get_depth(), o.get_children_count())
                for o in self.model.get_tree(node)]
        expected = [(u'1', 1, 0)]
        self.assertEqual(got, expected)

    def _multi_get_annotated_list_all(self):
        expected = [(u'1', True, [], 0), (u'2', False, [], 0),
                    (u'21', True, [], 1), (u'22', False, [], 1),
                    (u'23', False, [], 1), (u'231', True, [0], 2),
                    (u'24', False, [0], 1), (u'3', False, [], 0),
                    (u'4', False, [], 0), (u'41', True, [0, 1], 1)]
        self._assert_get_annotated_list(expected)

    def _multi_get_annotated_list_node(self):
        node = self.model.objects.get(desc=u'2')
        expected = [(u'2', True, [], 0), (u'21', True, [], 1),
                    (u'22', False, [], 1), (u'23', False, [], 1),
                    (u'231', True, [0], 2), (u'24', False, [0, 1], 1)]
        self._assert_get_annotated_list(expected, node)

    def _multi_get_annotated_list_leaf(self):
        node = self.model.objects.get(desc=u'1')
        expected = [(u'1', True, [0], 0)]
        self._assert_get_annotated_list(expected, node)

    def _multi_dump_bulk_node(self):
        node = self.model.objects.get(desc=u'231')
        self.model.load_bulk(BASE_DATA, node)

        # the tree was modified by load_bulk, so we reload our node object
        node = self.model.objects.get(pk=node.id)

        got = self.model.dump_bulk(node, False)
        expected = [{'data':{'desc':u'231'}, 'children':BASE_DATA}]
        self.assertEqual(got, expected)

    def _multi_load_and_dump_bulk_keeping_ids(self):
        exp = self.model.dump_bulk(keep_ids=True)
        self.model.objects.all().delete()
        self.model.load_bulk(exp, None, True)
        got = self.model.dump_bulk(keep_ids=True)
        self.assertEqual(got, exp)
        # do we really have an unchaged tree after the dump/delete/load?
        got = [(o.desc, o.get_depth(), o.get_children_count())
                for o in self.model.get_tree()]
        self.assertEqual(got, self.unchanged)

    def _multi_get_root_nodes(self):
        got = self.model.get_root_nodes()
        expected = ['1', '2', '3', '4']
        self.assertEqual([node.desc for node in got], expected)

    def _multi_get_first_root_node(self):
        got = self.model.get_first_root_node()
        self.assertEqual(got.desc, '1')

    def _multi_get_last_root_node(self):
        got = self.model.get_last_root_node()
        self.assertEqual(got.desc, '4')

    def _multi_add_root(self):
        obj = self.model.add_root(desc='5')
        self.assertEqual(obj.get_depth(), 1)
        self.assertEqual(self.model.get_last_root_node().desc, '5')


class TestSimpleNodeMethods(TestNonEmptyTree):

    def _multi_is_root(self):
        data = [
            ('2', True),
            ('1', True),
            ('4', True),
            ('21', False),
            ('24', False),
            ('22', False),
            ('231', False),
        ]
        for desc, expected in data:
            got = self.model.objects.get(desc=desc).is_root()
            self.assertEqual(got, expected)

    def _multi_is_leaf(self):
        data = [
            ('2', False),
            ('23', False),
            ('231', True),
        ]
        for desc, expected in data:
            got = self.model.objects.get(desc=desc).is_leaf()
            self.assertEqual(got, expected)

    def _multi_get_root(self):
        data = [
            ('2', '2'),
            ('1', '1'),
            ('4', '4'),
            ('21', '2'),
            ('24', '2'),
            ('22', '2'),
            ('231', '2'),
        ]
        for desc, expected in data:
            node = self.model.objects.get(desc=desc).get_root()
            self.assertEqual(node.desc, expected)

    def _multi_get_parent(self):
        data = [
            ('2', None),
            ('1', None),
            ('4', None),
            ('21', '2'),
            ('24', '2'),
            ('22', '2'),
            ('231', '23'),
        ]
        data = dict(data)
        objs = {}
        for desc, expected in data.items():
            node = self.model.objects.get(desc=desc)
            parent = node.get_parent()
            if expected:
                self.assertEqual(parent.desc, expected)
            else:
                self.assertEqual(parent, None)
            objs[desc] = node
            # corrupt the objects' parent cache
            node._parent_obj = 'CORRUPTED!!!'

        for desc, expected in data.items():
            node = objs[desc]
            # asking get_parent to not use the parent cache (since we
            # corrupted it in the previous loop)
            parent = node.get_parent(True)
            if expected:
                self.assertEqual(parent.desc, expected)
            else:
                self.assertEqual(parent, None)

    def _multi_get_children(self):
        data = [
            ('2', ['21', '22', '23', '24']),
            ('23', ['231']),
            ('231', []),
        ]
        for desc, expected in data:
            children = self.model.objects.get(desc=desc).get_children()
            self.assertEqual([node.desc for node in children], expected)

    def _multi_get_children_count(self):
        data = [
            ('2', 4),
            ('23', 1),
            ('231', 0),
        ]
        for desc, expected in data:
            got = self.model.objects.get(desc=desc).get_children_count()
            self.assertEqual(got, expected)

    def _multi_get_siblings(self):
        data = [
            ('2', ['1', '2', '3', '4']),
            ('21', ['21', '22', '23', '24']),
            ('231', ['231']),
        ]
        for desc, expected in data:
            siblings = self.model.objects.get(desc=desc).get_siblings()
            self.assertEqual([node.desc for node in siblings], expected)

    def _multi_get_first_sibling(self):
        data = [
            ('2', '1'),
            ('1', '1'),
            ('4', '1'),
            ('21', '21'),
            ('24', '21'),
            ('22', '21'),
            ('231', '231'),
        ]
        for desc, expected in data:
            node = self.model.objects.get(desc=desc).get_first_sibling()
            self.assertEqual(node.desc, expected)

    def _multi_get_prev_sibling(self):
        data = [
            ('2', '1'),
            ('1', None),
            ('4', '3'),
            ('21', None),
            ('24', '23'),
            ('22', '21'),
            ('231', None),
        ]
        for desc, expected in data:
            node = self.model.objects.get(desc=desc).get_prev_sibling()
            if expected is None:
                self.assertEqual(node, None)
            else:
                self.assertEqual(node.desc, expected)

    def _multi_get_next_sibling(self):
        data = [
            ('2', '3'),
            ('1', '2'),
            ('4', None),
            ('21', '22'),
            ('24', None),
            ('22', '23'),
            ('231', None),
        ]
        for desc, expected in data:
            node = self.model.objects.get(desc=desc).get_next_sibling()
            if expected is None:
                self.assertEqual(node, None)
            else:
                self.assertEqual(node.desc, expected)

    def _multi_get_last_sibling(self):
        data = [
            ('2', '4'),
            ('1', '4'),
            ('4', '4'),
            ('21', '24'),
            ('24', '24'),
            ('22', '24'),
            ('231', '231'),
        ]
        for desc, expected in data:
            node = self.model.objects.get(desc=desc).get_last_sibling()
            self.assertEqual(node.desc, expected)

    def _multi_get_first_child(self):
        data = [
            ('2', '21'),
            ('21', None),
            ('23', '231'),
            ('231', None),
        ]
        for desc, expected in data:
            node = self.model.objects.get(desc=desc).get_first_child()
            if expected is None:
                self.assertEqual(node, None)
            else:
                self.assertEqual(node.desc, expected)

    def _multi_get_last_child(self):
        data = [
            ('2', '24'),
            ('21', None),
            ('23', '231'),
            ('231', None),
        ]
        for desc, expected in data:
            node = self.model.objects.get(desc=desc).get_last_child()
            if expected is None:
                self.assertEqual(node, None)
            else:
                self.assertEqual(node.desc, expected)

    def _multi_get_ancestors(self):
        data = [
            ('2', []),
            ('21', ['2']),
            ('231', ['2', '23']),
        ]
        for desc, expected in data:
            nodes = self.model.objects.get(desc=desc).get_ancestors()
            self.assertEqual([node.desc for node in nodes], expected)

    def _multi_get_descendants(self):
        data = [
            ('2', ['21', '22', '23', '231', '24']),
            ('23', ['231']),
            ('231', []),
            ('1', []),
            ('4', ['41']),
        ]
        for desc, expected in data:
            nodes = self.model.objects.get(desc=desc).get_descendants()
            self.assertEqual([node.desc for node in nodes], expected)

    def _multi_get_descendant_count(self):
        data = [
            ('2', 5),
            ('23', 1),
            ('231', 0),
            ('1', 0),
            ('4', 1),
        ]
        for desc, expected in data:
            got = self.model.objects.get(desc=desc).get_descendant_count()
            self.assertEqual(got, expected)

    def _multi_is_sibling_of(self):
        data = [
            ('2', '2', True),
            ('2', '1', True),
            ('21', '2', False),
            ('231', '2', False),
            ('22', '23', True),
            ('231', '23', False),
            ('231', '231', True),
        ]
        for desc1, desc2, expected in data:
            node1 = self.model.objects.get(desc=desc1)
            node2 = self.model.objects.get(desc=desc2)
            self.assertEqual(node1.is_sibling_of(node2), expected)

    def _multi_is_child_of(self):
        data = [
            ('2', '2', False),
            ('2', '1', False),
            ('21', '2', True),
            ('231', '2', False),
            ('231', '23', True),
            ('231', '231', False),
        ]
        for desc1, desc2, expected in data:
            node1 = self.model.objects.get(desc=desc1)
            node2 = self.model.objects.get(desc=desc2)
            self.assertEqual(node1.is_child_of(node2), expected)

    def _multi_is_descendant_of(self):
        data = [
            ('2', '2', False),
            ('2', '1', False),
            ('21', '2', True),
            ('231', '2', True),
            ('231', '23', True),
            ('231', '231', False),
        ]
        for desc1, desc2, expected in data:
            node1 = self.model.objects.get(desc=desc1)
            node2 = self.model.objects.get(desc=desc2)
            self.assertEqual(node1.is_descendant_of(node2), expected)


class TestAddChild(TestNonEmptyTree):

    def _multi_add_child_to_leaf(self):
        self.model.objects.get(desc=u'231').add_child(desc='2311')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 1),
                    (u'2311', 4, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_add_child_to_node(self):
        self.model.objects.get(desc=u'2').add_child(desc='25')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 5),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'25', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


class TestAddSibling(TestNonEmptyTree):

    def _multi_add_sibling_invalid_pos(self):
        method = self.model.objects.get(desc=u'231').add_sibling
        self.assertRaises(InvalidPosition, method, 'invalid_pos')

    def _multi_add_sibling_missing_nodeorderby(self):
        node_wchildren = self.model.objects.get(desc=u'2')
        method = node_wchildren.add_sibling
        self.assertRaises(MissingNodeOrderBy, method, 'sorted-sibling',
                          desc='aaa')

    def _multi_add_sibling_last_root(self):
        node_wchildren = self.model.objects.get(desc=u'2')
        obj = node_wchildren.add_sibling('last-sibling', desc='5')
        self.assertEqual(obj.get_depth(), 1)
        self.assertEqual(node_wchildren.get_last_sibling().desc, u'5')

    def _multi_add_sibling_last(self):
        node = self.model.objects.get(desc=u'231')
        obj = node.add_sibling('last-sibling', desc='232')
        self.assertEqual(obj.get_depth(), 3)
        self.assertEqual(node.get_last_sibling().desc, u'232')

    def _multi_add_sibling_first_root(self):
        node_wchildren = self.model.objects.get(desc=u'2')
        obj = node_wchildren.add_sibling('first-sibling', desc='new')
        self.assertEqual(obj.get_depth(), 1)
        expected = [(u'new', 1, 0),
                    (u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_add_sibling_first(self):
        node_wchildren = self.model.objects.get(desc=u'23')
        obj = node_wchildren.add_sibling('first-sibling', desc='new')
        self.assertEqual(obj.get_depth(), 2)
        expected = [(u'1', 1, 0),
                    (u'2', 1, 5),
                    (u'new', 2, 0),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_add_sibling_left_root(self):
        node_wchildren = self.model.objects.get(desc=u'2')
        obj = node_wchildren.add_sibling('left', desc='new')
        self.assertEqual(obj.get_depth(), 1)
        expected = [(u'1', 1, 0),
                    (u'new', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_add_sibling_left(self):
        node_wchildren = self.model.objects.get(desc=u'23')
        obj = node_wchildren.add_sibling('left', desc='new')
        self.assertEqual(obj.get_depth(), 2)
        expected = [(u'1', 1, 0),
                    (u'2', 1, 5),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'new', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_add_sibling_left_noleft_root(self):
        node = self.model.objects.get(desc=u'1')
        obj = node.add_sibling('left', desc='new')
        self.assertEqual(obj.get_depth(), 1)
        expected = [(u'new', 1, 0),
                    (u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_add_sibling_left_noleft(self):
        node = self.model.objects.get(desc=u'231')
        obj = node.add_sibling('left', desc='new')
        self.assertEqual(obj.get_depth(), 3)
        expected = [(u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 2),
                    (u'new', 3, 0),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_add_sibling_right_root(self):
        node_wchildren = self.model.objects.get(desc=u'2')
        obj = node_wchildren.add_sibling('right', desc='new')
        self.assertEqual(obj.get_depth(), 1)
        expected = [(u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'new', 1, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_add_sibling_right(self):
        node_wchildren = self.model.objects.get(desc=u'23')
        obj = node_wchildren.add_sibling('right', desc='new')
        self.assertEqual(obj.get_depth(), 2)
        expected = [(u'1', 1, 0),
                    (u'2', 1, 5),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'new', 2, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_add_sibling_right_noright_root(self):
        node = self.model.objects.get(desc=u'4')
        obj = node.add_sibling('right', desc='new')
        self.assertEqual(obj.get_depth(), 1)
        expected = [(u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0),
                    (u'new', 1, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_add_sibling_right_noright(self):
        node = self.model.objects.get(desc=u'231')
        obj = node.add_sibling('right', desc='new')
        self.assertEqual(obj.get_depth(), 3)
        expected = [(u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 2),
                    (u'231', 3, 0),
                    (u'new', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


class TestDelete(TestNonEmptyTree):

    def setUp(self):
        super(TestDelete, self).setUp()
        for node in self.model.objects.all():
            self.dep_model(node=node).save()

    def _multi_delete_leaf(self):
        self.model.objects.get(desc=u'231').delete()
        expected = [(u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_delete_node(self):
        self.model.objects.get(desc=u'23').delete()
        expected = [(u'1', 1, 0),
                    (u'2', 1, 3),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_delete_root(self):
        self.model.objects.get(desc=u'2').delete()
        expected = [(u'1', 1, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_delete_filter_root_nodes(self):
        self.model.objects.filter(desc__in=('2', '3')).delete()
        expected = [(u'1', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_delete_filter_children(self):
        self.model.objects.filter(
            desc__in=('2', '23', '231')).delete()
        expected = [(u'1', 1, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_delete_nonexistant_nodes(self):
        self.model.objects.filter(desc__in=('ZZZ', 'XXX')).delete()
        self.assertEqual(self.got(), self.unchanged)

    def _multi_delete_same_node_twice(self):
        self.model.objects.filter(
            desc__in=('2', '2')).delete()
        expected = [(u'1', 1, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_delete_all_root_nodes(self):
        self.model.get_root_nodes().delete()
        count = self.model.objects.count()
        self.assertEqual(count, 0)

    def _multi_delete_all_nodes(self):
        self.model.objects.all().delete()
        count = self.model.objects.count()
        self.assertEqual(count, 0)


class TestMoveErrors(TestNonEmptyTree):

    def _multi_move_invalid_pos(self):
        node = self.model.objects.get(desc=u'231')
        self.assertRaises(InvalidPosition, node.move, node, 'invalid_pos')

    def _multi_move_to_descendant(self):
        node = self.model.objects.get(desc=u'2')
        target = self.model.objects.get(desc=u'231')
        self.assertRaises(InvalidMoveToDescendant, node.move, target,
            'first-sibling')

    def _multi_move_missing_nodeorderby(self):
        node = self.model.objects.get(desc=u'231')
        self.assertRaises(MissingNodeOrderBy, node.move, node,
                          'sorted-child')
        self.assertRaises(MissingNodeOrderBy, node.move, node,
                          'sorted-sibling')


class TestMoveSortedErrors(TestNonEmptyTree):

    def _multi_nonsorted_move_in_sorted(self):
        node = self.sorted_model.add_root(val1=3, val2=3, desc='zxy')
        self.assertRaises(InvalidPosition, node.move, node, 'left')


class TestMoveLeafRoot(TestNonEmptyTree):

    def _multi_move_leaf_last_sibling_root(self):
        self.model.objects.get(desc=u'231').move(
            self.model.objects.get(desc=u'2'), 'last-sibling')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0),
                    (u'231', 1, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_leaf_first_sibling_root(self):
        self.model.objects.get(desc=u'231').move(
            self.model.objects.get(desc=u'2'), 'first-sibling')
        expected = [(u'231', 1, 0),
                    (u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_leaf_left_sibling_root(self):
        self.model.objects.get(desc=u'231').move(
            self.model.objects.get(desc=u'2'), 'left')
        expected = [(u'1', 1, 0),
                    (u'231', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_leaf_right_sibling_root(self):
        self.model.objects.get(desc=u'231').move(
            self.model.objects.get(desc=u'2'), 'right')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 0),
                    (u'24', 2, 0),
                    (u'231', 1, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_leaf_last_child_root(self):
        self.model.objects.get(desc=u'231').move(
            self.model.objects.get(desc=u'2'), 'last-child')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 5),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 0),
                    (u'24', 2, 0),
                    (u'231', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_leaf_first_child_root(self):
        self.model.objects.get(desc=u'231').move(
            self.model.objects.get(desc=u'2'), 'first-child')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 5),
                    (u'231', 2, 0),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


class TestMoveLeaf(TestNonEmptyTree):

    def _multi_move_leaf_last_sibling(self):
        self.model.objects.get(desc=u'231').move(
            self.model.objects.get(desc=u'22'), 'last-sibling')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 5),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 0),
                    (u'24', 2, 0),
                    (u'231', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_leaf_first_sibling(self):
        self.model.objects.get(desc=u'231').move(
            self.model.objects.get(desc=u'22'), 'first-sibling')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 5),
                    (u'231', 2, 0),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_leaf_left_sibling(self):
        self.model.objects.get(desc=u'231').move(
            self.model.objects.get(desc=u'22'), 'left')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 5),
                    (u'21', 2, 0),
                    (u'231', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_leaf_right_sibling(self):
        self.model.objects.get(desc=u'231').move(
            self.model.objects.get(desc=u'22'), 'right')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 5),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'231', 2, 0),
                    (u'23', 2, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_leaf_left_sibling_itself(self):
        self.model.objects.get(desc=u'231').move(
            self.model.objects.get(desc=u'231'), 'left')
        self.assertEqual(self.got(), self.unchanged)

    def _multi_move_leaf_last_child(self):
        self.model.objects.get(desc=u'231').move(
            self.model.objects.get(desc=u'22'), 'last-child')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 1),
                    (u'231', 3, 0),
                    (u'23', 2, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_leaf_first_child(self):
        self.model.objects.get(desc=u'231').move(
            self.model.objects.get(desc=u'22'), 'first-child')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 1),
                    (u'231', 3, 0),
                    (u'23', 2, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


class TestMoveBranchRoot(TestNonEmptyTree):

    def _multi_move_branch_first_sibling_root(self):
        self.model.objects.get(desc='4').move(
            self.model.objects.get(desc='2'), 'first-sibling')
        expected = [(u'4', 1, 1),
                    (u'41', 2, 0),
                    (u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_branch_last_sibling_root(self):
        self.model.objects.get(desc='4').move(
            self.model.objects.get(desc='2'), 'last-sibling')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_branch_left_sibling_root(self):
        self.model.objects.get(desc='4').move(
            self.model.objects.get(desc='2'), 'left')
        expected = [(u'1', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_branch_right_sibling_root(self):
        self.model.objects.get(desc='4').move(
            self.model.objects.get(desc='2'), 'right')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0),
                    (u'3', 1, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_branch_left_noleft_sibling_root(self):
        self.model.objects.get(desc='4').move(
            self.model.objects.get(desc='2').get_first_sibling(), 'left')
        expected = [(u'4', 1, 1),
                    (u'41', 2, 0),
                    (u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_branch_right_noright_sibling_root(self):
        self.model.objects.get(desc='4').move(
            self.model.objects.get(desc='2').get_last_sibling(), 'right')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_branch_first_child_root(self):
        self.model.objects.get(desc='4').move(
            self.model.objects.get(desc='2'), 'first-child')
        expected = [(u'1', 1, 0),
                   (u'2', 1, 5),
                   (u'4', 2, 1),
                   (u'41', 3, 0),
                   (u'21', 2, 0),
                   (u'22', 2, 0),
                   (u'23', 2, 1),
                   (u'231', 3, 0),
                   (u'24', 2, 0),
                   (u'3', 1, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_branch_last_child_root(self):
        self.model.objects.get(desc='4').move(
            self.model.objects.get(desc='2'), 'last-child')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 5),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'4', 2, 1),
                    (u'41', 3, 0),
                    (u'3', 1, 0)]
        self.assertEqual(self.got(), expected)


class TestMoveBranch(TestNonEmptyTree):

    def _multi_move_branch_first_sibling(self):
        self.model.objects.get(desc='4').move(
            self.model.objects.get(desc='23'), 'first-sibling')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 5),
                    (u'4', 2, 1),
                    (u'41', 3, 0),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_branch_last_sibling(self):
        self.model.objects.get(desc='4').move(
            self.model.objects.get(desc='23'), 'last-sibling')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 5),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'4', 2, 1),
                    (u'41', 3, 0),
                    (u'3', 1, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_branch_left_sibling(self):
        self.model.objects.get(desc='4').move(
            self.model.objects.get(desc='23'), 'left')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 5),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'4', 2, 1),
                    (u'41', 3, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_branch_right_sibling(self):
        self.model.objects.get(desc='4').move(
            self.model.objects.get(desc='23'), 'right')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 5),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'4', 2, 1),
                    (u'41', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_branch_left_noleft_sibling(self):
        self.model.objects.get(desc='4').move(
            self.model.objects.get(desc='23').get_first_sibling(), 'left')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 5),
                    (u'4', 2, 1),
                    (u'41', 3, 0),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_branch_right_noright_sibling(self):
        self.model.objects.get(desc='4').move(
            self.model.objects.get(desc='23').get_last_sibling(), 'right')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 5),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 1),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'4', 2, 1),
                    (u'41', 3, 0),
                    (u'3', 1, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_branch_left_itself_sibling(self):
        self.model.objects.get(desc='4').move(
            self.model.objects.get(desc='4'), 'left')
        self.assertEqual(self.got(), self.unchanged)

    def _multi_move_branch_first_child(self):
        self.model.objects.get(desc='4').move(
            self.model.objects.get(desc='23'), 'first-child')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 2),
                    (u'4', 3, 1),
                    (u'41', 4, 0),
                    (u'231', 3, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_branch_last_child(self):
        self.model.objects.get(desc='4').move(
            self.model.objects.get(desc='23'), 'last-child')
        expected = [(u'1', 1, 0),
                    (u'2', 1, 4),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'23', 2, 2),
                    (u'231', 3, 0),
                    (u'4', 3, 1),
                    (u'41', 4, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0)]
        self.assertEqual(self.got(), expected)


class TestTreeSorted(TestTreeBase):

    def got(self):
        return [(o.val1, o.val2, o.desc, o.get_depth(), o.get_children_count())
                 for o in self.sorted_model.get_tree()]

    def _multi_add_root_sorted(self):
        self.sorted_model.add_root(val1=3, val2=3, desc='zxy')
        self.sorted_model.add_root(val1=1, val2=4, desc='bcd')
        self.sorted_model.add_root(val1=2, val2=5, desc='zxy')
        self.sorted_model.add_root(val1=3, val2=3, desc='abc')
        self.sorted_model.add_root(val1=4, val2=1, desc='fgh')
        self.sorted_model.add_root(val1=3, val2=3, desc='abc')
        self.sorted_model.add_root(val1=2, val2=2, desc='qwe')
        self.sorted_model.add_root(val1=3, val2=2, desc='vcx')
        expected = [(1, 4, u'bcd', 1, 0),
                    (2, 2, u'qwe', 1, 0),
                    (2, 5, u'zxy', 1, 0),
                    (3, 2, u'vcx', 1, 0),
                    (3, 3, u'abc', 1, 0),
                    (3, 3, u'abc', 1, 0),
                    (3, 3, u'zxy', 1, 0),
                    (4, 1, u'fgh', 1, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_add_child_root_sorted(self):
        root = self.sorted_model.add_root(val1=0, val2=0, desc='aaa')
        root.add_child(val1=3, val2=3, desc='zxy')
        root.add_child(val1=1, val2=4, desc='bcd')
        root.add_child(val1=2, val2=5, desc='zxy')
        root.add_child(val1=3, val2=3, desc='abc')
        root.add_child(val1=4, val2=1, desc='fgh')
        root.add_child(val1=3, val2=3, desc='abc')
        root.add_child(val1=2, val2=2, desc='qwe')
        root.add_child(val1=3, val2=2, desc='vcx')
        expected = [(0, 0, u'aaa', 1, 8),
                    (1, 4, u'bcd', 2, 0),
                    (2, 2, u'qwe', 2, 0),
                    (2, 5, u'zxy', 2, 0),
                    (3, 2, u'vcx', 2, 0),
                    (3, 3, u'abc', 2, 0),
                    (3, 3, u'abc', 2, 0),
                    (3, 3, u'zxy', 2, 0),
                    (4, 1, u'fgh', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_add_child_nonroot_sorted(self):

        get_node = lambda node_id: self.sorted_model.objects.get(pk=node_id)

        root_id = self.sorted_model.add_root(val1=0, val2=0, desc='a').id
        node_id = get_node(root_id).add_child(val1=0, val2=0, desc='ac').id
        get_node(root_id).add_child(val1=0, val2=0, desc='aa')
        get_node(root_id).add_child(val1=0, val2=0, desc='av')
        get_node(node_id).add_child(val1=0, val2=0, desc='aca')
        get_node(node_id).add_child(val1=0, val2=0, desc='acc')
        get_node(node_id).add_child(val1=0, val2=0, desc='acb')

        expected = [(0, 0, u'a', 1, 3),
                    (0, 0, u'aa', 2, 0),
                    (0, 0, u'ac', 2, 3),
                    (0, 0, u'aca', 3, 0),
                    (0, 0, u'acb', 3, 0),
                    (0, 0, u'acc', 3, 0),
                    (0, 0, u'av', 2, 0)]
        self.assertEqual(self.got(), expected)

    def _multi_move_sorted(self):
        self.sorted_model.add_root(val1=3, val2=3, desc='zxy')
        self.sorted_model.add_root(val1=1, val2=4, desc='bcd')
        self.sorted_model.add_root(val1=2, val2=5, desc='zxy')
        self.sorted_model.add_root(val1=3, val2=3, desc='abc')
        self.sorted_model.add_root(val1=4, val2=1, desc='fgh')
        self.sorted_model.add_root(val1=3, val2=3, desc='abc')
        self.sorted_model.add_root(val1=2, val2=2, desc='qwe')
        self.sorted_model.add_root(val1=3, val2=2, desc='vcx')
        root_nodes = self.sorted_model.get_root_nodes()
        target = root_nodes[0]
        for node in root_nodes[1:]:

            # because raw queries don't update django objects
            node = self.sorted_model.objects.get(pk=node.id)
            target = self.sorted_model.objects.get(pk=target.id)

            node.move(target, 'sorted-child')
        expected = [(1, 4, u'bcd', 1, 7),
                    (2, 2, u'qwe', 2, 0),
                    (2, 5, u'zxy', 2, 0),
                    (3, 2, u'vcx', 2, 0),
                    (3, 3, u'abc', 2, 0),
                    (3, 3, u'abc', 2, 0),
                    (3, 3, u'zxy', 2, 0),
                    (4, 1, u'fgh', 2, 0)]
        self.assertEqual(self.got(), expected)


class TestMP_TreeAlphabet(TestCase):

    def test_alphabet(self):
        if not os.getenv('TREEBEARD_TEST_ALPHABET', False):
            # run this test only if the enviroment variable is set
            return
        basealpha = numconv.BASE85
        got_err = False
        last_good = None
        for alphabetlen in range(35, len(basealpha) + 1):
            alphabet = basealpha[0:alphabetlen]
            expected = [alphabet[0] + char for char in alphabet[1:]]
            expected.extend([alphabet[1] + char for char in alphabet])
            expected.append(alphabet[2] + alphabet[0])

            # remove all nodes
            MP_TestNodeAlphabet.objects.all().delete()

            # change the model's alphabet
            MP_TestNodeAlphabet.alphabet = alphabet

            # insert root nodes
            for pos in range(len(alphabet) * 2):
                try:
                    MP_TestNodeAlphabet.add_root(numval=pos)
                except:
                    got_err = True
                    break
            if got_err:
                break
            got = [obj.path for obj in MP_TestNodeAlphabet.objects.all()]
            if got != expected:
                got_err = True
            last_good = alphabet
        print '\nThe best BASE85 based alphabet for your setup is: %s' \
            % (last_good, )


class TestHelpers(TestTreeBase):

    def setUp(self):
        for model in (MP_TestNode, AL_TestNode, NS_TestNode):
            model.load_bulk(BASE_DATA)
            for node in model.get_root_nodes():
                model.load_bulk(BASE_DATA, node)
            model.add_root(desc='5')

    def _multi_descendants_group_count_root(self):
        expected = [(o.desc, o.get_descendant_count())
                    for o in self.model.get_root_nodes()]
        got = [(o.desc, o.descendants_count)
               for o in self.model.get_descendants_group_count()]
        self.assertEqual(got, expected)

    def _multi_descendants_group_count_node(self):
        parent = self.model.get_root_nodes().get(desc='2')
        expected = [(o.desc, o.get_descendant_count())
                    for o in parent.get_children()]
        got = [(o.desc, o.descendants_count)
               for o in self.model.get_descendants_group_count(parent)]
        self.assertEqual(got, expected)


class TestMP_TreeSortedAutoNow(TestCase):
    """
    The sorting mechanism used by treebeard when adding a node can fail if the
    ordering is using an "auto_now" field
    """

    def test_sorted_by_autonow_workaround(self):
        """
        workaround
        """
        import datetime
        for i in range(1, 5):
            MP_TestNodeSortedAutoNow.add_root(desc='node%d' % (i, ),
                                             created=datetime.datetime.now())

    def test_sorted_by_autonow_FAIL(self):
        """
        This test asserts that we have a problem.
        fix this, somehow
        """
        MP_TestNodeSortedAutoNow.add_root(desc='node1')
        self.assertRaises(ValueError, MP_TestNodeSortedAutoNow.add_root,
                          desc='node2')


class TestMP_TreeStepOverflow(TestCase):

    def test_add_root(self):
        method = MP_TestNodeSmallStep.add_root
        for i in range(1, 10):
            method()
        self.assertRaises(PathOverflow, method)

    def test_add_child(self):
        root = MP_TestNodeSmallStep.add_root()
        method = root.add_child
        for i in range(1, 10):
            method()
        self.assertRaises(PathOverflow, method)

    def test_add_sibling(self):
        root = MP_TestNodeSmallStep.add_root()
        for i in range(1, 10):
            root.add_child()
        method = root.get_last_child().add_sibling
        positions = ('first-sibling', 'left', 'right', 'last-sibling')
        for pos in positions:
            self.assertRaises(PathOverflow, method, pos)

    def test_move(self):
        root = MP_TestNodeSmallStep.add_root()
        for i in range(1, 10):
            root.add_child()
        newroot = MP_TestNodeSmallStep.add_root()
        targets = [(root, ['first-child', 'last-child']),
                   (root.get_first_child(), ['first-sibling',
                                            'left',
                                            'right',
                                            'last-sibling'])]
        for target, positions in targets:
            for pos in positions:
                self.assertRaises(PathOverflow, newroot.move, target, pos)


class TestMP_TreeShortPath(TestCase):
    """
    Here we test a tree with a very small path field (max_length=4) and a
    steplen of 1
    """

    def test_short_path(self):
        obj = MP_TestNodeShortPath.add_root()
        obj = obj.add_child().add_child().add_child()
        self.assertRaises(PathOverflow, obj.add_child)


class TestMP_TreeFindProblems(TestTreeBase):

    def test_find_problems(self):
        model = MP_TestNodeAlphabet
        model.alphabet = '01234'
        model(path='01', depth=1, numchild=0, numval=0).save()
        model(path='1', depth=1, numchild=0, numval=0).save()
        model(path='111', depth=1, numchild=0, numval=0).save()
        model(path='abcd', depth=1, numchild=0, numval=0).save()
        model(path='qa#$%!', depth=1, numchild=0, numval=0).save()
        model(path='0201', depth=2, numchild=0, numval=0).save()
        model(path='020201', depth=3, numchild=0, numval=0).save()
        model(path='03', depth=1, numchild=2, numval=0).save()
        model(path='0301', depth=2, numchild=0, numval=0).save()
        model(path='030102', depth=3, numchild=10, numval=0).save()
        model(path='04', depth=10, numchild=1, numval=0).save()
        model(path='0401', depth=20, numchild=0, numval=0).save()

        evil_chars, bad_steplen, orphans, wrong_depth, wrong_numchild = \
                                                        model.find_problems()
        self.assertEqual(['abcd', 'qa#$%!'],
            [o.path for o in model.objects.filter(id__in=evil_chars)])
        self.assertEqual(['1', '111'],
            [o.path for o in model.objects.filter(id__in=bad_steplen)])
        self.assertEqual(['0201', '020201'],
            [o.path for o in model.objects.filter(id__in=orphans)])
        self.assertEqual(['03', '0301', '030102'],
            [o.path for o in model.objects.filter(id__in=wrong_numchild)])
        self.assertEqual(['04', '0401'],
            [o.path for o in model.objects.filter(id__in=wrong_depth)])


class TestMP_TreeFix(TestTreeBase):

    def setUp(self):
        super(TestMP_TreeFix, self).setUp()
        self.expected_no_holes = {
            MP_TestNodeShortPath: [
                (u'1', u'b', 1, 2),
                (u'11', u'u', 2, 1),
                (u'111', u'i', 3, 1),
                (u'1111', u'e', 4, 0),
                (u'12', u'o', 2, 0),
                (u'2', u'd', 1, 0),
                (u'3', u'g', 1, 0),
                (u'4', u'a', 1, 4),
                (u'41', u'a', 2, 0),
                (u'42', u'a', 2, 0),
                (u'43', u'u', 2, 1),
                (u'431', u'i', 3, 1),
                (u'4311', u'e', 4, 0),
                (u'44', u'o', 2, 0)],
            MP_TestSortedNodeShortPath: [
                (u'1', u'a', 1, 4),
                (u'11', u'a', 2, 0),
                (u'12', u'a', 2, 0),
                (u'13', u'o', 2, 0),
                (u'14', u'u', 2, 1),
                (u'141', u'i', 3, 1),
                (u'1411', u'e', 4, 0),
                (u'2', u'b', 1, 2),
                (u'21', u'o', 2, 0),
                (u'22', u'u', 2, 1),
                (u'221', u'i', 3, 1),
                (u'2211', u'e', 4, 0),
                (u'3', u'd', 1, 0),
                (u'4', u'g', 1, 0)]}
        self.expected_with_holes = {
            MP_TestNodeShortPath: [
                (u'1', u'b', 1L, 2L),
                (u'13', u'u', 2L, 1L),
                (u'134', u'i', 3L, 1L),
                (u'1343', u'e', 4L, 0L),
                (u'14', u'o', 2L, 0L),
                (u'2', u'd', 1L, 0L),
                (u'3', u'g', 1L, 0L),
                (u'4', u'a', 1L, 4L),
                (u'41', u'a', 2L, 0L),
                (u'42', u'a', 2L, 0L),
                (u'43', u'u', 2L, 1L),
                (u'434', u'i', 3L, 1L),
                (u'4343', u'e', 4L, 0L),
                (u'44', u'o', 2L, 0L)],
            MP_TestSortedNodeShortPath: [
                (u'1', u'b', 1L, 2L),
                (u'13', u'u', 2L, 1L),
                (u'134', u'i', 3L, 1L),
                (u'1343', u'e', 4L, 0L),
                (u'14', u'o', 2L, 0L),
                (u'2', u'd', 1L, 0L),
                (u'3', u'g', 1L, 0L),
                (u'4', u'a', 1L, 4L),
                (u'41', u'a', 2L, 0L),
                (u'42', u'a', 2L, 0L),
                (u'43', u'u', 2L, 1L),
                (u'434', u'i', 3L, 1L),
                (u'4343', u'e', 4L, 0L),
                (u'44', u'o', 2L, 0L)]}

    def got(self, model):
        return [(o.path, o.desc, o.get_depth(), o.get_children_count())
                for o in model.get_tree()]

    def add_broken_test_data(self, model):
        model(path='4', depth=2, numchild=2, desc='a').save()
        model(path='13', depth=1000, numchild=0, desc='u').save()
        model(path='14', depth=4, numchild=500, desc='o').save()
        model(path='134', depth=321, numchild=543, desc='i').save()
        model(path='1343', depth=321, numchild=543, desc='e').save()
        model(path='42', depth=1, numchild=1, desc='a').save()
        model(path='43', depth=1000, numchild=0, desc='u').save()
        model(path='44', depth=4, numchild=500, desc='o').save()
        model(path='434', depth=321, numchild=543, desc='i').save()
        model(path='4343', depth=321, numchild=543, desc='e').save()
        model(path='41', depth=1, numchild=1, desc='a').save()
        model(path='3', depth=221, numchild=322, desc='g').save()
        model(path='1', depth=10, numchild=3, desc='b').save()
        model(path='2', depth=10, numchild=3, desc='d').save()

    def test_fix_tree_non_destructive(self):

        for model in (MP_TestNodeShortPath, MP_TestSortedNodeShortPath):
            self.add_broken_test_data(model)
            model.fix_tree(destructive=False)
            self.assertEqual(self.got(model), self.expected_with_holes[model])
            model.find_problems()

    def test_fix_tree_destructive(self):

        for model in (MP_TestNodeShortPath, MP_TestSortedNodeShortPath):
            self.add_broken_test_data(model)
            model.fix_tree(destructive=True)
            self.assertEqual(self.got(model), self.expected_no_holes[model])
            model.find_problems()


class TestIssues(TestCase):
    "test for http://code.google.com/p/django-treebeard/issues/detail?id=14"

    def test_many_to_many_django_user_anonymous(self):
        if not HAS_DJANGO_AUTH:  # pragma: no cover
            self.fail('this test needs django.contrib.auth in INSTALLED_APPS')

        # Using AnonymousUser() in the querysets will expose non-treebeard
        # related problems in Django 1.0
        #
        # Postgres:
        #   ProgrammingError: can't adapt
        # SQLite:
        #   InterfaceError: Error binding parameter 4 - probably unsupported
        #   type.
        # MySQL compared a string to an integer field:
        #   `treebeard_mp_testissue14_users`.`user_id` = 'AnonymousUser'
        #
        # Using a None field instead works (will be translated to IS NULL).
        #
        # anonuserobj = AnonymousUser()
        anonuserobj = None

        def qs_check(qs, expected):
            self.assertEqual(
                [o.name for o in qs],
                expected)

        user = User.objects.create_user('test_user', 'test@example.com',
                                        'testpasswd')
        user.save()
        root = MP_TestIssue14.add_root(name="the root node")

        root.add_child(name="first")
        second = root.add_child(name="second")

        qs_check(root.get_children(), ['first', 'second'])
        qs_check(root.get_children().filter(Q(name="first")), ['first'])
        qs_check(root.get_children().filter(Q(users=user)), [])
        qs_check(
            root.get_children().filter(Q(name="first") | Q(users=user)),
            ['first'])

        user = anonuserobj
        qs_check(
            root.get_children().filter(Q(name="first") | Q(users=user)),
            ['first', 'second'])

        user = User.objects.get(username="test_user")
        second.users.add(user)

        qs_check(
            root.get_children().filter(Q(name="first") | Q(users=user)),
            ['first', 'second'])

        user = anonuserobj
        qs_check(
            root.get_children().filter(Q(name="first") | Q(users=user)),
            ['first'])


class TestModelAdmin(ModelAdmin):
    form = MoveNodeForm


class TestMoveNodeForm(TestTreeBase):

    tpl = (u'<tr><th><label for="id__position">Position:</label></th>'
           '<td><select name="_position" id="id__position">\n'
           '<option value="first-child">First child of</option>\n'
           '<option value="left">Before</option>\n'
           '<option value="right">After</option>\n'
           '</select></td></tr>\n'
           '<tr><th><label for="id__ref_node_id">Relative to:</label>'
           '</th><td><select name="_ref_node_id" id="id__ref_node_id">\n'
           '<option value="0">-- root --</option>\n')

    def _multi_form_html_root_node(self):
        self.model.load_bulk(BASE_DATA)
        node = self.model.get_tree()[0]
        form = MoveNodeForm(instance=node)
        rtpl = self.tpl
        self.assertEqual(['_position', '_ref_node_id'],
                         form.base_fields.keys())
        for obj in self.model.get_tree():
            if node != obj or obj.is_descendant_of(node):
                rtpl += '<option value="%d">%sNode %d</option>\n' % (
                    obj.id, '. . ' * (obj.get_depth() - 1), obj.id)
        rtpl += '</select></td></tr>'
        formstr = unicode(form).replace(u' selected="selected"', u'')
        self.assertEqual(rtpl, formstr)

    def _multi_form_html_leaf_node(self):
        self.model.load_bulk(BASE_DATA)
        nodes = list(self.model.get_tree())
        node = nodes[-1]
        form = MoveNodeForm(instance=node)
        rtpl = self.tpl
        self.assertEqual(['_position', '_ref_node_id'],
                         form.base_fields.keys())
        for obj in self.model.get_tree():
            if node != obj or obj.is_descendant_of(node):
                rtpl += '<option value="%d">%sNode %d</option>\n' % (
                    obj.id, '. . ' * (obj.get_depth() - 1), obj.id)
        rtpl += '</select></td></tr>'
        formstr = unicode(form).replace(u' selected="selected"', u'')
        self.assertEqual(rtpl, formstr)

    def _multi_admin_html(self):
        tpl = ('<tr><th><label for="id_desc">Desc:</label>'
               '</th><td><input id="id_desc" type="text" class="vTextField" '
               'name="desc" maxlength="255" /></td></tr>\n'
               '<tr><th><label for="id__position">Position:</label></th>'
               '<td><select name="_position" id="id__position">\n'
               '<option value="first-child">First child of</option>\n'
               '<option value="left">Before</option>\n'
               '<option value="right">After</option>\n'
               '</select></td></tr>\n'
               '<tr><th><label for="id__ref_node_id">Relative to:</label>'
               '</th><td><select name="_ref_node_id" id="id__ref_node_id">\n'
               '<option value="0">-- root --</option>\n'
               '<option value="%d">Node %d</option>\n'
               '<option value="%d">Node %d</option>\n'
               '<option value="%d">. . Node %d</option>\n'
               '<option value="%d">. . Node %d</option>\n'
               '<option value="%d">. . Node %d</option>\n'
               '<option value="%d">. . . . Node %d</option>\n'
               '<option value="%d">. . Node %d</option>\n'
               '<option value="%d">Node %d</option>\n'
               '<option value="%d">Node %d</option>\n'
               '<option value="%d">. . Node %d</option>\n'
               '</select></td></tr>')
        request = None
        self.model.load_bulk(BASE_DATA)
        for node in self.model.objects.all():
            site = AdminSite()
            ma = TestModelAdmin(self.model, site)
            self.assertEqual(
                ['desc', '_position', '_ref_node_id'],
                ma.get_form(request).base_fields.keys())
            self.assertEqual(
                [(None, {'fields': ['desc', '_position', '_ref_node_id']})],
                ma.get_fieldsets(request))
            self.assertEqual(
                [(None, {'fields': ['desc', '_position', '_ref_node_id']})],
                ma.get_fieldsets(request, node))
            form = ma.get_form(request)()
            ids = []
            for obj in self.model.get_tree():
                ids.extend([obj.id] * 2)
            self.assertEqual(tpl % tuple(ids), unicode(form))


_load_test_methods(TestMoveNodeForm)
_load_test_methods(TestEmptyTree)
_load_test_methods(TestClassMethods)
_load_test_methods(TestSimpleNodeMethods)
_load_test_methods(TestAddChild)
_load_test_methods(TestAddSibling)
_load_test_methods(TestDelete)
_load_test_methods(TestMoveErrors)
_load_test_methods(TestMoveLeafRoot)
_load_test_methods(TestMoveLeaf)
_load_test_methods(TestMoveBranchRoot)
_load_test_methods(TestMoveBranch)
_load_test_methods(TestHelpers)
# we didn't create extra sorted-proxy models
_load_test_methods(TestMoveSortedErrors, proxy=False)
_load_test_methods(TestTreeSorted, proxy=False)
