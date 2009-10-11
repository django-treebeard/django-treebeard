from django.forms.models import model_to_dict, ErrorList, BaseModelForm
from django import forms
from django.contrib import admin


class TreeFormAdmin(forms.ModelForm):
    """ Admin for for treebeard model. """

    __position_choices = (
                        ('first-child', 'First child of'),
                        ('left', 'Before'),
                        ('right', 'After'),
                    )
    _position = forms.ChoiceField( required=True,
                                    label="Position",
                                    choices=__position_choices)

    _ref_node_id = forms.TypedChoiceField(  required=False,
                                            coerce=int,
                                            label="Relative to")

    class Meta:
        exclude = ( 'path',
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

        def mk_dropdown_tree(for_node=None):
            """ Creates a tree-like list of choices """

            is_loop_safe = lambda(possible_parent): True
            # Do actual check only if for_node is provided
            if for_node is not None:
                is_loop_safe = lambda(possible_parent): not (\
                            possible_parent.is_descendant_of(for_node) or \
                            possible_parent == for_node)

            mk_indent = lambda(level): '. . ' * (level - 1)

            def add_subtree(node, options):
                """ Recursively build options tree. """
                options.append((node.pk, mk_indent(node.get_depth())+str(node)))
                for subnode in node.get_children():
                    if is_loop_safe(subnode):
                        add_subtree(subnode, options)

            options = [(0, '-- root --')]
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
            prev_sibling = instance.get_prev_sibling()
            if prev_sibling is None:
                if(instance.is_root()):
                    object_data.update({'_ref_node_id': '',
                                        '_position': 'first-child',
                                        })
                else:
                    object_data.update({'_ref_node_id': instance.get_parent().pk,
                                        '_position': 'first-child',
                                        })
            else:
                object_data.update({'_ref_node_id': prev_sibling.pk,
                                    '_position': 'right',
                                    })

            self.declared_fields['_ref_node_id'].choices = mk_dropdown_tree(for_node=instance)
            self.instance = instance
        # if initial was provided, it should override the values from instance
        if initial is not None:
            object_data.update(initial)

        super(BaseModelForm, self).__init__(data, files, auto_id, prefix,
                                            object_data, error_class,
                                            label_suffix, empty_permitted)

    def save(self, commit=True):
        reference_node_id = 0
        if self.cleaned_data.has_key('_ref_node_id'):
            reference_node_id = self.cleaned_data['_ref_node_id']
        position_type = self.cleaned_data['_position']

        # delete auxilary fields not belonging to node model
        del self.cleaned_data['_ref_node_id']
        del self.cleaned_data['_position']

        if self.instance.pk is None:
            if reference_node_id:
                parent_node = self.Meta.model.objects.get(pk=reference_node_id)
                self.instance = parent_node.add_child(** self.cleaned_data)
            else:
                self.instance = self.Meta.model.add_root(** self.cleaned_data)
        else:
            if reference_node_id:
                parent_node = self.Meta.model.objects.get(pk=reference_node_id)
                self.instance.move(parent_node, pos=position_type)
            else:
                self.instance.move(self.Meta.model.get_first_root_node(),
                                                            pos='first-sibling')
            # Reload the instance
            self.instance = self.Meta.model.objects.get(pk=self.instance.pk)
        super(TreeFormAdmin, self).save(commit=commit)
        return self.instance

class TreeAdmin(admin.ModelAdmin):
    """ Manages treebeard model. """
    change_list_template = 'admin/tree_change_list.html'
    form = TreeFormAdmin
