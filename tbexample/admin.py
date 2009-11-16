import datetime

from django.contrib import admin
from treebeard.admin import TreeAdmin

from tbexample.models import MP_Post, AL_Post, NS_Post


class TreeExampleAdmin(TreeAdmin):
    def save_form(self, request, form, change):
        if not change:
            form.cleaned_data['created'] = datetime.datetime.now()
        return form.save(commit=False)


class MP_Admin(TreeExampleAdmin):
    pass


class AL_Admin(TreeExampleAdmin):
    pass


class NS_Admin(TreeExampleAdmin):
    pass


admin.site.register(MP_Post, MP_Admin)
admin.site.register(AL_Post, AL_Admin)
admin.site.register(NS_Post, NS_Admin)
