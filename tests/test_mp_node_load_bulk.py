"""
Unit tests for mp_node_load_bulk function.

This test file mirrors the existing load_bulk tests from test_treebeard.py
to ensure the new mp_node_load_bulk implementation maintains backward compatibility.
"""

import pytest

from tests import models
from treebeard.new import mp_node_load_bulk


BASE_DATA = [
    {"data": {"desc": "1"}},
    {
        "data": {"desc": "2"},
        "children": [
            {"data": {"desc": "21"}},
            {"data": {"desc": "22"}},
            {
                "data": {"desc": "23"},
                "children": [
                    {"data": {"desc": "231"}},
                ],
            },
            {"data": {"desc": "24"}},
        ],
    },
    {"data": {"desc": "3"}},
    {
        "data": {"desc": "4"},
        "children": [
            {"data": {"desc": "41"}},
        ],
    },
]
UNCHANGED = [
    ("1", 1, 0),
    ("2", 1, 4),
    ("21", 2, 0),
    ("22", 2, 0),
    ("23", 2, 1),
    ("231", 3, 0),
    ("24", 2, 0),
    ("3", 1, 0),
    ("4", 1, 1),
    ("41", 2, 0),
]


@pytest.fixture(scope="function")
def mp_model_without_data():
    """Fixture that returns an empty MP_TestNode model."""
    models.MP_TestNode.objects.all().delete()
    return models.MP_TestNode


@pytest.fixture(scope="function")
def mp_model():
    """Fixture that returns MP_TestNode with BASE_DATA already loaded."""
    models.MP_TestNode.objects.all().delete()
    mp_node_load_bulk(models.MP_TestNode, BASE_DATA)
    return models.MP_TestNode


@pytest.fixture(scope="function")
def mp_related_model():
    """Fixture that returns MP_TestNodeRelated model with BASE_DATA loaded."""
    models.MP_TestNodeRelated.objects.all().delete()
    mp_node_load_bulk(models.MP_TestNode, BASE_DATA)
    return models.MP_TestNodeRelated


class TestMPNodeLoadBulk:
    """Test class for mp_node_load_bulk function."""

    def got(self, model):
        """
        Helper method to get tree structure as list of tuples.
        Returns: [(desc, depth, children_count), ...] for entire tree.
        """
        return [(o.desc, o.get_depth(), o.get_children_count()) for o in model.get_tree()]

    @pytest.mark.django_db
    def test_load_bulk_empty(self, mp_model_without_data):
        """
        Test loading bulk data into an empty tree.

        Verifies:
        - Returns list of created node IDs
        - All nodes are created correctly
        - Tree structure matches UNCHANGED constant
        """
        model = mp_model_without_data
        ids = mp_node_load_bulk(model, BASE_DATA)

        # Verify all nodes were created
        got_descs = [obj.desc for obj in model.objects.filter(pk__in=ids)]
        expected_descs = [x[0] for x in UNCHANGED]
        assert sorted(got_descs) == sorted(expected_descs)

        # Verify tree structure
        assert self.got(model) == UNCHANGED

    @pytest.mark.django_db
    def test_load_bulk_existing(self, mp_model):
        """
        Test loading bulk data as children of an existing node.

        Verifies:
        - New nodes become children of specified parent
        - Depths are calculated correctly relative to parent
        - Returns list of newly created node IDs
        - Tree structure maintains proper relationships
        """
        model = mp_model

        # Load BASE_DATA as children of node "231"
        node = model.objects.get(desc="231")
        ids = mp_node_load_bulk(model, BASE_DATA, node)

        # Expected structure: original tree + BASE_DATA under node "231" (depth 3)
        # Node "231" now has 4 children instead of 0
        expected = [
            ("1", 1, 0),
            ("2", 1, 4),
            ("21", 2, 0),
            ("22", 2, 0),
            ("23", 2, 1),
            ("231", 3, 4),      # Now has 4 children (was 0)
            ("1", 4, 0),        # New nodes start at depth 4
            ("2", 4, 4),
            ("21", 5, 0),
            ("22", 5, 0),
            ("23", 5, 1),
            ("231", 6, 0),
            ("24", 5, 0),
            ("3", 4, 0),
            ("4", 4, 1),
            ("41", 5, 0),
            ("24", 2, 0),
            ("3", 1, 0),
            ("4", 1, 1),
            ("41", 2, 0),
        ]

        # Verify returned IDs match newly created nodes
        expected_descs = ["1", "2", "21", "22", "23", "231", "24", "3", "4", "41"]
        got_descs = [obj.desc for obj in model.objects.filter(pk__in=ids)]
        assert sorted(got_descs) == sorted(expected_descs)

        # Verify tree structure
        assert self.got(model) == expected

    @pytest.mark.django_db
    def test_load_and_dump_bulk_keeping_ids(self, mp_model):
        """
        Test round-trip: dump → delete → load(keep_ids=True) → dump.

        Verifies:
        - keep_ids=True preserves primary keys
        - Tree structure remains unchanged after round-trip
        - dump_bulk and load_bulk are inverse operations
        """
        model = mp_model

        # Dump the tree with IDs
        exp = model.dump_bulk(keep_ids=True)

        # Delete all nodes
        model.objects.all().delete()

        # Reload with same IDs
        mp_node_load_bulk(model, exp, None, True)

        # Dump again
        got = model.dump_bulk(keep_ids=True)

        # Should be identical
        assert got == exp

        # Verify tree structure is unchanged
        got_tree = [(o.desc, o.get_depth(), o.get_children_count()) for o in model.get_tree()]
        assert got_tree == UNCHANGED

    @pytest.mark.django_db
    def test_load_and_dump_bulk_with_fk(self, mp_related_model):
        """
        Test loading bulk data containing ForeignKey references.

        Verifies:
        - Foreign key fields are properly processed during load
        - ForeignKey references work correctly (passed as PKs)
        - Round-trip works with ForeignKey data intact
        - Tests _process_foreign_keys() method functionality
        """
        related_model = mp_related_model
        related_model.objects.all().delete()

        # Create or get a related object
        related, created = models.RelatedModel.objects.get_or_create(
            desc="Test %s" % related_model.__name__
        )

        # Data structure with foreign key references (as PKs)
        related_data = [
            {"data": {"desc": "1", "related": related.pk}},
            {
                "data": {"desc": "2", "related": related.pk},
                "children": [
                    {"data": {"desc": "21", "related": related.pk}},
                    {"data": {"desc": "22", "related": related.pk}},
                    {
                        "data": {"desc": "23", "related": related.pk},
                        "children": [
                            {"data": {"desc": "231", "related": related.pk}},
                        ],
                    },
                    {"data": {"desc": "24", "related": related.pk}},
                ],
            },
            {"data": {"desc": "3", "related": related.pk}},
            {
                "data": {"desc": "4", "related": related.pk},
                "children": [
                    {"data": {"desc": "41", "related": related.pk}},
                ],
            },
        ]

        # Load data with foreign keys
        mp_node_load_bulk(related_model, related_data)

        # Dump and verify
        got = related_model.dump_bulk(keep_ids=False)
        assert got == related_data

    @pytest.mark.django_db
    def test_load_bulk_returns_all_node_ids(self, mp_model_without_data):
        """
        Test that load_bulk returns IDs for all created nodes (including descendants).

        Verifies:
        - All node IDs are returned
        - Return value is a list
        - All returned IDs exist in database
        """
        model = mp_model_without_data
        ids = mp_node_load_bulk(model, BASE_DATA)

        # Should return 10 IDs (total nodes in BASE_DATA)
        assert len(ids) == 10

        # All IDs should be valid
        assert model.objects.filter(pk__in=ids).count() == 10

    @pytest.mark.django_db
    def test_load_bulk_empty_list(self, mp_model_without_data):
        """
        Test loading an empty list.

        Verifies:
        - Returns empty list
        - No nodes are created
        """
        model = mp_model_without_data
        ids = mp_node_load_bulk(model, [])

        assert ids == []
        assert model.objects.count() == 0

    @pytest.mark.django_db
    def test_load_bulk_single_root(self, mp_model_without_data):
        """
        Test loading a single root node without children.

        Verifies:
        - Single node is created correctly
        - Depth is 1
        - numchild is 0
        """
        model = mp_model_without_data
        single_node_data = [{"data": {"desc": "single_root"}}]

        ids = mp_node_load_bulk(model, single_node_data)

        assert len(ids) == 1
        node = model.objects.get(pk=ids[0])
        assert node.desc == "single_root"
        assert node.get_depth() == 1
        assert node.get_children_count() == 0

    @pytest.mark.django_db
    def test_load_bulk_multiple_roots(self, mp_model_without_data):
        """
        Test loading multiple root nodes at once.

        Verifies:
        - All root nodes are created
        - All are at depth 1
        - Sibling relationships are correct
        """
        model = mp_model_without_data
        multi_root_data = [
            {"data": {"desc": "root1"}},
            {"data": {"desc": "root2"}},
            {"data": {"desc": "root3"}},
        ]

        ids = mp_node_load_bulk(model, multi_root_data)

        assert len(ids) == 3
        assert model.objects.count() == 3

        # All should be root nodes
        for node in model.objects.all():
            assert node.get_depth() == 1
            assert node.get_children_count() == 0

    @pytest.mark.django_db
    def test_load_bulk_deep_nesting(self, mp_model_without_data):
        """
        Test loading deeply nested tree structure.

        Verifies:
        - Deep nesting is handled correctly
        - Depths are calculated correctly
        - Parent-child relationships are maintained
        """
        model = mp_model_without_data
        deep_data = [
            {
                "data": {"desc": "level1"},
                "children": [
                    {
                        "data": {"desc": "level2"},
                        "children": [
                            {
                                "data": {"desc": "level3"},
                                "children": [
                                    {"data": {"desc": "level4"}},
                                ],
                            },
                        ],
                    },
                ],
            },
        ]

        ids = mp_node_load_bulk(model, deep_data)

        assert len(ids) == 4

        # Verify depths
        node1 = model.objects.get(desc="level1")
        node2 = model.objects.get(desc="level2")
        node3 = model.objects.get(desc="level3")
        node4 = model.objects.get(desc="level4")

        assert node1.get_depth() == 1
        assert node2.get_depth() == 2
        assert node3.get_depth() == 3
        assert node4.get_depth() == 4

        # Verify parent-child relationships
        assert node2.get_parent().pk == node1.pk
        assert node3.get_parent().pk == node2.pk
        assert node4.get_parent().pk == node3.pk

    @pytest.mark.django_db
    def test_load_bulk_maintains_numchild(self, mp_model_without_data):
        """
        Test that numchild field is correctly set for all nodes.

        Verifies:
        - Leaf nodes have numchild=0
        - Parent nodes have correct numchild count
        """
        model = mp_model_without_data
        mp_node_load_bulk(model, BASE_DATA)

        # Check specific nodes
        node1 = model.objects.get(desc="1")
        assert node1.numchild == 0  # Leaf node

        node2 = model.objects.get(desc="2")
        assert node2.numchild == 4  # Has 4 children: 21, 22, 23, 24

        node23 = model.objects.get(desc="23")
        assert node23.numchild == 1  # Has 1 child: 231

        node231 = model.objects.get(desc="231")
        assert node231.numchild == 0  # Leaf node

    @pytest.mark.django_db
    def test_load_bulk_atomicity(self, mp_model_without_data):
        """
        Test that load_bulk is atomic (all-or-nothing).

        Note: This test verifies the @transaction.atomic decorator works.
        If any node creation fails, the entire operation should rollback.
        """
        model = mp_model_without_data

        # Normal case - should succeed
        ids = mp_node_load_bulk(model, BASE_DATA)
        assert len(ids) == 10
        assert model.objects.count() == 10


# Additional test for comparison with old implementation
@pytest.mark.django_db
class TestBackwardCompatibility:
    """Test backward compatibility between old and new implementations."""

    def got(self, model):
        """Helper method to get tree structure."""
        return [(o.desc, o.get_depth(), o.get_children_count()) for o in model.get_tree()]

    def test_new_vs_old_load_bulk_empty_tree(self):
        """
        Compare new mp_node_load_bulk with old model.load_bulk on empty tree.

        Both should produce identical results.
        """
        # Clean slate
        models.MP_TestNode.objects.all().delete()

        # Load with new implementation
        mp_node_load_bulk(models.MP_TestNode, BASE_DATA)
        new_result = self.got(models.MP_TestNode)

        # Clean and load with old implementation
        models.MP_TestNode.objects.all().delete()
        models.MP_TestNode.load_bulk(BASE_DATA)
        old_result = self.got(models.MP_TestNode)

        # Should be identical
        assert new_result == old_result
        assert new_result == UNCHANGED

    def test_new_vs_old_load_bulk_with_parent(self):
        """
        Compare new mp_node_load_bulk with old model.load_bulk when loading under a parent.

        Both should produce identical results.
        """
        # Set up initial tree with old implementation
        models.MP_TestNode.objects.all().delete()
        models.MP_TestNode.load_bulk(BASE_DATA)

        # Get parent node
        node = models.MP_TestNode.objects.get(desc="231")

        # Load children with new implementation
        mp_node_load_bulk(models.MP_TestNode, BASE_DATA, node)
        new_result = self.got(models.MP_TestNode)

        # Reset and do the same with old implementation
        models.MP_TestNode.objects.all().delete()
        models.MP_TestNode.load_bulk(BASE_DATA)
        node = models.MP_TestNode.objects.get(desc="231")
        models.MP_TestNode.load_bulk(BASE_DATA, node)
        old_result = self.got(models.MP_TestNode)

        # Should be identical
        assert new_result == old_result
