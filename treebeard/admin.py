"""Django admin support for treebeard"""

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.urls import path
from django.utils.translation import gettext_lazy as _
from django.views.i18n import JavaScriptCatalog

from treebeard.al_tree import AL_Node
from treebeard.exceptions import InvalidMoveToDescendant, InvalidPosition, MissingNodeOrderBy, PathOverflow


def check_empty_dict(GET_dict):
    """
    Returns True if the GET query string contains no values, but it can contain
    empty keys.
    This is better than doing not bool(request.GET) as an empty key will return True
    """
    for k, v in GET_dict.items():
        # Don't disable on p(age) or 'all' GET param
        if v and (k not in ["p", "all"]):
            return False
    return True


class TreeAdmin(admin.ModelAdmin):
    """Django Admin class for treebeard."""

    change_list_template = "admin/tree_change_list.html"

    def get_queryset(self, request):
        if issubclass(self.model, AL_Node):
            # AL Trees return a list instead of a QuerySet for .get_tree()
            # So we're returning the regular .get_queryset cause we will use
            # the old admin
            return super().get_queryset(request)

        # We deliberately don't use `get_tree()` here because we want the specific
        # model for inherited models. This assumes that all implementations
        # return the queryset in DFS order (except AL_Node which is handled above).
        return self.model.objects.all()

    def changelist_view(self, request, extra_context=None):
        if issubclass(self.model, AL_Node):
            # For AL trees, use the old admin display
            self.change_list_template = "admin/tree_list.html"

        if extra_context is None:
            extra_context = {}

        extra_context["has_change_permission"] = self.has_change_permission(request)
        extra_context["filtered"] = not check_empty_dict(request.GET)
        return super().changelist_view(request, extra_context)

    def _changeform_view(self, *args, **kwargs):
        # Because Treebeard frequently needs to modify many objects in a tree when one node
        # is added/updated, the normal behaviour of relying on `commit=False` to create
        # unsaved objects before validating inlines etc doesn't work: Treebeard has already
        # made database changes to prepare to insert/move a node.
        # For this reason, if the form has error
        response = super()._changeform_view(*args, **kwargs)
        if getattr(response, "context_data", {}).get("errors", None):
            # There was an error somewhere, likely in an inline, so we'll need to roll back
            transaction.set_rollback(True)
        return response

    def get_urls(self):
        """
        Adds a url to move nodes to this admin
        """
        new_urls = [
            path("move/", self.admin_site.admin_view(self.move_node)),
            path("jsi18n/", JavaScriptCatalog.as_view(packages=["treebeard"]), name="javascript-catalog"),
        ]
        return new_urls + super().get_urls()

    def move_node(self, request):
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied

        qs = self.get_queryset(request)

        class MoveForm(forms.Form):
            node = forms.ModelChoiceField(queryset=qs)
            target = forms.ModelChoiceField(queryset=qs)
            relation = forms.ChoiceField(choices=(("child", "child"), ("sibling", "sibling")))

        form = MoveForm(request.POST)

        if not form.is_valid():
            messages.error(request, _("Invalid form data provided"))
            return HttpResponseBadRequest("Invalid form data provided")

        node = form.cleaned_data["node"]
        target = form.cleaned_data["target"]
        relation = form.cleaned_data["relation"]

        if not self.has_change_permission(request, node):
            # The JS will trigger a page reload on error. This message will be displayed after reload.
            messages.error(request, _("You do not have permission to change this object."))
            raise PermissionDenied

        pos = {
            ("child", True): "sorted-child",
            ("child", False): "last-child",
            ("sibling", True): "sorted-sibling",
            ("sibling", False): "left",
        }[relation, bool(self.model.node_order_by)]

        try:
            self.model.objects.move(node, target, pos=pos)
            # Call the save method on the (reloaded) node in order to trigger
            # possible signal handlers etc.
            node.refresh_from_db()
            node.save()
        except (MissingNodeOrderBy, PathOverflow, InvalidMoveToDescendant, InvalidPosition) as exc:
            # An error was raised while trying to move the node, then set an
            # error message and return 400, this will cause a reload on the
            # client to show the message
            messages.error(request, _(str(exc)))
            return HttpResponseBadRequest("Exception raised during move")

        msg = (
            _('Moved node "%(node)s" as child of "%(other)s"')
            if relation == "child"
            else _('Moved node "%(node)s" as sibling of "%(other)s"')
        )
        messages.info(request, msg % {"node": node, "other": target})
        return HttpResponse("OK")


def admin_factory(form_class):
    """Dynamically build a TreeAdmin subclass for the given form class.

    :param form_class:
    :return: A TreeAdmin subclass.
    """
    return type(form_class.__name__ + "Admin", (TreeAdmin,), dict(form=form_class))
