from typing import Any, NotRequired, TypedDict


class BulkNodeData(TypedDict):
    """Structure for bulk loading tree nodes.

    Note: When ``keep_ids=True``, the primary key field name (e.g., "id")
    exists as a top-level key alongside "data" and "children".
    """

    data: dict[str, Any]
    children: NotRequired[list["BulkNodeData"]]
