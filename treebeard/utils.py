import inspect
from typing import Any, TypedDict

from django.core import serializers
from django.core.serializers.base import DeserializedObject
from django.db import models

from treebeard.exceptions import NodeAlreadySaved


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


def check_create_args(func):
    """
    Decorator to validate `create_kwargs` and `instance` parameters for methods that
    create new model objects.

    - Ensures that only one of `create_kwargs` and `instance` are set.
    - If `instance` is provided, ensures that is it an unsaved model object
    """
    sig = inspect.signature(func)

    def wrapper(*args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        instance = bound.arguments.get("instance")
        create_kwargs = bound.arguments.get("create_kwargs")

        if instance and create_kwargs:
            raise ValueError("Only one of create_kwargs and instance is allowed.")

        if instance is None and create_kwargs is None:
            raise ValueError("Either create_kwargs or instance must be supplied")

        if instance and not instance._state.adding:
            raise NodeAlreadySaved("Attempted to add a tree node that is already in the database")

        return func(*args, **kwargs)

    return wrapper
