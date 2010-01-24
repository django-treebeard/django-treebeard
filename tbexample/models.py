# -*- coding: utf-8 -*-
"""

    tbexample.models
    ----------------

    django-treebeard - models for the example app

    :copyright: 2008-2010 by Gustavo Picon
    :license: Apache License 2.0

"""

from django.db import models

from treebeard.mp_tree import MP_Node
from treebeard.al_tree import AL_Node
from treebeard.ns_tree import NS_Node


class MP_Post(MP_Node):
    author  = models.CharField(max_length=255)
    comment = models.TextField()
    #created = models.DateTimeField(auto_now_add=True)
    # Exception Value: Cannot use None as a query value
    created = models.DateTimeField(editable=False)

    node_order_by = ['created']

    @models.permalink
    def get_absolute_url(self):
        return ('node-view', ('mp', str(self.id),))

    def __unicode__(self):
        return u'MP_Post %d: %s' % (self.id, self.comment)

    class Meta:
        verbose_name = 'Materialized Path Tree Post'

        # when adding a custom Meta class to a MP model, the ordering must be
        # set again
        ordering = ['path']

MP_Post._meta.get_field('path').max_length = 255


class AL_Post(AL_Node):
    author  = models.CharField(max_length=255)
    comment = models.TextField()
    #created = models.DateTimeField(auto_now_add=True)
    # Exception Value: Cannot use None as a query value
    created = models.DateTimeField(editable=False)

    parent = models.ForeignKey('self',
                               related_name='children_set',
                               null=True,
                               db_index=True)
    node_order_by = ['created']

    @models.permalink
    def get_absolute_url(self):
        return ('node-view', ('al', str(self.id),))

    def __unicode__(self):
        return u'AL_Post %d: %s' % (self.id, self.comment)

    class Meta:
        verbose_name = 'Adjacenty List Tree Post'


class NS_Post(NS_Node):
    author  = models.CharField(max_length=255)
    comment = models.TextField()
    #created = models.DateTimeField(auto_now_add=True)
    # Exception Value: Cannot use None as a query value
    created = models.DateTimeField(editable=False)

    node_order_by = ['created']

    @models.permalink
    def get_absolute_url(self):
        return ('node-view', ('ns', str(self.id),))

    def __unicode__(self):
        return u'NS_Post %d: %s' % (self.id, self.comment)

    class Meta:
        verbose_name = 'Nested Set Tree Post'

        # when adding a custom Meta class to a NS model, the ordering must be
        # set again
        ordering = ['tree_id', 'lft']
