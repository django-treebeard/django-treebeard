from copy import deepcopy
from functools import cache
from typing import Any, TypedDict

from django.db import models


class DumpData(TypedDict):
    data: dict[str, Any]
    children: list["DumpData"]  # TODO: This should really be NotRequired. Add when Python 3.10 support is dropped


class PreparedDumpData(DumpData):
    children: list["DumpData"]
    pk: Any  # TODO: This should really be NotRequired. Add when Python 3.10 support is dropped


@cache
def get_foreign_key_fields(cls: type[models.Model]) -> set[str]:
    return {field.name for field in cls._meta.fields if (field.one_to_one or field.many_to_one)}


def prepare_dumpdata_for_loading(
    cls: type[models.Model], *, data: list[DumpData], keep_ids: bool
) -> list[PreparedDumpData]:
    """
    Given data previously dumped using dump_data, prepares the data for use with load_data.

    - Modifies foreign key field names to append an `_id` suffix
    - Adds a pk field if `keep_ids` is True.
    """
    foreign_key_fields = get_foreign_key_fields(cls)
    pk_field = cls._meta.pk.attname
    output = []
    for item in data:
        prepared = deepcopy(item)
        for field in foreign_key_fields:
            # Append _id to field name, so that we don't need to load the foreign objects into memory
            prepared["data"][f"{field}_id"] = prepared["data"].pop(field, None)
        if keep_ids:
            prepared["data"]["pk"] = item[pk_field]

        prepared["children"] = prepare_dumpdata_for_loading(cls, data=item.get("children", []), keep_ids=keep_ids)
        output.append(prepared)

    return output
