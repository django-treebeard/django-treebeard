# -*- coding: utf-8 -*-
"""

    treebeard.tests
    ---------------

    Unit tests.

    :copyright: 2008 by Gustavo Picon
    :license: Apache License 2.0

"""

from django.test import TestCase
from django.db import models
from treebeard import MPNode, InvalidPosition, InvalidMoveToDescendant

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


class TestNodeSorted(MPNode):
    steplen = 1
    node_order_by = ['val1', 'val2', 'desc']
    val1 = models.IntegerField()
    val2 = models.IntegerField()
    desc = models.CharField(max_length=255)



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

        newparent = TestNode.objects.get(path='002003001')
        ids = TestNode.load_bulk(BASE_DATA, newparent)
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


    def test_delete_all(self):
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



class TestTreeSortedSuite(TestCase):

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




#~
