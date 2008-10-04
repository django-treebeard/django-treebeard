# -*- coding: utf-8 -*-
"""

    treebeard.tests
    ---------------

    Unit tests.

    :copyright: 2008 by Gustavo Picon
    :license: Apache License 2.0

"""

import os
from django.test import TestCase
from django.db import models

from treebeard import InvalidPosition, InvalidMoveToDescendant, \
    PathOverflow, MissingNodeOrderBy, numconv
from treebeard.mp_tree import MPNode

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


class MPTestNode(MPNode):
    steplen = 3

    desc = models.CharField(max_length=255)


class MPTestNodeSomeDep(models.Model):
    node = models.ForeignKey(MPTestNode)


class MPTestNodeSorted(MPNode):
    steplen = 1
    node_order_by = ['val1', 'val2', 'desc']
    val1 = models.IntegerField()
    val2 = models.IntegerField()
    desc = models.CharField(max_length=255)


class MPTestNodeAlphabet(MPNode):
    steplen = 2

    numval = models.IntegerField()


class MPTestNodeSmallStep(MPNode):
    steplen = 1
    alphabet = '0123456789'


class MPTestNodeSortedAutoNow(MPNode):
    desc = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)

    node_order_by = ['created']


class MPTestNodeShortPath(MPNode):
    steplen = 1
    alphabet = '01234'
    desc = models.CharField(max_length=255)

# This is how you change the default fields defined in a Django abstract class
# (in this case, MPNode), since Django doesn't allow overriding fields, only
# mehods and attributes
MPTestNodeShortPath._meta.get_field('path').max_length = 4


class TestSortedNodeShortPath(MPNode):
    steplen = 1
    alphabet = '01234'
    desc = models.CharField(max_length=255)

    node_order_by = ['desc']
TestSortedNodeShortPath._meta.get_field('path').max_length = 4



class TestTreeBase(TestCase):

    def setUp(self):
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

    def got(self):
        return [(o.desc, o.depth, o.numchild) for o in MPTestNode.objects.all()]



class TestEmptyTree(TestTreeBase):

    def test_load_bulk_empty(self):
        ids = MPTestNode.load_bulk(BASE_DATA)
        got_descs = [obj.desc for obj in MPTestNode.objects.filter(id__in=ids)]
        expected_descs = [x[0] for x in self.unchanged]
        self.assertEqual(sorted(got_descs), sorted(expected_descs))
        self.assertEqual(self.got(), self.unchanged)

    
    def test_dump_bulk_empty(self):
        self.assertEqual(MPTestNode.dump_bulk(), [])


    def test_add_root_empty(self):
        obj = MPTestNode.add_root(desc='1')
        expected = [(u'1', 1, 0)]
        self.assertEqual(self.got(), expected)


    def test_get_root_nodes_empty(self):
        got = MPTestNode.get_root_nodes()
        expected = []
        self.assertEqual([node.path for node in got], expected)


    def test_get_first_root_node_empty(self):
        got = MPTestNode.get_first_root_node()
        self.assertEqual(got, None)


    def test_get_last_root_node_empty(self):
        got = MPTestNode.get_last_root_node()
        self.assertEqual(got, None)



class TestNonEmptyTree(TestTreeBase):

    def setUp(self):
        super(TestNonEmptyTree, self).setUp()
        MPTestNode.load_bulk(BASE_DATA)
        self.leafnode = MPTestNode.objects.get(desc=u'231')
        self.node_children = MPTestNode.objects.get(desc=u'2')


class TestManagerMethods(TestNonEmptyTree):

    def setUp(self):
        super(TestManagerMethods, self).setUp()


    def test_load_bulk_existing(self):

        # inserting on an existing node

        ids = MPTestNode.load_bulk(BASE_DATA, self.leafnode)
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
        expected_descs = [u'1', u'2', u'21', u'22', u'23', u'231', u'24', u'3',
                          u'4', u'41']
        got_descs = [obj.desc for obj in MPTestNode.objects.filter(id__in=ids)]
        self.assertEqual(sorted(got_descs), sorted(expected_descs))
        self.assertEqual(self.got(), expected)


    def test_dump_bulk_all(self):
        self.assertEqual(MPTestNode.dump_bulk(keep_ids=False), BASE_DATA)


    def test_dump_bulk_node(self):
        MPTestNode.load_bulk(BASE_DATA, self.leafnode)
        expected = [{'data':{'desc':u'231'}, 'children':BASE_DATA}]
        self.assertEqual(MPTestNode.dump_bulk(self.leafnode, False), expected)


    def test_load_and_dump_bulk_keeping_ids(self):
        exp = MPTestNode.dump_bulk(keep_ids=True)
        MPTestNode.objects.all().delete()
        MPTestNode.load_bulk(exp, None, True)
        got = MPTestNode.dump_bulk(keep_ids=True)
        self.assertEqual(got, exp)


    def test_get_root_nodes(self):
        got = MPTestNode.get_root_nodes()
        expected = ['1', '2', '3', '4']
        self.assertEqual([node.desc for node in got], expected)


    def test_get_first_root_node(self):
        got = MPTestNode.get_first_root_node()
        self.assertEqual(got.desc, '1')


    def test_get_last_root_node(self):
        got = MPTestNode.get_last_root_node()
        self.assertEqual(got.desc, '4')


    def test_add_root(self):
        obj = MPTestNode.add_root(desc='5')
        self.assertEqual(obj.depth, 1)
        self.assertEqual(MPTestNode.get_last_root_node().desc, '5')



class TestSimpleNodeMethods(TestNonEmptyTree):

    def test_get_root(self):
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
            node = MPTestNode.objects.get(desc=desc).get_root()
            self.assertEqual(node.desc, expected)


    def test_get_parent(self):
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
            node = MPTestNode.objects.get(desc=desc)
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
            # asking get_parent to not use the parent cache (since we corrupted
            # it in the previous loop)
            parent = node.get_parent(True)
            if expected:
                self.assertEqual(parent.desc, expected)
            else:
                self.assertEqual(parent, None)

    
    def test_get_children(self):
        data = [
            ('2', ['21', '22', '23', '24']),
            ('23', ['231']),
            ('231', []),
        ]
        for desc, expected in data:
            children = MPTestNode.objects.get(desc=desc).get_children()
            self.assertEqual([node.desc for node in children], expected)


    def test_get_siblings(self):
        data = [
            ('2', ['1', '2', '3', '4']),
            ('21', ['21', '22', '23', '24']),
            ('231', ['231']),
        ]
        for desc, expected in data:
            siblings = MPTestNode.objects.get(desc=desc).get_siblings()
            self.assertEqual([node.desc for node in siblings], expected)


    def test_get_first_sibling(self):
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
            node = MPTestNode.objects.get(desc=desc).get_first_sibling()
            self.assertEqual(node.desc, expected)
    

    def test_get_prev_sibling(self):
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
            node = MPTestNode.objects.get(desc=desc).get_prev_sibling()
            if expected is None:
                self.assertEqual(node, None)
            else:
                self.assertEqual(node.desc, expected)
    
    
    def test_get_next_sibling(self):
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
            node = MPTestNode.objects.get(desc=desc).get_next_sibling()
            if expected is None:
                self.assertEqual(node, None)
            else:
                self.assertEqual(node.desc, expected)


    def test_get_last_sibling(self):
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
            node = MPTestNode.objects.get(desc=desc).get_last_sibling()
            self.assertEqual(node.desc, expected)


    def test_get_first_child(self):
        data = [
            ('2', '21'),
            ('21', None),
            ('23', '231'),
            ('231', None),
        ]
        for desc, expected in data:
            node = MPTestNode.objects.get(desc=desc).get_first_child()
            if expected is None:
                self.assertEqual(node, None)
            else:
                self.assertEqual(node.desc, expected)


    def test_get_last_child(self):
        data = [
            ('2', '24'),
            ('21', None),
            ('23', '231'),
            ('231', None),
        ]
        for desc, expected in data:
            node = MPTestNode.objects.get(desc=desc).get_last_child()
            if expected is None:
                self.assertEqual(node, None)
            else:
                self.assertEqual(node.desc, expected)


    def test_get_ancestors(self):
        data = [
            ('2', []),
            ('21', ['2']),
            ('231', ['2', '23']),
        ]
        for desc, expected in data:
            nodes = MPTestNode.objects.get(desc=desc).get_ancestors()
            self.assertEqual([node.desc for node in nodes], expected)


    def test_get_descendants(self):
        data = [
            ('2', ['21', '22', '23', '231', '24']),
            ('23', ['231']),
            ('231', []),
            ('1', []),
            ('4', ['41']),
        ]
        for desc, expected in data:
            nodes = MPTestNode.objects.get(desc=desc).get_descendants()
            self.assertEqual([node.desc for node in nodes], expected)


    def test_is_sibling_of(self):
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
            node1 = MPTestNode.objects.get(desc=desc1)
            node2 = MPTestNode.objects.get(desc=desc2)
            self.assertEqual(node1.is_sibling_of(node2), expected)



    def test_is_child_of(self):
        data = [
            ('2', '2', False),
            ('2', '1', False),
            ('21', '2', True),
            ('231', '2', False),
            ('231', '23', True),
            ('231', '231', False),
        ]
        for desc1, desc2, expected in data:
            node1 = MPTestNode.objects.get(desc=desc1)
            node2 = MPTestNode.objects.get(desc=desc2)
            self.assertEqual(node1.is_child_of(node2), expected)


    def test_is_descendant_of(self):
        data = [
            ('2', '2', False),
            ('2', '1', False),
            ('21', '2', True),
            ('231', '2', True),
            ('231', '23', True),
            ('231', '231', False),
        ]
        for desc1, desc2, expected in data:
            node1 = MPTestNode.objects.get(desc=desc1)
            node2 = MPTestNode.objects.get(desc=desc2)
            self.assertEqual(node1.is_descendant_of(node2), expected)


class TestAddChild(TestNonEmptyTree):

    def test_add_child_to_leaf(self):
        obj = MPTestNode.objects.get(desc=u'231').add_child(desc='2311')
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


    def test_add_child_to_node(self):
        obj = MPTestNode.objects.get(desc=u'2').add_child(desc='25')
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


    def test_add_sibling_invalid_pos(self):
        method =  MPTestNode.objects.get(desc=u'231').add_sibling
        self.assertRaises(InvalidPosition, method, 'invalid_pos')


    def test_add_sibling_missing_nodeorderby(self):
        method = self.node_children.add_sibling
        self.assertRaises(MissingNodeOrderBy, method, 'sorted-sibling',
                          desc='aaa')
    
    
    def test_add_sibling_last(self):
        obj = self.node_children.add_sibling('last-sibling', desc='5')
        self.assertEqual(obj.depth, 1)
        self.assertEqual(self.node_children.get_last_sibling().desc, u'5')

        obj = self.leafnode.add_sibling('last-sibling', desc='232')
        self.assertEqual(obj.depth, 3)
        self.assertEqual(self.leafnode.get_last_sibling().desc, u'232')


    def test_add_sibling_first(self):
        obj = self.node_children.add_sibling('first-sibling', desc='new')
        self.assertEqual(obj.depth, 1)
        expected = [( u'new', 1, 0),
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


    def test_add_sibling_left(self):
        obj = self.node_children.add_sibling('left', desc='new')
        self.assertEqual(obj.depth, 1)
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


    def test_add_sibling_left_noleft(self):
        obj = self.leafnode.add_sibling('left', desc='new')
        self.assertEqual(obj.depth, 3)
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


    def test_add_sibling_right(self):
        obj = self.node_children.add_sibling('right', desc='new')
        self.assertEqual(obj.depth, 1)
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


    def test_add_sibling_right_noright(self):
        obj = self.leafnode.add_sibling('right', desc='new')
        self.assertEqual(obj.depth, 3)
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
        for node in MPTestNode.objects.all():
            MPTestNodeSomeDep(node=node).save()

    def test_delete_leaf(self):
        MPTestNode.objects.get(desc=u'231').delete()
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


    def test_delete_node(self):
        MPTestNode.objects.get(desc=u'23').delete()
        expected = [(u'1', 1, 0),
                    (u'2', 1, 3),
                    (u'21', 2, 0),
                    (u'22', 2, 0),
                    (u'24', 2, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_delete_root(self):
        MPTestNode.objects.get(desc=u'2').delete()
        expected = [(u'1', 1, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_delete_filter_root_nodes(self):
        MPTestNode.objects.filter(desc__in=('2', '3')).delete()
        expected = [(u'1', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_delete_filter_children(self):
        MPTestNode.objects.filter(
            desc__in=('2', '23', '231')).delete()
        expected = [(u'1', 1, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_delete_nonexistant_nodes(self):
        MPTestNode.objects.filter(desc__in=('ZZZ', 'XXX')).delete()
        self.assertEqual(self.got(), self.unchanged)


    def test_delete_same_node_twice(self):
        MPTestNode.objects.filter(
            desc__in=('2', '2')).delete()
        expected = [(u'1', 1, 0),
                    (u'3', 1, 0),
                    (u'4', 1, 1),
                    (u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_delete_all_root_nodes(self):
        MPTestNode.get_root_nodes().delete()
        count = MPTestNode.objects.count()
        self.assertEqual(count, 0)


    def test_delete_all_nodes(self):
        MPTestNode.objects.all().delete()
        count = MPTestNode.objects.count()
        self.assertEqual(count, 0)



class TestMoveErrors(TestNonEmptyTree):

    def test_move_invalid_pos(self):
        node = MPTestNode.objects.get(desc=u'231')
        self.assertRaises(InvalidPosition, node.move, node, 'invalid_pos')


    def test_move_to_descendant(self):
        node = MPTestNode.objects.get(desc=u'2')
        target = MPTestNode.objects.get(desc=u'231')
        self.assertRaises(InvalidMoveToDescendant, node.move, target,
            'first-sibling')

    def test_nonsorted_move_in_sorted(self):
        node = MPTestNodeSorted.add_root(val1=3, val2=3, desc='zxy')
        self.assertRaises(InvalidPosition, node.move, node, 'left')


    def test_move_missing_nodeorderby(self):
        node = MPTestNode.objects.get(desc=u'231')
        self.assertRaises(MissingNodeOrderBy, node.move, node,
                          'sorted-child')
        self.assertRaises(MissingNodeOrderBy, node.move, node,
                          'sorted-sibling')




class TestMoveLeaf(TestNonEmptyTree):

    def setUp(self):
        super(TestMoveLeaf, self).setUp()
        self.node = MPTestNode.objects.get(desc=u'231')
        self.target = MPTestNode.objects.get(desc=u'2')


    def test_move_leaf_last_sibling(self):
        self.node.move(self.target, 'last-sibling')
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


    def test_move_leaf_first_sibling(self):
        self.node.move(self.target, 'first-sibling')
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


    def test_move_leaf_left_sibling(self):
        self.node.move(self.target, 'left')
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


    def test_move_leaf_right_sibling(self):
        self.node.move(self.target, 'right')
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


    def test_move_leaf_left_sibling_itself(self):
        self.node.move(self.node, 'left')
        self.assertEqual(self.got(), self.unchanged)


    def test_move_leaf_last_child(self):
        self.node.move(self.target, 'last-child')
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


    def test_move_leaf_first_child(self):
        self.node.move(self.target, 'first-child')
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



class TestMoveBranch(TestNonEmptyTree):

    def setUp(self):
        super(TestMoveBranch, self).setUp()
        self.node = MPTestNode.objects.get(desc='4')
        self.target = MPTestNode.objects.get(desc='23')


    def test_move_branch_first_sibling(self):
        self.node.move(self.target, 'first-sibling')
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


    def test_move_branch_last_sibling(self):
        self.node.move(self.target, 'last-sibling')
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


    def test_move_branch_left_sibling(self):
        self.node.move(self.target, 'left')
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


    def test_move_branch_right_sibling(self):
        self.node.move(self.target, 'right')
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


    def test_move_branch_left_noleft_sibling(self):
        self.node.move(self.target.get_first_sibling(), 'left')
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


    def test_move_branch_right_noright_sibling(self):
        self.node.move(self.target.get_last_sibling(), 'right')
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


    def test_move_branch_left_itself_sibling(self):
        self.node.move(self.node, 'left')
        self.assertEqual(self.got(), self.unchanged)


    def test_move_branch_first_child(self):
        self.node.move(self.target, 'first-child')
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


    def test_move_branch_last_child(self):
        self.node.move(self.target, 'last-child')
        expected =  [(u'1', 1, 0),
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



class TestTreeSorted(TestCase):

    def got(self):
        return [(o.val1, o.val2, o.desc, o.depth, o.numchild)
                 for o in MPTestNodeSorted.objects.all()]


    def test_add_root_sorted(self):
        MPTestNodeSorted.add_root(val1=3, val2=3, desc='zxy')
        MPTestNodeSorted.add_root(val1=1, val2=4, desc='bcd')
        MPTestNodeSorted.add_root(val1=2, val2=5, desc='zxy')
        MPTestNodeSorted.add_root(val1=3, val2=3, desc='abc')
        MPTestNodeSorted.add_root(val1=4, val2=1, desc='fgh')
        MPTestNodeSorted.add_root(val1=3, val2=3, desc='abc')
        MPTestNodeSorted.add_root(val1=2, val2=2, desc='qwe')
        MPTestNodeSorted.add_root(val1=3, val2=2, desc='vcx')
        expected = [(1, 4, u'bcd', 1, 0),
                    (2, 2, u'qwe', 1, 0),
                    (2, 5, u'zxy', 1, 0),
                    (3, 2, u'vcx', 1, 0),
                    (3, 3, u'abc', 1, 0),
                    (3, 3, u'abc', 1, 0),
                    (3, 3, u'zxy', 1, 0),
                    (4, 1, u'fgh', 1, 0)]
        self.assertEqual(self.got(), expected)


    def test_add_child_sorted(self):
        root = MPTestNodeSorted.add_root(val1=0, val2=0, desc='aaa')
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


    def test_move_sorted(self):
        MPTestNodeSorted.add_root(val1=3, val2=3, desc='zxy')
        MPTestNodeSorted.add_root(val1=1, val2=4, desc='bcd')
        MPTestNodeSorted.add_root(val1=2, val2=5, desc='zxy')
        MPTestNodeSorted.add_root(val1=3, val2=3, desc='abc')
        MPTestNodeSorted.add_root(val1=4, val2=1, desc='fgh')
        MPTestNodeSorted.add_root(val1=3, val2=3, desc='abc')
        MPTestNodeSorted.add_root(val1=2, val2=2, desc='qwe')
        MPTestNodeSorted.add_root(val1=3, val2=2, desc='vcx')
        root_nodes = MPTestNodeSorted.get_root_nodes()
        target = root_nodes[0]
        for node in root_nodes[1:]:
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


class TestTreeAlphabet(TestCase):

    def test_alphabet(self):
        if not os.getenv('TREEBEARD_TEST_ALPHABET', False):
            # run this test only if the enviroment variable is set
            return
        basealpha = numconv.BASE85
        got_err = False
        last_good = None
        for alphabetlen in range(35, len(basealpha)+1):
            alphabet = basealpha[0:alphabetlen]
            expected = [alphabet[0]+char for char in alphabet[1:]]
            expected.extend([alphabet[1]+char for char in alphabet])
            expected.append(alphabet[2]+alphabet[0])

            # remove all nodes
            MPTestNodeAlphabet.objects.all().delete()

            # change the model's alphabet
            MPTestNodeAlphabet.alphabet = alphabet

            # insert root nodes
            for pos in range(len(alphabet)*2):
                try:
                    MPTestNodeAlphabet.add_root(numval=pos)
                except:
                    got_err = True
                    break
            if not got_err:
                got = [obj.path for obj in MPTestNodeAlphabet.objects.all()]
                if got != expected:
                    got_err = True
            if got_err:
                break
            else:
                last_good = alphabet
        if last_good:
            print '\nThe best BASE85 based alphabet for your setup is: %s' \
                % (last_good,)
        else:
            # this should never happen
            self.fail("Couldn't find a default working alphabet for your setup!")



class TestTreeStepOverflow(TestCase):
    
    def test_add_root(self):
        method = MPTestNodeSmallStep.add_root
        for i in range(1, 10):
            method()
        self.assertRaises(PathOverflow, method)

    def test_add_child(self):
        root = MPTestNodeSmallStep.add_root()
        method = root.add_child
        for i in range(1, 10):
            method()
        self.assertRaises(PathOverflow, method)

    def test_add_sibling(self):
        root = MPTestNodeSmallStep.add_root()
        for i in range(1, 10):
            root.add_child()
        method = root.get_last_child().add_sibling
        positions = ('first-sibling', 'left', 'right', 'last-sibling')
        for pos in positions:
            self.assertRaises(PathOverflow, method, pos)

    def test_move(self):
        root = MPTestNodeSmallStep.add_root()
        for i in range(1, 10):
            root.add_child()
        newroot = MPTestNodeSmallStep.add_root()
        targets = [(root, ['first-child', 'last-child']),
                   (root.get_first_child(), ['first-sibling',
                                            'left',
                                            'right',
                                            'last-sibling'])]
        for target, positions in targets:
            for pos in positions:
                self.assertRaises(PathOverflow, newroot.move, target, pos)



class TestTreeSortedAutoNow(TestCase):
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
            MPTestNodeSortedAutoNow.add_root(desc='node%d' % (i,),
                                           created=datetime.datetime.now())

    def test_sorted_by_autonow_FAIL(self):
        """
        This test asserts that we have a problem.
        fix this, somehow
        """
        MPTestNodeSortedAutoNow.add_root(desc='node1')
        self.assertRaises(ValueError, MPTestNodeSortedAutoNow.add_root, desc='node2')



class TestTreeShortPath(TestCase):
    """
    Here we test a tree with a very small path field (max_length=4) and a
    steplen of 1
    """
    def test_short_path(self):
        obj = MPTestNodeShortPath.add_root().add_child().add_child().add_child()
        self.assertRaises(PathOverflow, obj.add_child)



class TestFindProblems(TestTreeBase):

    def test_find_problems(self):
        model = MPTestNodeAlphabet
        model.alphabet = '012'
        model(path='01', depth=1, numchild=0, numval=0).save()
        model(path='1', depth=1, numchild=0, numval=0).save()
        model(path='111', depth=1, numchild=0, numval=0).save()
        model(path='abcd', depth=1, numchild=0, numval=0).save()
        model(path='qa#$%!', depth=1, numchild=0, numval=0).save()
        model(path='0201', depth=2, numchild=0, numval=0).save()
        model(path='020201', depth=3, numchild=0, numval=0).save()

        evil_chars, bad_steplen, orphans = model.find_problems()
        self.assertEqual(['abcd', 'qa#$%!'],
            [o.path for o in model.objects.filter(id__in=evil_chars)])
        self.assertEqual(['1', '111'],
            [o.path for o in model.objects.filter(id__in=bad_steplen)])
        self.assertEqual(['0201', '020201'],
            [o.path for o in model.objects.filter(id__in=orphans)])



class TestFixTree(TestTreeBase):

    def got(self, model):
        return [(o.path, o.desc, o.depth, o.numchild) for o in model.objects.all()]


    def test_fix_tree(self):
        # (o.path, o.desc, o.depth, o.numchild)
        expected_unsorted = [(u'1', u'b', 1, 2),
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
                             (u'44', u'o', 2, 0)]
        expected_sorted = [(u'1', u'a', 1, 4),
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
                           (u'4', u'g', 1, 0)]

        for model in (MPTestNodeShortPath, TestSortedNodeShortPath):
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
        MPTestNodeShortPath.fix_tree()
        self.assertEqual(self.got(MPTestNodeShortPath), expected_unsorted)
        
        TestSortedNodeShortPath.fix_tree()
        self.assertEqual(self.got(TestSortedNodeShortPath), expected_sorted)


class TestHelpers(TestTreeBase):

    def setUp(self):
        MPTestNode.load_bulk(BASE_DATA)
        for node in MPTestNode.get_root_nodes():
            MPTestNode.load_bulk(BASE_DATA, node)
        MPTestNode.add_root(desc='5')

    def test_descendants_group_count_root(self):
        expected = [(o.desc, o.get_descendants().count())
                    for o in MPTestNode.get_root_nodes()]
        got = [(o.desc, o.descendants_count)
               for o in MPTestNode.get_descendants_group_count()]
        self.assertEqual(got, expected)


    def test_descendants_group_count_node(self):
        parent = MPTestNode.objects.filter(depth=1).get(desc='2')
        expected = [(o.desc, o.get_descendants().count())
                    for o in parent.get_children()]
        got = [(o.desc, o.descendants_count)
               for o in MPTestNode.get_descendants_group_count(parent)]
        self.assertEqual(got, expected)

#~
