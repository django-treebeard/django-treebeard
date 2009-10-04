
import datetime
import random

from django import forms
from django.db import transaction
from django.http import HttpResponseRedirect
from django.db import connection
from django.shortcuts import render_to_response, get_object_or_404
from django.core.cache import cache

from tbexample.models import MP_Post, AL_Post, NS_Post
from tbexample.forms import CommentForm


def treetype2model(treetype):
    """ Returns the tree model for a given tree type from the url
    """
    return {'mp': MP_Post,
            'al': AL_Post,
            'ns': NS_Post}[treetype]


@transaction.commit_on_success
def load_random_data(request, treetype):
    """ Makes lots of dummy posts.
    """
    tbmodel = treetype2model(treetype)
    data = {'sql_queries': connection.queries,
            'treetype': treetype}

    key = 'treebeard_tbexample_loadfloodprot_%s' % treetype
    if cache.get(key):
        return render_to_response('tbexample/loadflood.html', data)
    cache.set(key, True, 60*5)

    interval = range(1,6)
    vals = {1: 4, 2: 10, 3: 25, 4: 50, 5: 50}
    for depth in interval:
        num = vals[depth]
        if depth > 1:
            if treetype == 'al':
                nodes = [obj for obj in tbmodel.objects.all()
                         if obj.get_depth() == depth-1]
            else:
                nodes = list(tbmodel.objects.filter(depth=depth-1))
        for i in range(num):
            if depth == 1:
                meth = tbmodel.add_root
            else:
                node = nodes[random.randint(0, len(nodes)-1)]
                if treetype == 'ns':
                    node = tbmodel.objects.get(pk=node.id)
                meth = node.add_child
            obj = meth(author='author_%d' % (i,),
                 comment='lorem ipsum! %d' % (random.randint(1000000000,
                                                             9999999999), ),
                 created=datetime.datetime.now())
    return render_to_response('tbexample/loaddata.html', data)


@transaction.commit_on_success
def delete_node(request, treetype, node_id):
    """ View to remove a message and it's replies
    """
    tbmodel = treetype2model(treetype)
    data = {'sql_queries': connection.queries,
            'treetype': treetype}
    node = get_object_or_404(tbmodel, id=node_id)
    node.delete()
    return render_to_response('tbexample/delete.html', data)


@transaction.commit_on_success
def delete_all(request, treetype):
    """ Remove all messages
    """
    tbmodel = treetype2model(treetype)
    data = {'sql_queries': connection.queries,
            'treetype': treetype}
    tbmodel.objects.all().delete()
    return render_to_response('tbexample/delete.html', data)


@transaction.commit_on_success
def convo(request, treetype, node_id=None):
    """ convo view~
    """
    tbmodel = treetype2model(treetype)
    data = {'sql_queries': connection.queries,
            'treetype': treetype}
    if node_id:
        root = get_object_or_404(tbmodel, id=node_id)
        if root.get_depth() != 1:
            # meh not really a root node, redirecting...
            return HttpResponseRedirect('%s#comment_%d' %
                (root.get_root().get_absolute_url(), root.id))
    else:
        root = None

    if request.method == 'POST':
        form = CommentForm(request.POST)
        form.root = root
        form.tbmodel = tbmodel
        if form.is_valid():
            obj = form.add_method(
                author=form.cleaned_data['author'],
                comment=form.cleaned_data['comment'],
                created=datetime.datetime.now())
            if not root:
                root = obj
            data['link'] = '%s#comment_%d' % \
                           (root.get_absolute_url(), obj.id)
            return render_to_response('tbexample/posted.html', data)
    else:
        form = CommentForm()
        form.root = root
        form.tbmodel = tbmodel

    data['form'] = form
    if node_id:
        template_html = 'tbexample/convo.html'
        descendants = root.get_descendants()
        nodes = [(root, len(descendants))] + [
            (node, node.get_children_count())
            for node in descendants
        ]
        data['mainpage'] = False
        data['nodes'] = nodes
        form.fields['parent'].widget = forms.TextInput()
    else:
        template_html = 'tbexample/main.html'
        data['mainpage'] = True
        data['nodes'] = [(node, node.descendants_count)
                         for node in tbmodel.get_descendants_group_count()]
        data['total_comments'] = len(data['nodes']) + \
                                 sum([count for _, count in data['nodes']])
        data['treetype'] = treetype
    return render_to_response(template_html, data)


def choose(request):
    return render_to_response('tbexample/choose.html', {})


