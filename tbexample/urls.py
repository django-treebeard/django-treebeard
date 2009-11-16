import os
from django.contrib import admin
from django.conf.urls.defaults import *
import treebeard
from tbexample.views import convo, load_random_data, delete_node, delete_all
from tbexample.views import choose

admin.autodiscover()

baseurl = r'^(?P<treetype>mp|al|ns)/'
lurls = [
    (r'loaddata/$', load_random_data, 'load-data'),
    (r'delete_all/$', delete_all, 'delete-all'),
    (r'(?P<node_id>\d+)/delete/$', delete_node, 'delete-node'),
    (r'(?P<node_id>\d+)/reply/$', convo, 'reply-view'),
    (r'(?P<node_id>\d+)/$', convo, 'node-view'),
    (r'$', convo, 'main-view')
]

path = os.path.dirname(treebeard.__file__)
static_path = os.path.normpath(os.path.join(path, 'static/'))

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': static_path, 'show_indexes': True}))

for pat, view, name in lurls:
    urlpatterns += patterns('', url('%s%s' % (baseurl, pat), view, name=name))
urlpatterns += patterns('', url('^$', choose, name='choose-tree'))
