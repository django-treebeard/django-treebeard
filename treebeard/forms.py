"Forms for treebeard."

from django.forms.models import model_to_dict, ErrorList, BaseModelForm
from django import forms
from django.utils.translation import ugettext as _


class MoveNodeForm(forms.ModelForm):
    """
    Form to handle moving a node in a tree.

    Handles sorted/unsorted trees.
    """

    __position_choices_sorted = (
                        ('sorted-child', _(u'Child of')),
                        ('sorted-sibling', _(u'Sibling of')),
                    )

    __position_choices_unsorted = (
                        ('first-child', _(u'First child of')),
                        ('left', _(u'Before')),
                        ('right', _(u'After')),
                    )

    _position = forms.ChoiceField(required=True, label=_(u"Position"))

    _ref_node_id = forms.TypedChoiceField(required=False,
                                          coerce=int,
                                          label=_(u"Relative to"))

    class Meta:
        exclude = ('path',
                   'depth',
                   'numchild',
                   'lft',
                   'rgt',
                   'tree_id',
                   'parent',
                   'sib_order')

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, instance=None):

        opts = self._meta
        if instance:
            opts.model = type(instance)
        self.is_sorted = (hasattr(opts.model, 'node_order_by') and
                          opts.model.node_order_by)
        #self.is_sorted = (len(opts.model.node_order_by) > 0)

        if self.is_sorted:
            self.declared_fields['_position'].choices = \
                self.__class__.__position_choices_sorted
        else:
            self.declared_fields['_position'].choices = \
                self.__class__.__position_choices_unsorted

        def mk_dropdown_tree(for_node=None):
            """ Creates a tree-like list of choices """

            is_loop_safe = lambda(possible_parent): True
            # Do actual check only if for_node is provided
            if for_node is not None:
                is_loop_safe = lambda(possible_parent): not (\
                            possible_parent == for_node) or \
                            possible_parent.is_descendant_of(for_node)

            mk_indent = lambda(level): '. . ' * (level - 1)

            def add_subtree(node, options):
                """ Recursively build options tree. """
                if is_loop_safe(node):
                    options.append(
                        (node.pk, mk_indent(node.get_depth()) + str(node)))
                    for subnode in node.get_children():
                        add_subtree(subnode, options)

            options = [(0, _(u'-- root --'))]
            for node in opts.model.get_root_nodes():
                add_subtree(node, options)
            return options

        if instance is None:
            # if we didn't get an instance, instantiate a new one
            self.instance = opts.model()
            object_data = {}
            self.declared_fields['_ref_node_id'].choices = mk_dropdown_tree()
        else:
            object_data = model_to_dict(instance, opts.fields, opts.exclude)
            if self.is_sorted:
                node_parent = instance.get_parent()
                if node_parent is None:
                    object_data.update({'_ref_node_id': '',
                                        '_position': 'sorted-child',
                                        })
                else:
                    object_data.update({'_ref_node_id': node_parent.pk,
                                        '_position': 'sorted-child',
                                        })
            else:
                prev_sibling = instance.get_prev_sibling()
                if prev_sibling is None:
                    if(instance.is_root()):
                        object_data.update({'_ref_node_id': '',
                                            '_position': 'first-child',
                                            })
                    else:
                        object_data.update(
                            {'_ref_node_id': instance.get_parent().pk,
                             '_position': 'first-child',
                            })
                else:
                    object_data.update({'_ref_node_id': prev_sibling.pk,
                                        '_position': 'right',
                                        })
            self.declared_fields['_ref_node_id'].choices = mk_dropdown_tree(
                for_node=instance)
            self.instance = instance
        # if initial was provided, it should override the values from instance
        if initial is not None:
            object_data.update(initial)
        super(BaseModelForm, self).__init__(data, files, auto_id, prefix,
                                            object_data, error_class,
                                            label_suffix, empty_permitted)

    def save(self, commit=True):
        reference_node_id = 0
        if '_ref_node_id' in self.cleaned_data:
            reference_node_id = self.cleaned_data['_ref_node_id']
        position_type = self.cleaned_data['_position']

        # delete auxilary fields not belonging to node model
        del self.cleaned_data['_ref_node_id']
        del self.cleaned_data['_position']
        if self.instance.pk is None:
            if reference_node_id:
                reference_node = self.Meta.model.objects.get(
                    pk=reference_node_id)
                self.instance = reference_node.add_child(** self.cleaned_data)
                self.instance.move(reference_node, pos=position_type)
            else:
                self.instance = self.Meta.model.add_root(** self.cleaned_data)
        else:
            # this is needed in django >= 1.2
            self.instance.save()
            if reference_node_id:
                reference_node = self.Meta.model.objects.get(
                    pk=reference_node_id)
                self.instance.move(reference_node, pos=position_type)
            else:
                if self.is_sorted:
                    self.instance.move(self.Meta.model.get_first_root_node(),
                                                        pos='sorted-sibling')
                else:
                    self.instance.move(self.Meta.model.get_first_root_node(),
                                       pos='first-sibling')
            # Reload the instance
        self.instance = self.Meta.model.objects.get(pk=self.instance.pk)
        super(MoveNodeForm, self).save(commit=commit)
        return self.instance
