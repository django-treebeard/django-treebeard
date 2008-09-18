from django.test import TestCase
from django.db import models
from treebeard import Tree, Node, InvalidPosition, InvalidMoveToDescendant, \
    WrongTreeParm, NeedOneNodeRelationPerTree

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


class TestTree(Tree):
    desc = models.CharField(max_length=255)
    foo = models.IntegerField()


class TestNode(Node):
    steplen = 3

    desc = models.CharField(max_length=255)
    tree = models.ForeignKey(TestTree,
                             related_name='treebeard_nodes')


class TestTreeErrorNoRelNodes(Tree):
    pass


class TestTreeSorted(Tree):
    pass


class TestNodeSorted(Node):
    steplen = 1
    node_order_by = ['val1', 'val2', 'desc']
    val1 = models.IntegerField()
    val2 = models.IntegerField()
    desc = models.CharField(max_length=255)
    tree = models.ForeignKey(TestTreeSorted,
                             related_name='treebeard_nodes')



class TestTreeCreation(TestCase):

    def test_tree(self):
        self.tree = TestTree(desc='test tree', foo=5)
        self.tree.save()

        tree = TestTree.objects.get(id=self.tree.id)

        self.assertTrue(tree != None)
        self.assertEqual(tree.desc, 'test tree')
        self.assertEqual(tree.foo, 5)


    def test_tree_err_no_rel_nodes(self):
        self.assertRaises(NeedOneNodeRelationPerTree, TestTreeErrorNoRelNodes)




class TestTreeBase(TestCase):

    def setUp(self):
        self.tree = TestTree.objects.create(desc='test tree', foo=5)
        self.tree2 = TestTree.objects.create(desc='test tree 2', foo=4)
        self.treenodes = self.tree.treebeard_nodes
        self.tree2nodes = self.tree2.treebeard_nodes
        self.unchanged = [(u'001', u'1', 1),
                          (u'002', u'2', 1),
                          (u'002001', u'21', 2),
                          (u'002002', u'22', 2),
                          (u'002003', u'23', 2),
                          (u'002003001', u'231', 3),
                          (u'002004', u'24', 2),
                          (u'003', u'3', 1),
                          (u'004', u'4', 1),
                          (u'004001', u'41', 2)]


    def got(self, tree=1):
        if tree == 2:
            node_set = self.tree2nodes
        elif tree == 1:
            node_set = self.treenodes
        return [(o.path, o.desc, o.depth) for o in node_set.all()]



class TestEmptyTree(TestTreeBase):

    def test_tree(self):
        self.assertTrue(self.tree != None)
        self.assertTrue(self.tree2 != None)
        self.assertNotEqual(self.tree, self.tree2)


    def test_keylen(self):
        self.assertEqual(TestNode.steplen, 3)


    def test_tree_empty_on_creation(self):
        self.assertEqual(0, self.treenodes.count())


    def test_load_bulk_empty(self):

        # testing inserting on an empty tree, the 2nd tree should be empty
        paths = self.tree.load_bulk(BASE_DATA)
        #self.assertEqual(paths, ['001', '002', '003', '004'])
        self.assertEqual(paths, [x[0] for x in self.unchanged])
        self.assertEqual(self.got(), self.unchanged)
        self.assertEqual(0, self.tree2nodes.count())


        # testing on an empty 2nd tree, the 1st tree should still be the same
        paths = self.tree2.load_bulk(BASE_DATA)
        #self.assertEqual(paths, ['001', '002', '003', '004'])
        self.assertEqual(paths, [x[0] for x in self.unchanged])
        self.assertEqual(self.got(2), self.unchanged)
        self.assertEqual(self.got(), self.unchanged)


    def test_add_root_empty(self):
        obj = self.tree.add_root(desc='1')
        expected = [(u'001', u'1', 1)]
        self.assertEqual(self.got(), expected)


    def test_get_root_nodes_empty(self):
        got = self.tree.get_root_nodes()
        expected = []
        self.assertEqual([node.path for node in got], expected)


    def test_get_first_root_node_empty(self):
        got = self.tree.get_first_root_node()
        self.assertEqual(got, None)


    def test_get_last_root_node_empty(self):
        got = self.tree.get_last_root_node()
        self.assertEqual(got, None)



class TestNonEmptyTree(TestTreeBase):

    def setUp(self):
        super(TestNonEmptyTree, self).setUp()
        self.tree.load_bulk(BASE_DATA)
        self.tree2.load_bulk(BASE_DATA)
        self.leafnode = self.treenodes.get(path=u'002003001')
        self.node_children = self.treenodes.get(path=u'002')


class TestManagerMethods(TestNonEmptyTree):

    def setUp(self):
        super(TestManagerMethods, self).setUp()


    def test_load_bulk_wrong_tree(self):
        method = self.tree.load_bulk
        self.assertRaises(WrongTreeParm, method,
            BASE_DATA, self.tree2nodes.get(path='002003001'))


    def test_load_bulk_existing(self):

        # inserting on an existing node

        newparent = self.treenodes.get(path='002003001')
        ids = self.tree.load_bulk(BASE_DATA, newparent)
        expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'21', 2),
                    (u'002002', u'22', 2),
                    (u'002003', u'23', 2),
                    (u'002003001', u'231', 3),
                    (u'002003001001', u'1', 4),
                    (u'002003001002', u'2', 4),
                    (u'002003001002001', u'21', 5),
                    (u'002003001002002', u'22', 5),
                    (u'002003001002003', u'23', 5),
                    (u'002003001002003001', u'231', 6),
                    (u'002003001002004', u'24', 5),
                    (u'002003001003', u'3', 4),
                    (u'002003001004', u'4', 4),
                    (u'002003001004001', u'41', 5),
                    (u'002004', u'24', 2),
                    (u'003', u'3', 1),
                    (u'004', u'4', 1),
                    (u'004001', u'41', 2)]
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
        self.assertEqual(self.got(2), self.unchanged)


    def test_add_root(self):
        obj = self.tree.add_root(desc='5')
        self.assertEqual(obj.path, u'005')
        self.assertEqual(obj.depth, 1)
        self.assertEqual(self.got(2), self.unchanged)


    def test_get_root_nodes(self):
        got = self.tree.get_root_nodes()
        expected = ['001', '002', '003', '004']
        self.assertEqual([node.path for node in got], expected)


    def test_get_first_root_node_empty(self):
        got = self.tree.get_first_root_node()
        self.assertEqual(got.path, '001')


    def test_get_last_root_node_empty(self):
        got = self.tree.get_last_root_node()
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
            node = self.treenodes.get(path=path).get_root()
            self.assertEqual(node.path, expected)

    
    def test_get_children(self):
        data = [
            ('002', ['002001', '002002', '002003', '002004']),
            ('002003', ['002003001']),
            ('002003001', []),
        ]
        for path, expected in data:
            children = self.treenodes.get(path=path).get_children()
            self.assertEqual([node.path for node in children], expected)


    def test_get_siblings(self):
        data = [
            ('002', ['001', '002', '003', '004']),
            ('002001', ['002001', '002002', '002003', '002004']),
            ('002003001', ['002003001']),
        ]
        for path, expected in data:
            siblings = self.treenodes.get(path=path).get_siblings()
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
            node = self.treenodes.get(path=path).get_first_sibling()
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
            node = self.treenodes.get(path=path).get_prev_sibling()
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
            node = self.treenodes.get(path=path).get_next_sibling()
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
            node = self.treenodes.get(path=path).get_last_sibling()
            self.assertEqual(node.path, expected)


    def test_get_first_child(self):
        data = [
            ('002', '002001'),
            ('002001', None),
            ('002003', '002003001'),
            ('002003001', None),
        ]
        for path, expected in data:
            node = self.treenodes.get(path=path).get_first_child()
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
            node = self.treenodes.get(path=path).get_last_child()
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
            nodes = self.treenodes.get(path=path).get_ancestors()
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
            nodes = self.treenodes.get(path=path).get_descendants()
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
            node1 = self.treenodes.get(path=path1)
            node2 = self.treenodes.get(path=path2)
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
            node1 = self.treenodes.get(path=path1)
            node2 = self.treenodes.get(path=path2)
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
            node1 = self.treenodes.get(path=path1)
            node2 = self.treenodes.get(path=path2)
            self.assertEqual(node1.is_descendant_of(node2), expected)


class TestAddChild(TestNonEmptyTree):

    def test_add_child_to_leaf(self):
        obj = self.treenodes.get(path=u'002003001').add_child(desc='2311')
        expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'21', 2),
                    (u'002002', u'22', 2),
                    (u'002003', u'23', 2),
                    (u'002003001', u'231', 3),
                    (u'002003001001', u'2311', 4),
                    (u'002004', u'24', 2),
                    (u'003', u'3', 1),
                    (u'004', u'4', 1),
                    (u'004001', u'41', 2)]
        self.assertEqual(self.got(), expected)
        self.assertEqual(self.got(2), self.unchanged)


    def test_add_child_to_node(self):
        obj = self.treenodes.get(path=u'002').add_child(desc='25')
        expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'21', 2),
                    (u'002002', u'22', 2),
                    (u'002003', u'23', 2),
                    (u'002003001', u'231', 3),
                    (u'002004', u'24', 2),
                    (u'002005', u'25', 2),
                    (u'003', u'3', 1),
                    (u'004', u'4', 1),
                    (u'004001', u'41', 2)]
        self.assertEqual(self.got(), expected)
        self.assertEqual(self.got(2), self.unchanged)



class TestAddSibling(TestNonEmptyTree):


    def test_add_sibling_invalid_pos(self):
        method =  self.treenodes.get(path=u'002003001').add_sibling
        self.assertRaises(InvalidPosition, method, 'invalid_pos')
    
    
    def test_add_sibling_last(self):
        obj = self.node_children.add_sibling('last', desc='5')
        self.assertEqual(obj.path, u'005')
        self.assertEqual(obj.depth, 1)

        obj = self.leafnode.add_sibling('last', desc='232')
        self.assertEqual(obj.path, u'002003002')
        self.assertEqual(obj.depth, 3)

        self.assertEqual(self.got(2), self.unchanged)


    def test_add_sibling_first(self):
        obj = self.node_children.add_sibling('first', desc='new')
        self.assertEqual(obj.path, u'001')
        expected = [(u'001', u'new', 1),
                    (u'002', u'1', 1),
                    (u'003', u'2', 1),
                    (u'003001', u'21', 2),
                    (u'003002', u'22', 2),
                    (u'003003', u'23', 2),
                    (u'003003001', u'231', 3),
                    (u'003004', u'24', 2),
                    (u'004', u'3', 1),
                    (u'005', u'4', 1),
                    (u'005001', u'41', 2)]
        self.assertEqual(self.got(), expected)

        self.assertEqual(self.got(2), self.unchanged)


    def test_add_sibling_prev(self):
        obj = self.node_children.add_sibling('prev', desc='new')
        self.assertEqual(obj.path, u'002')
        expected = [(u'001', u'1', 1),
                    (u'002', u'new', 1),
                    (u'003', u'2', 1),
                    (u'003001', u'21', 2),
                    (u'003002', u'22', 2),
                    (u'003003', u'23', 2),
                    (u'003003001', u'231', 3),
                    (u'003004', u'24', 2),
                    (u'004', u'3', 1),
                    (u'005', u'4', 1),
                    (u'005001', u'41', 2)]
        self.assertEqual(self.got(), expected)

        self.assertEqual(self.got(2), self.unchanged)


    def test_add_sibling_prev_noprev(self):
        obj = self.leafnode.add_sibling('prev', desc='new')
        self.assertEqual(obj.path, u'002003001')
        expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'21', 2),
                    (u'002002', u'22', 2),
                    (u'002003', u'23', 2),
                    (u'002003001', u'new', 3),
                    (u'002003002', u'231', 3),
                    (u'002004', u'24', 2),
                    (u'003', u'3', 1),
                    (u'004', u'4', 1),
                    (u'004001', u'41', 2)]
        self.assertEqual(self.got(), expected)

        self.assertEqual(self.got(2), self.unchanged)


    def test_add_sibling_next(self):
        obj = self.node_children.add_sibling('next', desc='new')
        self.assertEqual(obj.path, u'003')
        expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'21', 2),
                    (u'002002', u'22', 2),
                    (u'002003', u'23', 2),
                    (u'002003001', u'231', 3),
                    (u'002004', u'24', 2),
                    (u'003', u'new', 1),
                    (u'004', u'3', 1),
                    (u'005', u'4', 1),
                    (u'005001', u'41', 2)]
        self.assertEqual(self.got(), expected)

        self.assertEqual(self.got(2), self.unchanged)


    def test_add_sibling_next_nonext(self):
        obj = self.leafnode.add_sibling('next', desc='new')
        self.assertEqual(obj.path, u'002003002')
        expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'21', 2),
                    (u'002002', u'22', 2),
                    (u'002003', u'23', 2),
                    (u'002003001', u'231', 3),
                    (u'002003002', u'new', 3),
                    (u'002004', u'24', 2),
                    (u'003', u'3', 1),
                    (u'004', u'4', 1),
                    (u'004001', u'41', 2)]
        self.assertEqual(self.got(), expected)

        self.assertEqual(self.got(2), self.unchanged)



class TestDelete(TestNonEmptyTree):

    def test_delete_leaf(self):
        self.treenodes.get(path=u'002003001').delete()
        expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'21', 2),
                    (u'002002', u'22', 2),
                    (u'002003', u'23', 2),
                    (u'002004', u'24', 2),
                    (u'003', u'3', 1),
                    (u'004', u'4', 1),
                    (u'004001', u'41', 2)]
        self.assertEqual(self.got(), expected)
        self.assertEqual(self.got(2), self.unchanged)


    def test_delete_node(self):
        self.treenodes.get(path=u'002003').delete()
        expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'21', 2),
                    (u'002002', u'22', 2),
                    (u'002004', u'24', 2),
                    (u'003', u'3', 1),
                    (u'004', u'4', 1),
                    (u'004001', u'41', 2)]
        self.assertEqual(self.got(), expected)
        self.assertEqual(self.got(2), self.unchanged)


    def test_delete_root(self):
        self.treenodes.get(path=u'002').delete()
        expected = [(u'001', u'1', 1),
                    (u'003', u'3', 1),
                    (u'004', u'4', 1),
                    (u'004001', u'41', 2)]
        self.assertEqual(self.got(), expected)
        self.assertEqual(self.got(2), self.unchanged)


    def test_delete_filter_root_nodes(self):
        self.treenodes.filter(path__in=('002', '003')).delete()
        expected = [(u'001', u'1', 1),
                    (u'004', u'4', 1),
                    (u'004001', u'41', 2)]
        self.assertEqual(self.got(), expected)
        self.assertEqual(self.got(2), self.unchanged)


    def test_delete_filter_children(self):
        self.treenodes.filter(
            path__in=('002', '002003', '002003001')).delete()
        expected = [(u'001', u'1', 1),
                    (u'003', u'3', 1),
                    (u'004', u'4', 1),
                    (u'004001', u'41', 2)]
        self.assertEqual(self.got(), expected)

        self.assertEqual(self.got(2), self.unchanged)


    def test_delete_nonexistant_nodes(self):
        self.treenodes.filter(path__in=('ZZZ', 'XXX')).delete()
        self.assertEqual(self.got(), self.unchanged)
        self.assertEqual(self.got(2), self.unchanged)


    def test_delete_same_node_twice(self):
        self.treenodes.filter(
            path__in=('002', '002')).delete()
        expected = [(u'001', u'1', 1),
                    (u'003', u'3', 1),
                    (u'004', u'4', 1),
                    (u'004001', u'41', 2)]
        self.assertEqual(self.got(), expected)
        self.assertEqual(self.got(2), self.unchanged)


    def test_delete_all_root_nodes(self):
        self.treenodes.filter(depth=1).delete()
        count = self.treenodes.count()
        self.assertEqual(count, 0)
        self.assertEqual(self.got(2), self.unchanged)


    def test_delete_all(self):
        self.treenodes.all().delete()
        count = self.treenodes.count()
        self.assertEqual(count, 0)
        self.assertEqual(self.got(2), self.unchanged)



class TestMoveErrors(TestNonEmptyTree):

    def test_move_invalid_pos(self):
        node = self.treenodes.get(path=u'002003001')
        method = node.move
        self.assertRaises(InvalidPosition, method, node, 'invalid_pos')


    def test_move_to_descendant(self):
        node = self.treenodes.get(path=u'002')
        target = self.treenodes.get(path=u'002003001')
        method = node.move
        self.assertRaises(InvalidMoveToDescendant, method, target, 'first')



class TestMoveLeafSameTree(TestNonEmptyTree):

    def setUp(self):
        super(TestMoveLeafSameTree, self).setUp()
        self.node = self.treenodes.get(path=u'002003001')
        self.target = self.treenodes.get(path=u'002')


    def test_move_leaf_last(self):
        self.node.move(self.target, 'last')
        expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'21', 2),
                    (u'002002', u'22', 2),
                    (u'002003', u'23', 2),
                    (u'002004', u'24', 2),
                    (u'003', u'3', 1),
                    (u'004', u'4', 1),
                    (u'004001', u'41', 2),
                    (u'005', u'231', 1)]
        self.assertEqual(self.got(), expected)
        self.assertEqual(self.got(2), self.unchanged)


    def test_move_leaf_first(self):
        self.node.move(self.target, 'first')
        expected = [(u'001', u'231', 1),
                    (u'002', u'1', 1),
                    (u'003', u'2', 1),
                    (u'003001', u'21', 2),
                    (u'003002', u'22', 2),
                    (u'003003', u'23', 2),
                    (u'003004', u'24', 2),
                    (u'004', u'3', 1),
                    (u'005', u'4', 1),
                    (u'005001', u'41', 2)]
        self.assertEqual(self.got(), expected)
        self.assertEqual(self.got(2), self.unchanged)


    def test_move_leaf_prev(self):
        self.node.move(self.target, 'prev')
        expected = [(u'001', u'1', 1),
                    (u'002', u'231', 1),
                    (u'003', u'2', 1),
                    (u'003001', u'21', 2),
                    (u'003002', u'22', 2),
                    (u'003003', u'23', 2),
                    (u'003004', u'24', 2),
                    (u'004', u'3', 1),
                    (u'005', u'4', 1),
                    (u'005001', u'41', 2)]
        self.assertEqual(self.got(), expected)
        self.assertEqual(self.got(2), self.unchanged)


    def test_move_leaf_next(self):
        self.node.move(self.target, 'next')
        expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'21', 2),
                    (u'002002', u'22', 2),
                    (u'002003', u'23', 2),
                    (u'002004', u'24', 2),
                    (u'003', u'231', 1),
                    (u'004', u'3', 1),
                    (u'005', u'4', 1),
                    (u'005001', u'41', 2)]
        self.assertEqual(self.got(), expected)
        self.assertEqual(self.got(2), self.unchanged)


    def test_move_leaf_prev_itself(self):
        self.node.move(self.node, 'prev')
        self.assertEqual(self.got(), self.unchanged)
        self.assertEqual(self.got(2), self.unchanged)



class TestMoveBranchSameTree(TestNonEmptyTree):

    def setUp(self):
        super(TestMoveBranchSameTree, self).setUp()
        self.node = self.treenodes.get(path='004')
        self.target = self.treenodes.get(path='002003')


    def test_move_branch_first(self):
        self.node.move(self.target, 'first')
        expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'4', 2),
                    (u'002001001', u'41', 3),
                    (u'002002', u'21', 2),
                    (u'002003', u'22', 2),
                    (u'002004', u'23', 2),
                    (u'002004001', u'231', 3),
                    (u'002005', u'24', 2),
                    (u'003', u'3', 1)]
        self.assertEqual(self.got(), expected)
        self.assertEqual(self.got(2), self.unchanged)


    def test_move_branch_last(self):
        self.node.move(self.target, 'last')
        expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'21', 2),
                    (u'002002', u'22', 2),
                    (u'002003', u'23', 2),
                    (u'002003001', u'231', 3),
                    (u'002004', u'24', 2),
                    (u'002005', u'4', 2),
                    (u'002005001', u'41', 3),
                    (u'003', u'3', 1)]
        self.assertEqual(self.got(), expected)
        self.assertEqual(self.got(2), self.unchanged)


    def test_move_branch_prev(self):
        self.node.move(self.target, 'prev')
        expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'21', 2),
                    (u'002002', u'22', 2),
                    (u'002003', u'4', 2),
                    (u'002003001', u'41', 3),
                    (u'002004', u'23', 2),
                    (u'002004001', u'231', 3),
                    (u'002005', u'24', 2),
                    (u'003', u'3', 1)]
        self.assertEqual(self.got(), expected)
        self.assertEqual(self.got(2), self.unchanged)


    def test_move_branch_next(self):
        self.node.move(self.target, 'next')
        expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'21', 2),
                    (u'002002', u'22', 2),
                    (u'002003', u'23', 2),
                    (u'002003001', u'231', 3),
                    (u'002004', u'4', 2),
                    (u'002004001', u'41', 3),
                    (u'002005', u'24', 2),
                    (u'003', u'3', 1)]
        self.assertEqual(self.got(), expected)
        self.assertEqual(self.got(2), self.unchanged)


    def test_move_branch_prev_noprev(self):
        self.node.move(self.target.get_first_sibling(), 'prev')
        expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'4', 2),
                    (u'002001001', u'41', 3),
                    (u'002002', u'21', 2),
                    (u'002003', u'22', 2),
                    (u'002004', u'23', 2),
                    (u'002004001', u'231', 3),
                    (u'002005', u'24', 2),
                    (u'003', u'3', 1)]
        self.assertEqual(self.got(), expected)
        self.assertEqual(self.got(2), self.unchanged)


    def test_move_branch_next_nonext(self):
        self.node.move(self.target.get_last_sibling(), 'next')
        expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'21', 2),
                    (u'002002', u'22', 2),
                    (u'002003', u'23', 2),
                    (u'002003001', u'231', 3),
                    (u'002004', u'24', 2),
                    (u'002005', u'4', 2),
                    (u'002005001', u'41', 3),
                    (u'003', u'3', 1)]
        self.assertEqual(self.got(), expected)
        self.assertEqual(self.got(2), self.unchanged)


    def test_move_branch_prev_itself(self):
        self.node.move(self.node, 'prev')
        self.assertEqual(self.got(), self.unchanged)
        self.assertEqual(self.got(2), self.unchanged)




class TestMoveLeafAnotherTree(TestNonEmptyTree):

    def setUp(self):
        super(TestMoveLeafAnotherTree, self).setUp()
        self.node = self.treenodes.get(path=u'002003001')
        self.target = self.tree2nodes.get(path=u'002')
        self.expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'21', 2),
                    (u'002002', u'22', 2),
                    (u'002003', u'23', 2),
                    (u'002004', u'24', 2),
                    (u'003', u'3', 1),
                    (u'004', u'4', 1),
                    (u'004001', u'41', 2)]


    def test_move_leaf_last_tree2(self):
        self.node.move(self.target, 'last')
        expected2 = [(u'001', u'1', 1),
                     (u'002', u'2', 1),
                     (u'002001', u'21', 2),
                     (u'002002', u'22', 2),
                     (u'002003', u'23', 2),
                     (u'002003001', u'231', 3),
                     (u'002004', u'24', 2),
                     (u'003', u'3', 1),
                     (u'004', u'4', 1),
                     (u'004001', u'41', 2),
                     (u'005', u'231', 1)]
        self.assertEqual(self.got(), self.expected)
        self.assertEqual(self.got(2), expected2)


    def test_move_leaf_first_tree2(self):
        self.node.move(self.target, 'first')
        expected2 = [(u'001', u'231', 1),
                     (u'002', u'1', 1),
                     (u'003', u'2', 1),
                     (u'003001', u'21', 2),
                     (u'003002', u'22', 2),
                     (u'003003', u'23', 2),
                     (u'003003001', u'231', 3),
                     (u'003004', u'24', 2),
                     (u'004', u'3', 1),
                     (u'005', u'4', 1),
                     (u'005001', u'41', 2)]
        self.assertEqual(self.got(), self.expected)
        self.assertEqual(self.got(2), expected2)


    def test_move_leaf_prev_tree2(self):
        self.node.move(self.target, 'prev')
        expected2 = [(u'001', u'1', 1),
                     (u'002', u'231', 1),
                     (u'003', u'2', 1),
                     (u'003001', u'21', 2),
                     (u'003002', u'22', 2),
                     (u'003003', u'23', 2),
                     (u'003003001', u'231', 3),
                     (u'003004', u'24', 2),
                     (u'004', u'3', 1),
                     (u'005', u'4', 1),
                     (u'005001', u'41', 2)]
        self.assertEqual(self.got(), self.expected)
        self.assertEqual(self.got(2), expected2)


    def test_move_leaf_next_tree2(self):
        self.node.move(self.target, 'next')
        expected2 = [(u'001', u'1', 1),
                     (u'002', u'2', 1),
                     (u'002001', u'21', 2),
                     (u'002002', u'22', 2),
                     (u'002003', u'23', 2),
                     (u'002003001', u'231', 3),
                     (u'002004', u'24', 2),
                     (u'003', u'231', 1),
                     (u'004', u'3', 1),
                     (u'005', u'4', 1),
                     (u'005001', u'41', 2)]
        self.assertEqual(self.got(), self.expected)
        self.assertEqual(self.got(2), expected2)



class TestMoveBranchAnotherTree(TestNonEmptyTree):

    def setUp(self):
        super(TestMoveBranchAnotherTree, self).setUp()
        self.node = self.treenodes.get(path='004')
        self.target = self.tree2nodes.get(path='002003')
        self.expected = [(u'001', u'1', 1),
                    (u'002', u'2', 1),
                    (u'002001', u'21', 2),
                    (u'002002', u'22', 2),
                    (u'002003', u'23', 2),
                    (u'002003001', u'231', 3),
                    (u'002004', u'24', 2),
                    (u'003', u'3', 1)]


    def test_move_branch_first_tree2(self):
        self.node.move(self.target, 'first')
        expected2 = [(u'001', u'1', 1),
                     (u'002', u'2', 1),
                     (u'002001', u'4', 2),
                     (u'002001001', u'41', 3),
                     (u'002002', u'21', 2),
                     (u'002003', u'22', 2),
                     (u'002004', u'23', 2),
                     (u'002004001', u'231', 3),
                     (u'002005', u'24', 2),
                     (u'003', u'3', 1),
                     (u'004', u'4', 1),
                     (u'004001', u'41', 2)]
        self.assertEqual(self.got(), self.expected)
        self.assertEqual(self.got(2), expected2)


    def test_move_branch_last_tree2(self):
        self.node.move(self.target, 'last')
        expected2 = [(u'001', u'1', 1),
                     (u'002', u'2', 1),
                     (u'002001', u'21', 2),
                     (u'002002', u'22', 2),
                     (u'002003', u'23', 2),
                     (u'002003001', u'231', 3),
                     (u'002004', u'24', 2),
                     (u'002005', u'4', 2),
                     (u'002005001', u'41', 3),
                     (u'003', u'3', 1),
                     (u'004', u'4', 1),
                     (u'004001', u'41', 2)]
        self.assertEqual(self.got(), self.expected)
        self.assertEqual(self.got(2), expected2)


    def test_move_branch_prev_tree2(self):
        self.node.move(self.target, 'prev')
        expected2 = [(u'001', u'1', 1),
                     (u'002', u'2', 1),
                     (u'002001', u'21', 2),
                     (u'002002', u'22', 2),
                     (u'002003', u'4', 2),
                     (u'002003001', u'41', 3),
                     (u'002004', u'23', 2),
                     (u'002004001', u'231', 3),
                     (u'002005', u'24', 2),
                     (u'003', u'3', 1),
                     (u'004', u'4', 1),
                     (u'004001', u'41', 2)]
        self.assertEqual(self.got(), self.expected)
        self.assertEqual(self.got(2), expected2)


    def test_move_branch_next_tree2(self):
        self.node.move(self.target, 'next')
        expected2 = [(u'001', u'1', 1),
                     (u'002', u'2', 1),
                     (u'002001', u'21', 2),
                     (u'002002', u'22', 2),
                     (u'002003', u'23', 2),
                     (u'002003001', u'231', 3),
                     (u'002004', u'4', 2),
                     (u'002004001', u'41', 3),
                     (u'002005', u'24', 2),
                     (u'003', u'3', 1),
                     (u'004', u'4', 1),
                     (u'004001', u'41', 2)]
        self.assertEqual(self.got(), self.expected)
        self.assertEqual(self.got(2), expected2)


    def test_move_branch_prev_noprev_tree2(self):
        self.node.move(self.target.get_first_sibling(), 'prev')
        expected2 = [(u'001', u'1', 1),
                     (u'002', u'2', 1),
                     (u'002001', u'4', 2),
                     (u'002001001', u'41', 3),
                     (u'002002', u'21', 2),
                     (u'002003', u'22', 2),
                     (u'002004', u'23', 2),
                     (u'002004001', u'231', 3),
                     (u'002005', u'24', 2),
                     (u'003', u'3', 1),
                     (u'004', u'4', 1),
                     (u'004001', u'41', 2)]
        self.assertEqual(self.got(), self.expected)
        self.assertEqual(self.got(2), expected2)


    def test_move_branch_next_nonext_tree2(self):
        self.node.move(self.target.get_last_sibling(), 'next')
        expected2 = [(u'001', u'1', 1),
                     (u'002', u'2', 1),
                     (u'002001', u'21', 2),
                     (u'002002', u'22', 2),
                     (u'002003', u'23', 2),
                     (u'002003001', u'231', 3),
                     (u'002004', u'24', 2),
                     (u'002005', u'4', 2),
                     (u'002005001', u'41', 3),
                     (u'003', u'3', 1),
                     (u'004', u'4', 1),
                     (u'004001', u'41', 2)]
        self.assertEqual(self.got(), self.expected)
        self.assertEqual(self.got(2), expected2)


class TestTreeSortedSuite(TestCase):
    def setUp(self):
        self.tree = TestTreeSorted.objects.create()


    def got(self):
        return [(o.path, o.val1, o.val2, o.desc, o.depth)
                 for o in self.tree.treebeard_nodes.all()]


    def test_add_root_sorted(self):
        self.tree.add_root(val1=3, val2=3, desc='zxy')
        self.tree.add_root(val1=1, val2=4, desc='bcd')
        self.tree.add_root(val1=2, val2=5, desc='zxy')
        self.tree.add_root(val1=3, val2=3, desc='abc')
        self.tree.add_root(val1=4, val2=1, desc='fgh')
        self.tree.add_root(val1=3, val2=3, desc='abc')
        self.tree.add_root(val1=2, val2=2, desc='qwe')
        self.tree.add_root(val1=3, val2=2, desc='vcx')
        expected = [(u'1', 1, 4, u'bcd', 1),
                    (u'2', 2, 2, u'qwe', 1),
                    (u'3', 2, 5, u'zxy', 1),
                    (u'4', 3, 2, u'vcx', 1),
                    (u'5', 3, 3, u'abc', 1),
                    (u'6', 3, 3, u'abc', 1),
                    (u'7', 3, 3, u'zxy', 1),
                    (u'8', 4, 1, u'fgh', 1)]
        self.assertEqual(self.got(), expected)


    def test_add_child_sorted(self):
        root = self.tree.add_root(val1=0, val2=0, desc='aaa')
        root.add_child(val1=3, val2=3, desc='zxy')
        root.add_child(val1=1, val2=4, desc='bcd')
        root.add_child(val1=2, val2=5, desc='zxy')
        root.add_child(val1=3, val2=3, desc='abc')
        root.add_child(val1=4, val2=1, desc='fgh')
        root.add_child(val1=3, val2=3, desc='abc')
        root.add_child(val1=2, val2=2, desc='qwe')
        root.add_child(val1=3, val2=2, desc='vcx')
        expected = [(u'1', 0, 0, u'aaa', 1),
                    (u'11', 1, 4, u'bcd', 2),
                    (u'12', 2, 2, u'qwe', 2),
                    (u'13', 2, 5, u'zxy', 2),
                    (u'14', 3, 2, u'vcx', 2),
                    (u'15', 3, 3, u'abc', 2),
                    (u'16', 3, 3, u'abc', 2),
                    (u'17', 3, 3, u'zxy', 2),
                    (u'18', 4, 1, u'fgh', 2)]
        self.assertEqual(self.got(), expected)



#~
