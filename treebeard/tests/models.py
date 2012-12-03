from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

from treebeard.mp_tree import MP_Node
from treebeard.al_tree import AL_Node
from treebeard.ns_tree import NS_Node


class MP_TestNode(MP_Node):
    steplen = 3

    desc = models.CharField(max_length=255)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class MP_TestNodeSomeDep(models.Model):
    node = models.ForeignKey(MP_TestNode)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class NS_TestNode(NS_Node):
    desc = models.CharField(max_length=255)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class NS_TestNodeSomeDep(models.Model):
    node = models.ForeignKey(NS_TestNode)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class AL_TestNode(AL_Node):
    parent = models.ForeignKey('self',
                               related_name='children_set',
                               null=True,
                               db_index=True)
    sib_order = models.PositiveIntegerField()
    desc = models.CharField(max_length=255)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class AL_TestNodeSomeDep(models.Model):
    node = models.ForeignKey(AL_TestNode)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class MP_TestNodeSorted(MP_Node):
    steplen = 1
    node_order_by = ['val1', 'val2', 'desc']
    val1 = models.IntegerField()
    val2 = models.IntegerField()
    desc = models.CharField(max_length=255)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class NS_TestNodeSorted(NS_Node):
    node_order_by = ['val1', 'val2', 'desc']
    val1 = models.IntegerField()
    val2 = models.IntegerField()
    desc = models.CharField(max_length=255)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class AL_TestNodeSorted(AL_Node):
    parent = models.ForeignKey('self',
                               related_name='children_set',
                               null=True,
                               db_index=True)
    node_order_by = ['val1', 'val2', 'desc']
    val1 = models.IntegerField()
    val2 = models.IntegerField()
    desc = models.CharField(max_length=255)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class MP_TestNodeAlphabet(MP_Node):
    steplen = 2

    numval = models.IntegerField()

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class MP_TestNodeSmallStep(MP_Node):
    steplen = 1
    alphabet = '0123456789'

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class MP_TestNodeSortedAutoNow(MP_Node):
    desc = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)

    node_order_by = ['created']

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class MP_TestNodeShortPath(MP_Node):
    steplen = 1
    alphabet = '01234'
    desc = models.CharField(max_length=255)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


# This is how you change the default fields defined in a Django abstract class
# (in this case, MP_Node), since Django doesn't allow overriding fields, only
# mehods and attributes
MP_TestNodeShortPath._meta.get_field('path').max_length = 4


class MP_TestNode_Proxy(MP_TestNode):
    class Meta:
        proxy = True


class NS_TestNode_Proxy(NS_TestNode):
    class Meta:
        proxy = True


class AL_TestNode_Proxy(AL_TestNode):
    class Meta:
        proxy = True


class MP_TestSortedNodeShortPath(MP_Node):
    steplen = 1
    alphabet = '01234'
    desc = models.CharField(max_length=255)

    node_order_by = ['desc']

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


MP_TestSortedNodeShortPath._meta.get_field('path').max_length = 4

class MP_TestIssue14(MP_Node):
    name = models.CharField(max_length=255)
    users = models.ManyToManyField(User)
