from django.contrib import admin
from django.urls import include, path

admin.autodiscover()

urlpatterns = [
    path('admin/', admin.site.urls),
]
