from treebeard.tests import models
from treebeard.forms import MoveNodeForm


class AL_TestNodeForm(MoveNodeForm):
    class Meta:
        model = models.AL_TestNode
        exclude = ['sib_order', 'parent']


class MP_TestNodeForm(MoveNodeForm):
    class Meta:
        model = models.MP_TestNode
        exclude = ['depth', 'numchild', 'path']


class NS_TestNodeForm(MoveNodeForm):
    class Meta:
        model = models.NS_TestNode
        exclude = ['depth', 'lft', 'rgt', 'tree_id']


class AL_TestNodeProxyForm(MoveNodeForm):
    class Meta:
        model = models.AL_TestNode_Proxy
        exclude = ['sib_order', 'parent']


class MP_TestNodeProxyForm(MoveNodeForm):
    class Meta:
        model = models.MP_TestNode_Proxy
        exclude = ['depth', 'numchild', 'path']


class NS_TestNodeProxyForm(MoveNodeForm):
    class Meta:
        model = models.NS_TestNode_Proxy
        exclude = ['depth', 'lft', 'rgt', 'tree_id']
