Forms
=====

.. module:: treebeard.forms

.. autoclass:: MoveNodeForm
   :show-inheritance:

.. autofunction:: movenodeform_factory

    For a full reference of this function, please read
    the `documentation for modelform_factory`_.


    Example, ``MyNode`` is a subclass of :py:class:`treebeard.al_tree.AL_Node`:

    .. code-block:: python

        MyNodeForm = movenodeform_factory(MyNode)

    is equivalent to:

    .. code-block:: python

        class MyNodeForm(MoveNodeForm):
            class Meta:
                model = models.MyNode
                exclude = ('sib_order', 'parent')



.. _`documentation for modelform_factory`:
   https://docs.djangoproject.com/en/dev/ref/forms/models/#django.forms.models.modelform_factory

