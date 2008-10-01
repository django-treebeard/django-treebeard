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
from treebeard import MPNode, InvalidPosition, InvalidMoveToDescendant, \
    PathOverflow, MissingNodeOrderBy, numconv

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


class TestNode(MPNode):
    steplen = 3

    desc = models.CharField(max_length=255)


class SomeDepForTestNode(models.Model):
    node = models.ForeignKey(TestNode)


class TestNodeSorted(MPNode):
    steplen = 1
    node_order_by = ['val1', 'val2', 'desc']
    val1 = models.IntegerField()
    val2 = models.IntegerField()
    desc = models.CharField(max_length=255)


class TestNodeAlphabet(MPNode):
    steplen = 2

    numval = models.IntegerField()


class TestNodeSmallStep(MPNode):
    steplen = 1
    alphabet = '0123456789'


class TestNodeSortedAutoNow(MPNode):
    desc = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)

    node_order_by = ['created']


class TestNodeShortPath(MPNode):
    steplen = 1
    alphabet = '01234'
    desc = models.CharField(max_length=255)

# This is how you change the default fields defined in a Django abstract class
# (in this case, MPNode), since Django doesn't allow overriding fields, only
# mehods and attributes
TestNodeShortPath._meta.get_field('path').max_length = 4


class TestSortedNodeShortPath(MPNode):
    steplen = 1
    alphabet = '01234'
    desc = models.CharField(max_length=255)

    node_order_by = ['desc']
TestSortedNodeShortPath._meta.get_field('path').max_length = 4



class TestTreeBase(TestCase):

    def setUp(self):
        self.unchanged = [(u'001', u'1', 1, 0),
                          (u'002', u'2', 1, 4),
                          (u'002001', u'21', 2, 0),
                          (u'002002', u'22', 2, 0),
                          (u'002003', u'23', 2, 1),
                          (u'002003001', u'231', 3, 0),
                          (u'002004', u'24', 2, 0),
                          (u'003', u'3', 1, 0),
                          (u'004', u'4', 1, 1),
                          (u'004001', u'41', 2, 0)]


    def got(self, tree=1):
        return [(o.path, o.desc, o.depth, o.numchild) for o in TestNode.objects.all()]



class TestEmptyTree(TestTreeBase):

    def test_keylen(self):
        self.assertEqual(TestNode.steplen, 3)


    def test_load_bulk_empty(self):
        paths = TestNode.load_bulk(BASE_DATA)
        self.assertEqual(paths, [x[0] for x in self.unchanged])
        self.assertEqual(self.got(), self.unchanged)

    
    def test_dump_bulk_empty(self):
        self.assertEqual(TestNode.dump_bulk(), [])


    def test_add_root_empty(self):
        obj = TestNode.add_root(desc='1')
        expected = [(u'001', u'1', 1, 0)]
        self.assertEqual(self.got(), expected)


    def test_get_root_nodes_empty(self):
        got = TestNode.get_root_nodes()
        expected = []
        self.assertEqual([node.path for node in got], expected)


    def test_get_first_root_node_empty(self):
        got = TestNode.get_first_root_node()
        self.assertEqual(got, None)


    def test_get_last_root_node_empty(self):
        got = TestNode.get_last_root_node()
        self.assertEqual(got, None)



class TestNonEmptyTree(TestTreeBase):

    def setUp(self):
        super(TestNonEmptyTree, self).setUp()
        TestNode.load_bulk(BASE_DATA)
        self.leafnode = TestNode.objects.get(path=u'002003001')
        self.node_children = TestNode.objects.get(path=u'002')


class TestManagerMethods(TestNonEmptyTree):

    def setUp(self):
        super(TestManagerMethods, self).setUp()


    def test_load_bulk_existing(self):

        # inserting on an existing node

        ids = TestNode.load_bulk(BASE_DATA, self.leafnode)
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 4),
                    (u'002001', u'21', 2, 0),
                    (u'002002', u'22', 2, 0),
                    (u'002003', u'23', 2, 1),
                    (u'002003001', u'231', 3, 4),
                    (u'002003001001', u'1', 4, 0),
                    (u'002003001002', u'2', 4, 4),
                    (u'002003001002001', u'21', 5, 0),
                    (u'002003001002002', u'22', 5, 0),
                    (u'002003001002003', u'23', 5, 1),
                    (u'002003001002003001', u'231', 6, 0),
                    (u'002003001002004', u'24', 5, 0),
                    (u'002003001003', u'3', 4, 0),
                    (u'002003001004', u'4', 4, 1),
                    (u'002003001004001', u'41', 5, 0),
                    (u'002004', u'24', 2, 0),
                    (u'003', u'3', 1, 0),
                    (u'004', u'4', 1, 1),
                    (u'004001', u'41', 2, 0)]
        expected_ids = [u'002003001001',
                        u'002003001002',
                        u'002003001002001',
                        u'002003001002002',
                        u'002003001002003',
                        u'002003001002003001',
                        u'002003001002004',
                        u'002003001003',
                        u'002003001004',
                        u'002003001004001']
        self.assertEqual(ids, expected_ids)
        self.assertEqual(self.got(), expected)


    def test_dump_bulk_all(self):
        self.assertEqual(TestNode.dump_bulk(keep_ids=False), BASE_DATA)


    def test_dump_bulk_node(self):
        TestNode.load_bulk(BASE_DATA, self.leafnode)
        expected = [{'data':{'desc':u'231'}, 'children':BASE_DATA}]
        self.assertEqual(TestNode.dump_bulk(self.leafnode, False), expected)

    def test_load_and_dump_bulk_keeping_ids(self):
        exp = TestNode.dump_bulk(keep_ids=True)
        TestNode.objects.all().delete()
        TestNode.load_bulk(exp, None, True)
        got = TestNode.dump_bulk(keep_ids=True)
        self.assertEqual(got, exp)



    def test_add_root(self):
        obj = TestNode.add_root(desc='5')
        self.assertEqual(obj.path, u'005')
        self.assertEqual(obj.depth, 1)


    def test_get_root_nodes(self):
        got = TestNode.get_root_nodes()
        expected = ['001', '002', '003', '004']
        self.assertEqual([node.path for node in got], expected)


    def test_get_first_root_node_empty(self):
        got = TestNode.get_first_root_node()
        self.assertEqual(got.path, '001')


    def test_get_last_root_node_empty(self):
        got = TestNode.get_last_root_node()
        self.assertEqual(got.path, '004')



class TestSimpleNodeMethods(TestNonEmptyTree):

    def test_get_root(self):
        data = [
            ('002', '002'),
            ('001', '001'),
            ('004', '004'),
            ('002001', '002'),
            ('002004', '002'),
            ('002002', '002'),
            ('002003001', '002'),
        ]
        for path, expected in data:
            node = TestNode.objects.get(path=path).get_root()
            self.assertEqual(node.path, expected)


    def test_get_parent(self):
        data = [
            ('002', None),
            ('001', None),
            ('004', None),
            ('002001', '002'),
            ('002004', '002'),
            ('002002', '002'),
            ('002003001', '002003'),
        ]
        data = dict(data)
        objs = {}
        for path, expected in data.items():
            node = TestNode.objects.get(path=path)
            parent = node.get_parent()
            if expected:
                self.assertEqual(parent.path, expected)
            else:
                self.assertEqual(parent, None)
            objs[path] = node
            # corrupt the objects' parent cache
            node._parent_obj = 'CORRUPTED!!!'

        for path, expected in data.items():
            node = objs[path]
            # asking get_parent to not use the parent cache (since we corrupted
            # it in the previous loop)
            parent = node.get_parent(True)
            if expected:
                self.assertEqual(parent.path, expected)
            else:
                self.assertEqual(parent, None)

    
    def test_get_children(self):
        data = [
            ('002', ['002001', '002002', '002003', '002004']),
            ('002003', ['002003001']),
            ('002003001', []),
        ]
        for path, expected in data:
            children = TestNode.objects.get(path=path).get_children()
            self.assertEqual([node.path for node in children], expected)


    def test_get_siblings(self):
        data = [
            ('002', ['001', '002', '003', '004']),
            ('002001', ['002001', '002002', '002003', '002004']),
            ('002003001', ['002003001']),
        ]
        for path, expected in data:
            siblings = TestNode.objects.get(path=path).get_siblings()
            self.assertEqual([node.path for node in siblings], expected)


    def test_get_first_sibling(self):
        data = [
            ('002', '001'),
            ('001', '001'),
            ('004', '001'),
            ('002001', '002001'),
            ('002004', '002001'),
            ('002002', '002001'),
            ('002003001', '002003001'),
        ]
        for path, expected in data:
            node = TestNode.objects.get(path=path).get_first_sibling()
            self.assertEqual(node.path, expected)
    

    def test_get_prev_sibling(self):
        data = [
            ('002', '001'),
            ('001', None),
            ('004', '003'),
            ('002001', None),
            ('002004', '002003'),
            ('002002', '002001'),
            ('002003001', None),
        ]
        for path, expected in data:
            node = TestNode.objects.get(path=path).get_prev_sibling()
            if expected is None:
                self.assertEqual(node, None)
            else:
                self.assertEqual(node.path, expected)
    
    
    def test_get_next_sibling(self):
        data = [
            ('002', '003'),
            ('001', '002'),
            ('004', None),
            ('002001', '002002'),
            ('002004', None),
            ('002002', '002003'),
            ('002003001', None),
        ]
        for path, expected in data:
            node = TestNode.objects.get(path=path).get_next_sibling()
            if expected is None:
                self.assertEqual(node, None)
            else:
                self.assertEqual(node.path, expected)


    def test_get_last_sibling(self):
        data = [
            ('002', '004'),
            ('001', '004'),
            ('004', '004'),
            ('002001', '002004'),
            ('002004', '002004'),
            ('002002', '002004'),
            ('002003001', '002003001'),
        ]
        for path, expected in data:
            node = TestNode.objects.get(path=path).get_last_sibling()
            self.assertEqual(node.path, expected)


    def test_get_first_child(self):
        data = [
            ('002', '002001'),
            ('002001', None),
            ('002003', '002003001'),
            ('002003001', None),
        ]
        for path, expected in data:
            node = TestNode.objects.get(path=path).get_first_child()
            if expected is None:
                self.assertEqual(node, None)
            else:
                self.assertEqual(node.path, expected)


    def test_get_last_child(self):
        data = [
            ('002', '002004'),
            ('002001', None),
            ('002003', '002003001'),
            ('002003001', None),
        ]
        for path, expected in data:
            node = TestNode.objects.get(path=path).get_last_child()
            if expected is None:
                self.assertEqual(node, None)
            else:
                self.assertEqual(node.path, expected)


    def test_get_ancestors(self):
        data = [
            ('002', []),
            ('002001', ['002']),
            ('002003001', ['002', '002003']),
        ]
        for path, expected in data:
            nodes = TestNode.objects.get(path=path).get_ancestors()
            self.assertEqual([node.path for node in nodes], expected)


    def test_get_descendants(self):
        data = [
            ('002', ['002001', '002002', '002003', '002003001', '002004']),
            ('002003', ['002003001']),
            ('002003001', []),
            ('001', []),
            ('004', ['004001']),
        ]
        for path, expected in data:
            nodes = TestNode.objects.get(path=path).get_descendants()
            self.assertEqual([node.path for node in nodes], expected)


    def test_is_sibling_of(self):
        data = [
            ('002', '002', True),
            ('002', '001', True),
            ('002001', '002', False),
            ('002003001', '002', False),
            ('002002', '002003', True),
            ('002003001', '002003', False),
            ('002003001', '002003001', True),
        ]
        for path1, path2, expected in data:
            node1 = TestNode.objects.get(path=path1)
            node2 = TestNode.objects.get(path=path2)
            self.assertEqual(node1.is_sibling_of(node2), expected)



    def test_is_child_of(self):
        data = [
            ('002', '002', False),
            ('002', '001', False),
            ('002001', '002', True),
            ('002003001', '002', False),
            ('002003001', '002003', True),
            ('002003001', '002003001', False),
        ]
        for path1, path2, expected in data:
            node1 = TestNode.objects.get(path=path1)
            node2 = TestNode.objects.get(path=path2)
            self.assertEqual(node1.is_child_of(node2), expected)


    def test_is_descendant_of(self):
        data = [
            ('002', '002', False),
            ('002', '001', False),
            ('002001', '002', True),
            ('002003001', '002', True),
            ('002003001', '002003', True),
            ('002003001', '002003001', False),
        ]
        for path1, path2, expected in data:
            node1 = TestNode.objects.get(path=path1)
            node2 = TestNode.objects.get(path=path2)
            self.assertEqual(node1.is_descendant_of(node2), expected)


class TestAddChild(TestNonEmptyTree):

    def test_add_child_to_leaf(self):
        obj = TestNode.objects.get(path=u'002003001').add_child(desc='2311')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 4),
                    (u'002001', u'21', 2, 0),
                    (u'002002', u'22', 2, 0),
                    (u'002003', u'23', 2, 1),
                    (u'002003001', u'231', 3, 1),
                    (u'002003001001', u'2311', 4, 0),
                    (u'002004', u'24', 2, 0),
                    (u'003', u'3', 1, 0),
                    (u'004', u'4', 1, 1),
                    (u'004001', u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_add_child_to_node(self):
        obj = TestNode.objects.get(path=u'002').add_child(desc='25')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 5),
                    (u'002001', u'21', 2, 0),
                    (u'002002', u'22', 2, 0),
                    (u'002003', u'23', 2, 1),
                    (u'002003001', u'231', 3, 0),
                    (u'002004', u'24', 2, 0),
                    (u'002005', u'25', 2, 0),
                    (u'003', u'3', 1, 0),
                    (u'004', u'4', 1, 1),
                    (u'004001', u'41', 2, 0)]
        self.assertEqual(self.got(), expected)



class TestAddSibling(TestNonEmptyTree):


    def test_add_sibling_invalid_pos(self):
        method =  TestNode.objects.get(path=u'002003001').add_sibling
        self.assertRaises(InvalidPosition, method, 'invalid_pos')


    def test_add_sibling_missing_nodeorderby(self):
        method = self.node_children.add_sibling
        self.assertRaises(MissingNodeOrderBy, method, 'sorted-sibling',
                          desc='aaa')
    
    
    def test_add_sibling_last(self):
        obj = self.node_children.add_sibling('last-sibling', desc='5')
        self.assertEqual(obj.path, u'005')
        self.assertEqual(obj.depth, 1)

        obj = self.leafnode.add_sibling('last-sibling', desc='232')
        self.assertEqual(obj.path, u'002003002')
        self.assertEqual(obj.depth, 3)


    def test_add_sibling_first(self):
        obj = self.node_children.add_sibling('first-sibling', desc='new')
        self.assertEqual(obj.path, u'001')
        expected = [(u'001', u'new', 1, 0),
                    (u'002', u'1', 1, 0),
                    (u'003', u'2', 1, 4),
                    (u'003001', u'21', 2, 0),
                    (u'003002', u'22', 2, 0),
                    (u'003003', u'23', 2, 1),
                    (u'003003001', u'231', 3, 0),
                    (u'003004', u'24', 2, 0),
                    (u'004', u'3', 1, 0),
                    (u'005', u'4', 1, 1),
                    (u'005001', u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_add_sibling_left(self):
        obj = self.node_children.add_sibling('left', desc='new')
        self.assertEqual(obj.path, u'002')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'new', 1, 0),
                    (u'003', u'2', 1, 4),
                    (u'003001', u'21', 2, 0),
                    (u'003002', u'22', 2, 0),
                    (u'003003', u'23', 2, 1),
                    (u'003003001', u'231', 3, 0),
                    (u'003004', u'24', 2, 0),
                    (u'004', u'3', 1, 0),
                    (u'005', u'4', 1, 1),
                    (u'005001', u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_add_sibling_left_noleft(self):
        obj = self.leafnode.add_sibling('left', desc='new')
        self.assertEqual(obj.path, u'002003001')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 4),
                    (u'002001', u'21', 2, 0),
                    (u'002002', u'22', 2, 0),
                    (u'002003', u'23', 2, 2),
                    (u'002003001', u'new', 3, 0),
                    (u'002003002', u'231', 3, 0),
                    (u'002004', u'24', 2, 0),
                    (u'003', u'3', 1, 0),
                    (u'004', u'4', 1, 1),
                    (u'004001', u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_add_sibling_right(self):
        obj = self.node_children.add_sibling('right', desc='new')
        self.assertEqual(obj.path, u'003')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 4),
                    (u'002001', u'21', 2, 0),
                    (u'002002', u'22', 2, 0),
                    (u'002003', u'23', 2, 1),
                    (u'002003001', u'231', 3, 0),
                    (u'002004', u'24', 2, 0),
                    (u'003', u'new', 1, 0),
                    (u'004', u'3', 1, 0),
                    (u'005', u'4', 1, 1),
                    (u'005001', u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_add_sibling_right_noright(self):
        obj = self.leafnode.add_sibling('right', desc='new')
        self.assertEqual(obj.path, u'002003002')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 4),
                    (u'002001', u'21', 2, 0),
                    (u'002002', u'22', 2, 0),
                    (u'002003', u'23', 2, 2),
                    (u'002003001', u'231', 3, 0),
                    (u'002003002', u'new', 3, 0),
                    (u'002004', u'24', 2, 0),
                    (u'003', u'3', 1, 0),
                    (u'004', u'4', 1, 1),
                    (u'004001', u'41', 2, 0)]
        self.assertEqual(self.got(), expected)



class TestDelete(TestNonEmptyTree):

    def setUp(self):
        super(TestDelete, self).setUp()
        for node in TestNode.objects.all():
            SomeDepForTestNode(node=node).save()

    def test_delete_leaf(self):
        TestNode.objects.get(path=u'002003001').delete()
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 4),
                    (u'002001', u'21', 2, 0),
                    (u'002002', u'22', 2, 0),
                    (u'002003', u'23', 2, 0),
                    (u'002004', u'24', 2, 0),
                    (u'003', u'3', 1, 0),
                    (u'004', u'4', 1, 1),
                    (u'004001', u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_delete_node(self):
        TestNode.objects.get(path=u'002003').delete()
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 3),
                    (u'002001', u'21', 2, 0),
                    (u'002002', u'22', 2, 0),
                    (u'002004', u'24', 2, 0),
                    (u'003', u'3', 1, 0),
                    (u'004', u'4', 1, 1),
                    (u'004001', u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_delete_root(self):
        TestNode.objects.get(path=u'002').delete()
        expected = [(u'001', u'1', 1, 0),
                    (u'003', u'3', 1, 0),
                    (u'004', u'4', 1, 1),
                    (u'004001', u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_delete_filter_root_nodes(self):
        TestNode.objects.filter(path__in=('002', '003')).delete()
        expected = [(u'001', u'1', 1, 0),
                    (u'004', u'4', 1, 1),
                    (u'004001', u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_delete_filter_children(self):
        TestNode.objects.filter(
            path__in=('002', '002003', '002003001')).delete()
        expected = [(u'001', u'1', 1, 0),
                    (u'003', u'3', 1, 0),
                    (u'004', u'4', 1, 1),
                    (u'004001', u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_delete_nonexistant_nodes(self):
        TestNode.objects.filter(path__in=('ZZZ', 'XXX')).delete()
        self.assertEqual(self.got(), self.unchanged)


    def test_delete_same_node_twice(self):
        TestNode.objects.filter(
            path__in=('002', '002')).delete()
        expected = [(u'001', u'1', 1, 0),
                    (u'003', u'3', 1, 0),
                    (u'004', u'4', 1, 1),
                    (u'004001', u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_delete_all_root_nodes(self):
        TestNode.get_root_nodes().delete()
        count = TestNode.objects.count()
        self.assertEqual(count, 0)


    def test_delete_all_nodes(self):
        TestNode.objects.all().delete()
        count = TestNode.objects.count()
        self.assertEqual(count, 0)



class TestMoveErrors(TestNonEmptyTree):

    def test_move_invalid_pos(self):
        node = TestNode.objects.get(path=u'002003001')
        self.assertRaises(InvalidPosition, node.move, node, 'invalid_pos')


    def test_move_to_descendant(self):
        node = TestNode.objects.get(path=u'002')
        target = TestNode.objects.get(path=u'002003001')
        self.assertRaises(InvalidMoveToDescendant, node.move, target,
            'first-sibling')

    def test_nonsorted_move_in_sorted(self):
        TestNodeSorted.add_root(val1=3, val2=3, desc='zxy')
        node = TestNodeSorted.objects.get(path=u'1')
        self.assertRaises(InvalidPosition, node.move, node, 'left')


    def test_move_missing_nodeorderby(self):
        node = TestNode.objects.get(path=u'002003001')
        self.assertRaises(MissingNodeOrderBy, node.move, node,
                          'sorted-child')
        self.assertRaises(MissingNodeOrderBy, node.move, node,
                          'sorted-sibling')




class TestMoveLeaf(TestNonEmptyTree):

    def setUp(self):
        super(TestMoveLeaf, self).setUp()
        self.node = TestNode.objects.get(path=u'002003001')
        self.target = TestNode.objects.get(path=u'002')


    def test_move_leaf_last_sibling(self):
        self.node.move(self.target, 'last-sibling')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 4),
                    (u'002001', u'21', 2, 0),
                    (u'002002', u'22', 2, 0),
                    (u'002003', u'23', 2, 0),
                    (u'002004', u'24', 2, 0),
                    (u'003', u'3', 1, 0),
                    (u'004', u'4', 1, 1),
                    (u'004001', u'41', 2, 0),
                    (u'005', u'231', 1, 0)]
        self.assertEqual(self.got(), expected)


    def test_move_leaf_first_sibling(self):
        self.node.move(self.target, 'first-sibling')
        expected = [(u'001', u'231', 1, 0),
                    (u'002', u'1', 1, 0),
                    (u'003', u'2', 1, 4),
                    (u'003001', u'21', 2, 0),
                    (u'003002', u'22', 2, 0),
                    (u'003003', u'23', 2, 0),
                    (u'003004', u'24', 2, 0),
                    (u'004', u'3', 1, 0),
                    (u'005', u'4', 1, 1),
                    (u'005001', u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_move_leaf_left_sibling(self):
        self.node.move(self.target, 'left')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'231', 1, 0),
                    (u'003', u'2', 1, 4),
                    (u'003001', u'21', 2, 0),
                    (u'003002', u'22', 2, 0),
                    (u'003003', u'23', 2, 0),
                    (u'003004', u'24', 2, 0),
                    (u'004', u'3', 1, 0),
                    (u'005', u'4', 1, 1),
                    (u'005001', u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_move_leaf_right_sibling(self):
        self.node.move(self.target, 'right')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 4),
                    (u'002001', u'21', 2, 0),
                    (u'002002', u'22', 2, 0),
                    (u'002003', u'23', 2, 0),
                    (u'002004', u'24', 2, 0),
                    (u'003', u'231', 1, 0),
                    (u'004', u'3', 1, 0),
                    (u'005', u'4', 1, 1),
                    (u'005001', u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_move_leaf_left_sibling_itself(self):
        self.node.move(self.node, 'left')
        self.assertEqual(self.got(), self.unchanged)


    def test_move_leaf_last_child(self):
        self.node.move(self.target, 'last-child')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 5),
                    (u'002001', u'21', 2, 0),
                    (u'002002', u'22', 2, 0),
                    (u'002003', u'23', 2, 0),
                    (u'002004', u'24', 2, 0),
                    (u'002005', u'231', 2, 0),
                    (u'003', u'3', 1, 0),
                    (u'004', u'4', 1, 1),
                    (u'004001', u'41', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_move_leaf_first_child(self):
        self.node.move(self.target, 'first-child')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 5),
                    (u'002001', u'231', 2, 0),
                    (u'002002', u'21', 2, 0),
                    (u'002003', u'22', 2, 0),
                    (u'002004', u'23', 2, 0),
                    (u'002005', u'24', 2, 0),
                    (u'003', u'3', 1, 0),
                    (u'004', u'4', 1, 1),
                    (u'004001', u'41', 2, 0)] 
        self.assertEqual(self.got(), expected)



class TestMoveBranch(TestNonEmptyTree):

    def setUp(self):
        super(TestMoveBranch, self).setUp()
        self.node = TestNode.objects.get(path='004')
        self.target = TestNode.objects.get(path='002003')


    def test_move_branch_first_sibling(self):
        self.node.move(self.target, 'first-sibling')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 5),
                    (u'002001', u'4', 2, 1),
                    (u'002001001', u'41', 3, 0),
                    (u'002002', u'21', 2, 0),
                    (u'002003', u'22', 2, 0),
                    (u'002004', u'23', 2, 1),
                    (u'002004001', u'231', 3, 0),
                    (u'002005', u'24', 2, 0),
                    (u'003', u'3', 1, 0)]
        self.assertEqual(self.got(), expected)


    def test_move_branch_last_sibling(self):
        self.node.move(self.target, 'last-sibling')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 5),
                    (u'002001', u'21', 2, 0),
                    (u'002002', u'22', 2, 0),
                    (u'002003', u'23', 2, 1),
                    (u'002003001', u'231', 3, 0),
                    (u'002004', u'24', 2, 0),
                    (u'002005', u'4', 2, 1),
                    (u'002005001', u'41', 3, 0),
                    (u'003', u'3', 1, 0)]
        self.assertEqual(self.got(), expected)


    def test_move_branch_left_sibling(self):
        self.node.move(self.target, 'left')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 5),
                    (u'002001', u'21', 2, 0),
                    (u'002002', u'22', 2, 0),
                    (u'002003', u'4', 2, 1),
                    (u'002003001', u'41', 3, 0),
                    (u'002004', u'23', 2, 1),
                    (u'002004001', u'231', 3, 0),
                    (u'002005', u'24', 2, 0),
                    (u'003', u'3', 1, 0)]
        self.assertEqual(self.got(), expected)


    def test_move_branch_right_sibling(self):
        self.node.move(self.target, 'right')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 5),
                    (u'002001', u'21', 2, 0),
                    (u'002002', u'22', 2, 0),
                    (u'002003', u'23', 2, 1),
                    (u'002003001', u'231', 3, 0),
                    (u'002004', u'4', 2, 1),
                    (u'002004001', u'41', 3, 0),
                    (u'002005', u'24', 2, 0),
                    (u'003', u'3', 1, 0)]
        self.assertEqual(self.got(), expected)


    def test_move_branch_left_noleft_sibling(self):
        self.node.move(self.target.get_first_sibling(), 'left')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 5),
                    (u'002001', u'4', 2, 1),
                    (u'002001001', u'41', 3, 0),
                    (u'002002', u'21', 2, 0),
                    (u'002003', u'22', 2, 0),
                    (u'002004', u'23', 2, 1),
                    (u'002004001', u'231', 3, 0),
                    (u'002005', u'24', 2, 0),
                    (u'003', u'3', 1, 0)]
        self.assertEqual(self.got(), expected)


    def test_move_branch_right_noright_sibling(self):
        self.node.move(self.target.get_last_sibling(), 'right')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 5),
                    (u'002001', u'21', 2, 0),
                    (u'002002', u'22', 2, 0),
                    (u'002003', u'23', 2, 1),
                    (u'002003001', u'231', 3, 0),
                    (u'002004', u'24', 2, 0),
                    (u'002005', u'4', 2, 1),
                    (u'002005001', u'41', 3, 0),
                    (u'003', u'3', 1, 0)]
        self.assertEqual(self.got(), expected)


    def test_move_branch_left_itself_sibling(self):
        self.node.move(self.node, 'left')
        self.assertEqual(self.got(), self.unchanged)


    def test_move_branch_first_child(self):
        self.node.move(self.target, 'first-child')
        expected = [(u'001', u'1', 1, 0),
                    (u'002', u'2', 1, 4),
                    (u'002001', u'21', 2, 0),
                    (u'002002', u'22', 2, 0),
                    (u'002003', u'23', 2, 2),
                    (u'002003001', u'4', 3, 1),
                    (u'002003001001', u'41', 4, 0),
                    (u'002003002', u'231', 3, 0),
                    (u'002004', u'24', 2, 0),
                    (u'003', u'3', 1, 0)]
        self.assertEqual(self.got(), expected)


    def test_move_branch_last_child(self):
        self.node.move(self.target, 'last-child')
        expected =  [(u'001', u'1', 1, 0),
                     (u'002', u'2', 1, 4),
                     (u'002001', u'21', 2, 0),
                     (u'002002', u'22', 2, 0),
                     (u'002003', u'23', 2, 2),
                     (u'002003001', u'231', 3, 0),
                     (u'002003002', u'4', 3, 1),
                     (u'002003002001', u'41', 4, 0),
                     (u'002004', u'24', 2, 0),
                     (u'003', u'3', 1, 0)]
        self.assertEqual(self.got(), expected)



class TestTreeSorted(TestCase):

    def got(self):
        return [(o.path, o.val1, o.val2, o.desc, o.depth, o.numchild)
                 for o in TestNodeSorted.objects.all()]


    def test_add_root_sorted(self):
        TestNodeSorted.add_root(val1=3, val2=3, desc='zxy')
        TestNodeSorted.add_root(val1=1, val2=4, desc='bcd')
        TestNodeSorted.add_root(val1=2, val2=5, desc='zxy')
        TestNodeSorted.add_root(val1=3, val2=3, desc='abc')
        TestNodeSorted.add_root(val1=4, val2=1, desc='fgh')
        TestNodeSorted.add_root(val1=3, val2=3, desc='abc')
        TestNodeSorted.add_root(val1=2, val2=2, desc='qwe')
        TestNodeSorted.add_root(val1=3, val2=2, desc='vcx')
        expected = [(u'1', 1, 4, u'bcd', 1, 0),
                    (u'2', 2, 2, u'qwe', 1, 0),
                    (u'3', 2, 5, u'zxy', 1, 0),
                    (u'4', 3, 2, u'vcx', 1, 0),
                    (u'5', 3, 3, u'abc', 1, 0),
                    (u'6', 3, 3, u'abc', 1, 0),
                    (u'7', 3, 3, u'zxy', 1, 0),
                    (u'8', 4, 1, u'fgh', 1, 0)]
        self.assertEqual(self.got(), expected)


    def test_add_child_sorted(self):
        root = TestNodeSorted.add_root(val1=0, val2=0, desc='aaa')
        root.add_child(val1=3, val2=3, desc='zxy')
        root.add_child(val1=1, val2=4, desc='bcd')
        root.add_child(val1=2, val2=5, desc='zxy')
        root.add_child(val1=3, val2=3, desc='abc')
        root.add_child(val1=4, val2=1, desc='fgh')
        root.add_child(val1=3, val2=3, desc='abc')
        root.add_child(val1=2, val2=2, desc='qwe')
        root.add_child(val1=3, val2=2, desc='vcx')
        expected = [(u'1', 0, 0, u'aaa', 1, 8),
                    (u'11', 1, 4, u'bcd', 2, 0),
                    (u'12', 2, 2, u'qwe', 2, 0),
                    (u'13', 2, 5, u'zxy', 2, 0),
                    (u'14', 3, 2, u'vcx', 2, 0),
                    (u'15', 3, 3, u'abc', 2, 0),
                    (u'16', 3, 3, u'abc', 2, 0),
                    (u'17', 3, 3, u'zxy', 2, 0),
                    (u'18', 4, 1, u'fgh', 2, 0)]
        self.assertEqual(self.got(), expected)


    def test_move_sorted(self):
        TestNodeSorted.add_root(val1=3, val2=3, desc='zxy')
        TestNodeSorted.add_root(val1=1, val2=4, desc='bcd')
        TestNodeSorted.add_root(val1=2, val2=5, desc='zxy')
        TestNodeSorted.add_root(val1=3, val2=3, desc='abc')
        TestNodeSorted.add_root(val1=4, val2=1, desc='fgh')
        TestNodeSorted.add_root(val1=3, val2=3, desc='abc')
        TestNodeSorted.add_root(val1=2, val2=2, desc='qwe')
        TestNodeSorted.add_root(val1=3, val2=2, desc='vcx')
        root_nodes = TestNodeSorted.get_root_nodes()
        target = root_nodes[0]
        for node in root_nodes[1:]:
            node.move(target, 'sorted-child')
        expected = [(u'1', 1, 4, u'bcd', 1, 7),
                    (u'11', 2, 2, u'qwe', 2, 0),
                    (u'12', 2, 5, u'zxy', 2, 0),
                    (u'13', 3, 2, u'vcx', 2, 0),
                    (u'14', 3, 3, u'abc', 2, 0),
                    (u'15', 3, 3, u'abc', 2, 0),
                    (u'16', 3, 3, u'zxy', 2, 0),
                    (u'17', 4, 1, u'fgh', 2, 0)]
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
            TestNodeAlphabet.objects.all().delete()

            # change the model's alphabet
            TestNodeAlphabet.alphabet = alphabet

            # insert root nodes
            for pos in range(len(alphabet)*2):
                try:
                    TestNodeAlphabet.add_root(numval=pos)
                except:
                    got_err = True
                    break
            if not got_err:
                got = [obj.path for obj in TestNodeAlphabet.objects.all()]
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
        method = TestNodeSmallStep.add_root
        for i in range(1, 10):
            method()
        self.assertRaises(PathOverflow, method)

    def test_add_child(self):
        root = TestNodeSmallStep.add_root()
        method = root.add_child
        for i in range(1, 10):
            method()
        self.assertRaises(PathOverflow, method)

    def test_add_sibling(self):
        root = TestNodeSmallStep.add_root()
        for i in range(1, 10):
            root.add_child()
        method = root.get_last_child().add_sibling
        positions = ('first-sibling', 'left', 'right', 'last-sibling')
        for pos in positions:
            self.assertRaises(PathOverflow, method, pos)

    def test_move(self):
        root = TestNodeSmallStep.add_root()
        for i in range(1, 10):
            root.add_child()
        newroot = TestNodeSmallStep.add_root()
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
            TestNodeSortedAutoNow.add_root(desc='node%d' % (i,),
                                           created=datetime.datetime.now())

    def test_sorted_by_autonow_FAIL(self):
        """
        This test asserts that we have a problem.
        fix this, somehow
        """
        TestNodeSortedAutoNow.add_root(desc='node1')
        self.assertRaises(ValueError, TestNodeSortedAutoNow.add_root, desc='node2')



class TestTreeShortPath(TestCase):
    """
    Here we test a tree with a very small path field (max_length=4) and a
    steplen of 1
    """
    def test_short_path(self):
        obj = TestNodeShortPath.add_root().add_child().add_child().add_child()
        self.assertRaises(PathOverflow, obj.add_child)



class TestFindProblems(TestTreeBase):
    def setUp(self):
        model = TestNodeAlphabet
        model.alphabet = '012'
        model(path='01', depth=1, numchild=0, numval=0).save()
        model(path='1', depth=1, numchild=0, numval=0).save()
        model(path='111', depth=1, numchild=0, numval=0).save()
        model(path='abcd', depth=1, numchild=0, numval=0).save()
        model(path='qa#$%!', depth=1, numchild=0, numval=0).save()
        model(path='0201', depth=2, numchild=0, numval=0).save()
        model(path='020201', depth=3, numchild=0, numval=0).save()

    def test_find_problems(self):
        model = TestNodeAlphabet
        evil_chars, bad_steplen, orphans = model.find_problems()
        self.assertEqual(['abcd', 'qa#$%!'],
            [o.path for o in model.objects.filter(id__in=evil_chars)])
        self.assertEqual(['1', '111'],
            [o.path for o in model.objects.filter(id__in=bad_steplen)])
        self.assertEqual(['0201', '020201'],
            [o.path for o in model.objects.filter(id__in=orphans)])



class TestFixTree(TestTreeBase):

    def setUp(self):
        super(TestFixTree, self).setUp()
        for model in (TestNodeShortPath, TestSortedNodeShortPath):
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
    
    
    def got(self, model):
        return [(o.path, o.desc, o.depth, o.numchild) for o in model.objects.all()]


    def test_fix_tree(self):
        # (o.path, o.desc, o.depth, o.numchild)
        expected_unsorted = [
           ('1', 'b', 1, 2),
           ('11', 'u', 2, 1),
           ('111', 'i', 3, 1),
           ('1111', 'e', 4, 0),
           ('12', 'o', 2, 0),
           ('2', 'd', 1, 0),
           ('3', 'g', 1, 0),
           ('4', 'a', 1, 4),
           ('41', 'a', 2, 0),
           ('42', 'a', 2, 0),
           ('43', 'u', 2, 1),
           ('431', 'i', 3, 1),
           ('4311', 'e', 4, 0),
           ('44', 'o', 2, 0),
           ]
        expected_sorted = [
            ('1', 'a', 1, 4),
            ('11', 'a', 2, 0),
            ('12', 'a', 2, 0),
            ('13', 'o', 2, 0),
            ('14', 'u', 2, 1),
            ('141', 'i', 3, 1),
            ('1411', 'e', 4, 0),
            ('2', 'b', 1, 2),
            ('21', 'o', 2, 0),
            ('22', 'u', 2, 1),
            ('221', 'i', 3, 1),
            ('2211', 'e', 4, 0),
            ('3', 'd', 1, 0),
            ('4', 'g', 1, 0),
            ]

        TestNodeShortPath.fix_tree()
        self.assertEqual(self.got(TestNodeShortPath), expected_unsorted)
        
        TestSortedNodeShortPath.fix_tree()
        self.assertEqual(self.got(TestSortedNodeShortPath), expected_sorted)


class TestHelpers(TestTreeBase):

    def setUp(self):
        TestNode.load_bulk(BASE_DATA)
        for node in TestNode.get_root_nodes():
            TestNode.load_bulk(BASE_DATA, node)
        TestNode.add_root(desc='5')

    def test_descendants_group_count_root(self):
        got = [(o.path, count)
               for o, count in TestNode.get_descendants_group_count()]
        expected = [('001', 10),
                    ('002', 15),
                    ('003', 10),
                    ('004', 11),
                    ('005', 0)]
        self.assertEqual(got, expected)


    def test_descendants_group_count_node(self):
        parent = TestNode.objects.get(path='002')
        got = [(o.path, count)
               for o, count in TestNode.get_descendants_group_count(parent)]
        expected = [('002001', 0),
                    ('002002', 0),
                    ('002003', 1),
                    ('002004', 0),
                    ('002005', 0),
                    ('002006', 5),
                    ('002007', 0),
                    ('002008', 1)]
        self.assertEqual(got, expected)


#~
