import warnings
from functools import partial, partialmethod


class RemovedInTreebeard7Warning(DeprecationWarning): ...


def _handle_moved_classmethod(cls, *args, treebeard_method, **kwargs):  # pragma: no cover
    """
    Backward compatibility for class methods that have moved to the model manager.

    Logs a warning, and calls the manager method.

    This backward-compatibility will be removed in Treebeard 7.
    """
    warnings.warn(
        f"Using {cls.__name__}.{treebeard_method}() is deprecated. "
        f"Use {cls.__name__}.objects.{treebeard_method}() instead.",
        RemovedInTreebeard7Warning,
        stacklevel=3,
    )
    return getattr(cls.objects, treebeard_method)(*args, **kwargs)


def _handle_moved_method(self, *args, treebeard_method, **kwargs):  # pragma: no cover
    """
    Backward compatibility for methods that have moved to the model manager.

    Logs a warning, and calls the manager method.

    This backward-compatibility will be removed in Treebeard 7.
    """
    cls = self.__class__
    warnings.warn(
        f"Using {cls.__name__}.{treebeard_method}() is deprecated. "
        f"Use {cls.__name__}.objects.{treebeard_method}() instead.",
        RemovedInTreebeard7Warning,
        stacklevel=2,
    )
    return getattr(cls.objects, treebeard_method)(self, *args, **kwargs)


def moved_manager_classmethod(method_name):
    return classmethod(partial(_handle_moved_classmethod, treebeard_method=method_name))


def moved_manager_method(method_name):
    return partialmethod(_handle_moved_method, treebeard_method=method_name)
