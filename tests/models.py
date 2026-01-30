import os
import uuid

from django.db import models

from treebeard.al_tree import AL_Node
from treebeard.ltree import LT_Node
from treebeard.mp_tree import MP_Node
from treebeard.ns_tree import NS_Node


class DescMixin(models.Model):
    """
    Model with desc field, handy for identifying objects in tests
    """

    desc = models.CharField(max_length=255)

    def __str__(self):
        return self.desc

    class Meta:
        abstract = True


class RelatedModel(DescMixin): ...


class MP_TestNode(MP_Node, DescMixin):
    steplen = 3


class MP_TestNodeSomeDep(models.Model):
    node = models.ForeignKey(MP_TestNode, on_delete=models.CASCADE)


class MP_TestNodeRelated(MP_Node, DescMixin):
    steplen = 3
    related = models.ForeignKey(RelatedModel, on_delete=models.CASCADE)


class MP_TestNodeInherited(MP_TestNode):
    extra_desc = models.CharField(max_length=255)


class MP_TestNodeCustomId(MP_Node, DescMixin):
    steplen = 3
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)


class NS_TestNode(NS_Node, DescMixin): ...


class NS_TestNodeSomeDep(models.Model):
    node = models.ForeignKey(NS_TestNode, on_delete=models.CASCADE)


class NS_TestNodeRelated(NS_Node, DescMixin):
    related = models.ForeignKey(RelatedModel, on_delete=models.CASCADE)


class NS_TestNodeInherited(NS_TestNode):
    extra_desc = models.CharField(max_length=255)


class AL_TestNode(AL_Node, DescMixin):
    parent = models.ForeignKey(
        "self",
        related_name="children_set",
        null=True,
        db_index=True,
        on_delete=models.CASCADE,
    )
    sib_order = models.PositiveIntegerField()


class AL_TestNodeSomeDep(models.Model):
    node = models.ForeignKey(AL_TestNode, on_delete=models.CASCADE)


class AL_TestNodeRelated(AL_Node, DescMixin):
    parent = models.ForeignKey(
        "self",
        related_name="children_set",
        null=True,
        db_index=True,
        on_delete=models.CASCADE,
    )
    sib_order = models.PositiveIntegerField()
    related = models.ForeignKey(RelatedModel, on_delete=models.CASCADE)


class AL_TestNodeInherited(AL_TestNode):
    extra_desc = models.CharField(max_length=255)


class MP_TestNodeSorted(MP_Node, DescMixin):
    steplen = 1
    node_order_by = ["val1", "val2", "desc"]
    val1 = models.IntegerField()
    val2 = models.IntegerField()


class NS_TestNodeSorted(NS_Node, DescMixin):
    node_order_by = ["val1", "val2", "desc"]
    val1 = models.IntegerField()
    val2 = models.IntegerField()


class AL_TestNodeSorted(AL_Node, DescMixin):
    parent = models.ForeignKey(
        "self",
        related_name="children_set",
        null=True,
        db_index=True,
        on_delete=models.CASCADE,
    )
    node_order_by = ["val1", "val2", "desc"]
    val1 = models.IntegerField()
    val2 = models.IntegerField()


class MP_TestNodeAlphabet(MP_Node):
    steplen = 2
    numval = models.IntegerField()


class MP_TestNodeSmallStep(MP_Node):
    steplen = 1
    alphabet = "0123456789"


class MP_TestNodeSortedAutoNow(MP_Node, DescMixin):
    created = models.DateTimeField(auto_now_add=True)
    node_order_by = ["created"]


class MP_TestNodeShortPath(MP_Node, DescMixin):
    steplen = 1
    alphabet = "012345678"


class MP_TestNodeUuid(MP_Node, DescMixin):
    steplen = 1
    custom_id = models.UUIDField(primary_key=True, default=uuid.uuid1, editable=False)


# This is how you change the default fields defined in a Django abstract class
# (in this case, MP_Node), since Django doesn't allow overriding fields, only
# mehods and attributes
MP_TestNodeShortPath._meta.get_field("path").max_length = 4


class MP_TestNode_Proxy(MP_TestNode):
    class Meta:
        proxy = True


class NS_TestNode_Proxy(NS_TestNode):
    class Meta:
        proxy = True


class AL_TestNode_Proxy(AL_TestNode):
    class Meta:
        proxy = True


class MP_TestSortedNodeShortPath(MP_Node, DescMixin):
    steplen = 1
    alphabet = "012345678"
    node_order_by = ["desc"]


MP_TestSortedNodeShortPath._meta.get_field("path").max_length = 4


BASE_MODELS = [
    AL_TestNode,
    MP_TestNode,
    NS_TestNode,
    MP_TestNodeUuid,
    MP_TestNodeCustomId,
]

PROXY_MODELS = [AL_TestNode_Proxy, MP_TestNode_Proxy, NS_TestNode_Proxy]
SORTED_MODELS = [AL_TestNodeSorted, MP_TestNodeSorted, NS_TestNodeSorted]
MP_SHORTPATH_MODELS = [MP_TestNodeShortPath, MP_TestSortedNodeShortPath]
RELATED_MODELS = [AL_TestNodeRelated, MP_TestNodeRelated, NS_TestNodeRelated]

# Pairs of dependent models and base models that they depend on
DEP_MODELS = [(AL_TestNode, AL_TestNodeSomeDep), (MP_TestNode, MP_TestNodeSomeDep), (NS_TestNode, NS_TestNodeSomeDep)]

# Pairs of base models and models that inherit from them
INHERITED_MODELS = [
    (AL_TestNode, AL_TestNodeInherited),
    (MP_TestNode, MP_TestNodeInherited),
    (NS_TestNode, NS_TestNodeInherited),
]

if os.environ.get("DATABASE_ENGINE", "") == "psql":

    class LT_TestNode(LT_Node, DescMixin): ...

    class LT_TestNode_Proxy(LT_TestNode):
        class Meta:
            proxy = True

    class LT_TestNodeSorted(LT_Node, DescMixin):
        node_order_by = ["val1", "val2", "desc"]
        val1 = models.IntegerField()
        val2 = models.IntegerField()

    class LT_TestNodeInherited(LT_TestNode):
        extra_desc = models.CharField(max_length=255)

    class LT_TestNodeSomeDep(models.Model):
        node = models.ForeignKey(LT_TestNode, on_delete=models.CASCADE)

    BASE_MODELS.append(LT_TestNode)
    PROXY_MODELS.append(LT_TestNode_Proxy)
    DEP_MODELS.append((LT_TestNode, LT_TestNodeSomeDep))
    INHERITED_MODELS.append((LT_TestNode, LT_TestNodeInherited))
    SORTED_MODELS.append(LT_TestNodeSorted)
