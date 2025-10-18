import itertools

from django.contrib import admin

from tests.models import BASE_MODELS, DEP_MODELS, UNICODE_MODELS
from treebeard.admin import admin_factory
from treebeard.forms import movenodeform_factory


def register(admin_site, model):
    form_class = movenodeform_factory(model)
    admin_class = admin_factory(form_class)
    admin_site.register(model, admin_class)


def register_all(admin_site=admin.site):
    for model in itertools.chain(BASE_MODELS, UNICODE_MODELS, DEP_MODELS):
        register(admin_site, model)
