from __future__ import annotations

from typing import TYPE_CHECKING, Any, NotRequired, TypedDict

from django.db import models, transaction

if TYPE_CHECKING:
    from treebeard.mp_tree import MP_Node


class BulkNodeData(TypedDict):
    """Structure for bulk loading tree nodes."""

    data: dict[str, Any]
    children: NotRequired[list[BulkNodeData]]


@transaction.atomic
def mp_node_load_bulk(
    cls: type[MP_Node],
    bulk_data: list[BulkNodeData],
    parent: MP_Node | None = None,
    keep_ids: bool = False,
) -> list[Any]:
    """
    Loads a list/dictionary structure to the tree.

    :param bulk_data:

        The data that will be loaded, the structure is a list of
        dictionaries with 2 keys:

        - ``data``: will store arguments that will be passed for object
            creation, and

        - ``children``: a list of dictionaries, each one has it's own
            ``data`` and ``children`` keys (a recursive structure)


    :param parent:

        The node that will receive the structure as children, if not
        specified the first level of the structure will be loaded as root
        nodes


    :param keep_ids:

        If enabled, loads the nodes with the same primary keys that are
        given in the structure. Will error if there are nodes without
        primary key info or if the primary keys are already used.


    :returns: A list of the added node ids.

    Notes:
        - Concurrency issues: first row may include siblings,
            so we lock the parent node if given.
            How do we handle root nodes concurrency?

    # tree, iterative preorder
    # * Old implementation:
    added = []
    # stack of nodes to analyze
    stack = [(parent, node) for node in bulk_data[::-1]]
    foreign_keys = cls.get_foreign_keys()
    pk_field = cls._meta.pk.attname

    while stack:
        parent, node_struct = stack.pop()
        # shallow copy of the data structure so it doesn't persist...
        node_data = node_struct["data"].copy()
        # For each fk field, replace pk value with actual object
        cls._process_foreign_keys(foreign_keys, node_data)
        if keep_ids:
            # Will raise KeyError if pk_field is missing
            # If pk_field exists, this effectively does nothing
            node_data[pk_field] = node_struct[pk_field]
        if parent:
            node_obj = parent.add_child(**node_data)
        else:
            node_obj = cls.add_root(**node_data)
        added.append(node_obj.pk)
        if "children" in node_struct:
            # extending the stack with the current node as the parent of
            # the new nodes
            stack.extend([(node_obj, node) for node in node_struct["children"][::-1]])
    return added

    # * My shitty implementation for WEBOM:
    def _load_tree(
        self, tree_data: WebeardTreeNode[MP_NodeType], parent: MP_NodeType | None
    ) -> None:
        root, children = tree_data["data"], tree_data["children"]
        root.numchild = len(children)

        # Create the root node using treebeard's methods
        if parent is None:
            subtree_root_node: MP_NodeType = self.cls.add_root(instance=root)  # type: ignore[attr-defined]
        else:
            subtree_root_node: MP_NodeType = parent.add_child(instance=root)  # type: ignore[attr-defined]

        self.added_nodes.append(subtree_root_node.pk)

        # At this point, subtree_root_node is saved with valid path, depth, numchild.
        # We can now bulk create all descendants.

        children_to_create: list[MP_NodeType] = []

        def _collect_children(
            parent_node: MP_NodeType, child_nodes: list[WebeardTreeNode[MP_NodeType]]
        ) -> None:
            base_path = parent_node.path
            child_depth = parent_node.depth + 1

            for i, child in enumerate(child_nodes):
                child_node, grandchildren = child["data"], child["children"]

                # Manually set treebeard fields
                child_node.depth = child_depth
                child_node.numchild = len(grandchildren)
                child_node.path = self.cls._get_path(base_path, child_depth, i + 1)  # type: ignore[attr-defined]

                children_to_create.append(child_node)

                # Recursively process grandchildren
                _collect_children(child_node, grandchildren)

        _collect_children(subtree_root_node, children)

        # Bulk create all descendants at once with batch_size
        if children_to_create:
            created_children = self.cls.objects.bulk_create(
                children_to_create, batch_size=self.batch_size
            )
            self.added_nodes.extend([child.pk for child in created_children])
    """
    added: list[Any] = []
    foreign_keys: dict[str, type[models.Model]] = (  # pyright: ignore
        cls.get_foreign_keys()
    )
    pk_field: str = cls._meta.pk.attname  # pyright: ignore

    subtree_root_to_children_map: dict[MP_Node, list[BulkNodeData]] = {}

    # Create first level of the bulk data
    # This level could have siblings, so we need to process them first
    for node_struct in bulk_data[::-1]:
        # Shallow copy of the data structure so it doesn't persist
        node_data = node_struct["data"].copy()

        # For each fk field, replace pk value with actual object
        cls._process_foreign_keys(foreign_keys, node_data)  # pyright: ignore

        if keep_ids:
            # Will raise KeyError if pk_field is missing
            node_data[pk_field] = node_struct[pk_field]

        # Create first-level node using atomic methods
        if parent:
            node_obj = parent.add_child(**node_data)  # pyright: ignore
        else:
            node_obj = cls.add_root(**node_data)  # pyright: ignore

        added.append(node_obj.pk)  # pyright: ignore

        # Track children for bulk creation
        if "children" in node_struct:
            subtree_root_to_children_map[node_obj] = node_struct["children"]

    children_to_create: list[MP_Node] = []

    def _collect_children(
        parent_node: MP_Node, child_nodes: list[BulkNodeData]
    ) -> None:
        """Recursively collects child nodes and their metadata.

        Args:
            parent_node (MP_Node): The parent node to which child nodes belong.
            child_nodes (list[BulkNodeData]): The list of child nodes to process.
        """
        base_path = parent_node.path
        child_depth = parent_node.depth + 1

        for i, child in enumerate(child_nodes[::-1]):
            child_node, grandchildren = child["data"], child.get("children", [])
            child_obj = cls(**child_node)

            child_obj.depth = child_depth
            child_obj.numchild = len(grandchildren)
            child_obj.path = cls._get_path(base_path, child_depth, i + 1)  # type: ignore[attr-defined]

            children_to_create.append(child_obj)

            # Recursively process grandchildren
            _collect_children(child_obj, grandchildren)

    for subtree_root, children in subtree_root_to_children_map.items():
        _collect_children(subtree_root, children)

    # Bulk create all descendants at once with batch_size
    if children_to_create:
        created_children = cls.objects.bulk_create(children_to_create, batch_size=1000)
        added.extend([child.pk for child in created_children])

    return added


data: list[BulkNodeData] = [
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
