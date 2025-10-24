## Old implementation

```python
added = []
# stack of nodes to analyze, in reverse order?
stack = [(parent, node) for node in bulk_data[::-1]]
# map of foreign key fields to the model they point to
foreign_keys = cls.get_foreign_keys()
# Name of primary key field
pk_field = cls._meta.pk.attname

while stack:
    parent, node_struct = stack.pop()
    # shallow copy of the data structure so it doesn't persist...
    node_data = node_struct["data"].copy()
    cls._process_foreign_keys(foreign_keys, node_data)
    if keep_ids:
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

# Helpers
@classmethod
def _process_foreign_keys(cls, foreign_keys, node_data):
    """For each foreign key try to load the actual object so load_bulk
    doesn't fail trying to load an int where django expects a
    model instance
    """
    for key in foreign_keys.keys():
        if key in node_data:
            node_data[key] = foreign_keys[key].objects.get(pk=node_data[key])
```

Don't need to handle \_cached_parent_obj, since it is only for the in-memory object.
