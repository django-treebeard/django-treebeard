# -*- coding: utf-8 -*-
"""

    tbbench.models
    --------------

    django-treebeard django models

    :copyright: 2008 by Gustavo Picon
    :license: Apache License 2.0

"""

from django.db import models
from treebeard.mp_tree import MP_Node
try:
    import mptt
except ImportError:
    mptt = None



class TbNode(MP_Node):
    numval = models.IntegerField()
    strval = models.CharField(max_length=255)


class TbSortedNode(MP_Node):
    node_order_by = ['numval', 'strval']

    numval = models.IntegerField()
    strval = models.CharField(max_length=255)

if mptt:
    class MpttNode(models.Model):
        numval = models.IntegerField()
        strval = models.CharField(max_length=255)
        parent = models.ForeignKey('self',
                                   null=True,
                                   blank=True,
                                   related_name='children')
    mptt.register(MpttNode)

    class MpttSortedNode(models.Model):
        numval = models.IntegerField()
        strval = models.CharField(max_length=255)
        parent = models.ForeignKey('self',
                                   null=True,
                                   blank=True,
                                   related_name='children')
    mptt.register(MpttSortedNode, order_insertion_by=['numval', 'strval'])

else:
    MpttNode, MpttSortedNode = None, None

