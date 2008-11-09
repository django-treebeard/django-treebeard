from django import forms
from django.db import transaction


class CommentForm(forms.Form):
    """ A fancy comment form.
    """
    author = forms.CharField(label='Author',
                             max_length=255)
    comment = forms.CharField(label='Comment',
                              widget=forms.Textarea)
    parent = forms.IntegerField(label='Parent',
                                required=False,
                                widget=forms.HiddenInput)


    @transaction.commit_on_success
    def clean_parent(self):
        """ Parent field validation
        """
        if self.root is None:
            self.add_method = self.tbmodel.add_root
            return
        parent_id = self.cleaned_data['parent']
        if not parent_id:
            parent_id = self.root.id
        try:
            parent_obj = self.tbmodel.objects.get(id=parent_id)
        except self.tbmodel.DoesNotExist:
            raise forms.ValidationError('Invalid comment id: %d' %
                                        (parent_id,))
        if parent_obj != self.root and not parent_obj.is_descendant_of(self.root):
            raise forms.ValidationError(
                'Comment %d does not belong to convo %d (wrong page)' %
                (parent_id, self.root.id,))
        self.add_method = parent_obj.add_child


