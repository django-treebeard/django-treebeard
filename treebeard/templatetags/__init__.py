from django.template import Variable


action_form_var = Variable('action_form')


def needs_checkboxes(context):
    return action_form_var.resolve(context) is not None
