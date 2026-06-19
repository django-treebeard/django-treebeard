from typing import Any, TypedDict

from django.core import serializers
from django.core.serializers.base import DeserializedObject
from django.db import models


class DumpData(TypedDict):
    data: dict[str, Any]
    children: list["DumpData"]  # TODO: This should really be NotRequired. Add when Python 3.10 support is dropped


def prepare_dumpdata_for_loading(
    cls: type[models.Model], *, data: list[DumpData], keep_ids: bool
) -> list[DeserializedObject]:
    """
    Given data previously dumped using dump_data, prepares a DeserializedObject for use with load_data.
    """
    pk_field = cls._meta.pk.attname
    model_identifier = str(cls._meta)
    output = []
    for item in data:
        obj = {"fields": item["data"], "model": model_identifier, "pk": item[pk_field] if keep_ids else None}
        deserialized_obj = next(serializers.deserialize("python", [obj]))
        deserialized_obj.children = prepare_dumpdata_for_loading(cls, data=item.get("children", []), keep_ids=keep_ids)
        output.append(deserialized_obj)

    return output


def save_m2m(node: models.Model, deserialized_obj: DeserializedObject):
    """
    Saves m2m relationships stored on a DeserializedObject.
    """
    if deserialized_obj.m2m_data:
        for accessor_name, object_list in deserialized_obj.m2m_data.items():
            getattr(node, accessor_name).set(object_list)
        deserialized_obj.m2m_data = None  # Avoid accidental reuse of m2m_data if save() is called on the object
