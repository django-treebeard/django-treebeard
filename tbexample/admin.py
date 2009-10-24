from django.contrib import admin
from treebeard.admin import TreeAdmin

from tbexample.models import MP_Post, AL_Post, NS_Post


class MP_Admin(TreeAdmin):
    pass


class AL_Admin(TreeAdmin):
    pass

class NS_Admin(TreeAdmin):
    pass


admin.site.register(MP_Post, MP_Admin)
admin.site.register(AL_Post, AL_Admin)
admin.site.register(NS_Post, NS_Admin)
