"""Forms for treebeard."""

from django import forms
from django.forms.models import modelform_factory as django_modelform_factory
from django.forms.utils import ErrorList
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from treebeard.al_tree import AL_Node
from treebeard.mp_tree import MP_Node
from treebeard.ns_tree import NS_Node


class MoveNodeForm(forms.ModelForm):
    """
    Form to handle moving a node in a tree.

    Handles sorted/unsorted trees.

    It adds two fields to the form:

    - Relative to: The target node where the current node will
                   be moved to.
    - Position: The position relative to the target node that
                will be used to move the node. These can be:

                - For sorted trees: ``Child of`` and ``Sibling of``
                - For unsorted trees: ``First child of``, ``Before`` and
                  ``After``

    .. warning::

        Subclassing :py:class:`MoveNodeForm` directly is
        discouraged, since special care is needed to handle
        excluded fields, and these change depending on the
        tree type.

        It is recommended that the :py:func:`movenodeform_factory`
        function is used instead.

    """

    __position_choices_sorted = (
        ("sorted-child", _("Child of")),
        ("sorted-sibling", _("Sibling of")),
    )

    __position_choices_unsorted = (
        ("first-child", _("First child of")),
        ("left", _("Before")),
        ("right", _("After")),
    )

    treebeard_position = forms.ChoiceField(required=True, label=_("Position"))

    treebeard_ref_node_id = forms.ChoiceField(required=False, label=_("Relative to"))

    def _get_position_ref_node(self, instance):
        if self.is_sorted:
            position = "sorted-child"
            node_parent = instance.get_parent()
            if node_parent:
                ref_node_id = node_parent.pk
            else:
                ref_node_id = ""
        else:
            prev_sibling = instance.get_prev_sibling()
            if prev_sibling:
                position = "right"
                ref_node_id = prev_sibling.pk
            else:
                position = "first-child"
                if instance.is_root():
                    ref_node_id = ""
                else:
                    ref_node_id = instance.get_parent().pk
        return {"treebeard_ref_node_id": ref_node_id, "treebeard_position": position}

    def __init__(
        self,
        data=None,
        files=None,
        auto_id="id_%s",
        prefix=None,
        initial=None,
        error_class=ErrorList,
        label_suffix=":",
        empty_permitted=False,
        instance=None,
        **kwargs,
    ):
        opts = self._meta
        if opts.model is None:
            raise ValueError("ModelForm has no model class specified")

        # update the 'treebeard_position' field choices
        self.is_sorted = getattr(opts.model, "node_order_by", False)
        if self.is_sorted:
            choices_sort_mode = self.__class__.__position_choices_sorted
        else:
            choices_sort_mode = self.__class__.__position_choices_unsorted
        self.declared_fields["treebeard_position"].choices = choices_sort_mode

        # update the 'treebeard_ref_node_id' choices
        choices = self.mk_dropdown_tree(opts.model, for_node=instance)
        self.declared_fields["treebeard_ref_node_id"].choices = choices
        # use the formfield `to_python` method to coerse the field for custom ids
        pkFormField = opts.model._meta.pk.formfield()
        self.declared_fields["treebeard_ref_node_id"].coerce = pkFormField.to_python if pkFormField else int

        # put initial data for these fields into a map, update the map with
        # initial data, and pass this new map to the parent constructor as
        # initial data
        if instance is None:
            initial_ = {}
        else:
            initial_ = self._get_position_ref_node(instance)

        if initial is not None:
            initial_.update(initial)

        super().__init__(
            data=data,
            files=files,
            auto_id=auto_id,
            prefix=prefix,
            initial=initial_,
            error_class=error_class,
            label_suffix=label_suffix,
            empty_permitted=empty_permitted,
            instance=instance,
            **kwargs,
        )

    def _clean_cleaned_data(self):
        """delete auxilary fields not belonging to node model"""
        reference_node_id = self.cleaned_data.pop("treebeard_ref_node_id", None)

        if reference_node_id and reference_node_id.isdigit():
            reference_node_id = int(reference_node_id)

        position_type = self.cleaned_data.pop("treebeard_position")

        return position_type, reference_node_id

    def save(self, commit=True):
        position_type, reference_node_id = self._clean_cleaned_data()

        if self.instance._state.adding:
            if reference_node_id:
                reference_node = self._meta.model.objects.get(pk=reference_node_id)
                self.instance = reference_node.add_child(instance=self.instance)
                self.instance.move(reference_node, pos=position_type)
            else:
                self.instance = self._meta.model.add_root(instance=self.instance)
        else:
            self.instance.save()
            if reference_node_id:
                reference_node = self._meta.model.objects.get(pk=reference_node_id)
                self.instance.move(reference_node, pos=position_type)
            else:
                if self.is_sorted:
                    pos = "sorted-sibling"
                else:
                    pos = "first-sibling"
                self.instance.move(self._meta.model.get_first_root_node(), pos)
        # Reload the instance
        self.instance.refresh_from_db()
        super().save(commit=commit)
        return self.instance

    @staticmethod
    def is_loop_safe(for_node, possible_parent):
        if for_node is not None:
            return not (possible_parent == for_node) or (possible_parent.is_descendant_of(for_node))
        return True

    @staticmethod
    def mk_indent(level):
        return "&nbsp;&nbsp;&nbsp;&nbsp;" * (level - 1)

    @classmethod
    def add_subtree(cls, for_node, node, options):
        """Recursively build options tree."""
        if cls.is_loop_safe(for_node, node):
            for item, _ in node.get_annotated_list(node):
                options.append((item.pk, mark_safe(cls.mk_indent(item.get_depth()) + escape(item))))

    @classmethod
    def mk_dropdown_tree(cls, model, for_node=None):
        """Creates a tree-like list of choices"""

        options = [(None, _("-- root --"))]
        for node in model.get_root_nodes():
            cls.add_subtree(for_node, node, options)
        return options


def movenodeform_factory(model, form=MoveNodeForm, exclude=None, **kwargs):
    """Dynamically build a MoveNodeForm subclass with the proper Meta.

    :param Node model:

        The subclass of :py:class:`Node` that will be handled
        by the form.

    :param form:

        The form class that will be used as a base. By
        default, :py:class:`MoveNodeForm` will be used.

    Accepts all other kwargs that can be passed to Django's `modelform_factory`.

    :return: A :py:class:`MoveNodeForm` subclass
    """
    _exclude = _get_exclude_for_model(model, exclude)
    return django_modelform_factory(model, form, exclude=_exclude, **kwargs)


def _get_exclude_for_model(model, exclude):
    if issubclass(model, AL_Node):
        to_exclude = ("sib_order", "parent")
    elif issubclass(model, MP_Node):
        to_exclude = ("depth", "numchild", "path")
    elif issubclass(model, NS_Node):
        to_exclude = ("depth", "lft", "rgt", "tree_id")
    else:
        to_exclude = ()

    return tuple(exclude or ()) + to_exclude
