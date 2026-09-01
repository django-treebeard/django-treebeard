"""Django admin support for treebeard"""

import warnings

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.templatetags.admin_list import result_list
from django.contrib.admin.views.main import IGNORED_PARAMS, PAGE_VAR, SEARCH_VAR
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models.query import QuerySet
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.template import loader
from django.urls import path
from django.utils.translation import gettext_lazy as _
from django.views.i18n import JavaScriptCatalog

from treebeard.exceptions import InvalidMoveToDescendant, InvalidPosition, MissingNodeOrderBy, PathOverflow
from treebeard.templatetags.admin_tree import tree_context


class TreeAdmin(admin.ModelAdmin):
    """Django Admin class for treebeard."""

    change_list_template = "admin/tree_change_list.html"

    def __init__(self, *args, **kwargs):
        if self.list_editable:
            warnings.warn("list_editable cannot be used with TreeAdmin. The value will be ignored.")
            self.__class__.list_editable = ()
        super().__init__(*args, **kwargs)

    def is_filtered(self, request) -> bool:
        """
        Whether the changelist is showing a search result or a filtered list.

        The changelist normally shows one level of the tree and is drilled into
        from there, which a search cannot work with: it would only ever match
        the level that happens to be on screen. A filtered changelist therefore
        drops the tree and lists every match, wherever it sits.
        """
        if request.GET.get(SEARCH_VAR):
            return True

        ignored = {*IGNORED_PARAMS, PAGE_VAR, SEARCH_VAR}

        return any(param not in ignored for param in request.GET)

    def get_queryset(self, request) -> QuerySet:
        # We only filter the queryset when _treebeard_parent_id is set
        if not hasattr(request, "_treebeard_parent_id"):
            return super().get_queryset(request)

        # A search or a filter looks at the whole tree, not at one level of it.
        if self.is_filtered(request):
            request._treebeard_parent = None
            return super().get_queryset(request)

        if request._treebeard_parent_id:
            parent = get_object_or_404(self.model, pk=request._treebeard_parent_id)
            request._treebeard_parent = parent
            qs = self.model.objects.get_children(parent)
        else:
            request._treebeard_parent = None
            qs = self.model.objects.get_root_nodes()

        # For inherited models, we need to convert back from the tree model to the specific one
        # filtering out any nodes that don't have a specific instance
        if self.model != qs.model:
            ptr = self.model._meta.get_ancestor_link(qs.model).name
            qs = self.model.objects.filter(**{f"{ptr}__in": qs})

        return qs

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
            path("children/<str:parent_id>/", self.admin_site.admin_view(self.children_view)),
            path("jsi18n/", JavaScriptCatalog.as_view(packages=["treebeard"]), name="javascript-catalog"),
        ]
        return new_urls + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        if request.method == "GET":
            request._treebeard_parent_id = None

        extra_context = {
            **(extra_context or {}),
            # The template drops the tree markup and its script when the list is
            # a flat set of matches, since neither expanding nor dragging means
            # anything without the surrounding tree.
            "treebeard_tree": not self.is_filtered(request),
        }

        return super().changelist_view(request, extra_context)

    def children_view(self, request, parent_id):
        """
        Handles AJAX requests for children of a node, and returns, in a JSON object:

        - The HTML for the tree
        - The JSON context object for the nodes
        """

        if not self.has_view_permission(request):
            raise PermissionDenied

        request._treebeard_parent_id = parent_id
        cl = self.get_changelist_instance(request)
        cl.formset = None

        return JsonResponse(
            {
                "result_html": loader.get_template("admin/change_list_results.html").render(result_list(cl)),
                "tree_context": tree_context(cl, request),
                "page": cl.page_num,
                "num_pages": cl.paginator.num_pages,
            }
        )

    def move_node(self, request):
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied

        class MoveForm(forms.Form):
            node = forms.ModelChoiceField(queryset=self.model.objects.all())
            target = forms.ModelChoiceField(queryset=self.model.objects.all())
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
