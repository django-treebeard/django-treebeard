from django.contrib import admin
from treebeard.admin import TreebeardModelAdmin

from tbexample.models import MP_Post, AL_Post, NS_Post


class MP_Admin(TreebeardModelAdmin):
    pass


class AL_Admin(TreebeardModelAdmin):
    pass

class NS_Admin(TreebeardModelAdmin):
    pass


admin.site.register(MP_Post, MP_Admin)
admin.site.register(AL_Post, AL_Admin)
admin.site.register(NS_Post, NS_Admin)
