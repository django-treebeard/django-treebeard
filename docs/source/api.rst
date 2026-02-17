API
===

.. module:: treebeard.models

.. inheritance-diagram:: Node
.. autoclass:: Node
  :show-inheritance:

  This is the base class that all tree models in this library inherit from.

  .. warning::

      Please be aware of the :doc:`caveats` when using this library.

  .. automethod:: delete

        .. note::

         Call our queryset's delete to handle children removal. Subclasses
         will handle extra maintenance.

  .. automethod:: get_depth

     Example:

     .. code-block:: python

        node.get_depth()

  .. automethod:: is_child_of

     Example:

     .. code-block:: python

        node.is_child_of(node2)

  .. automethod:: is_descendant_of

     Example:

     .. code-block:: python

        node.is_descendant_of(node2)

  .. automethod:: is_sibling_of

     Example:

     .. code-block:: python

        node.is_sibling_of(node2)

  .. automethod:: is_root

     Example:

     .. code-block:: python

        node.is_root()

  .. automethod:: is_leaf

     Example:

     .. code-block:: python

        node.is_leaf()


.. autoclass:: NodeManager

  This is the base manager class for models subclassing ``Node``.
  It contains the bulk of Treebeard's API for interacting with node objects.

  .. automethod:: add_root

     Example:

     .. code-block:: python

        MyNode.objects.add_root({"numval": 1, "strval"="abcd"})

     Or, to pass in an existing instance:

     .. code-block:: python

        new_node = MyNode(numval=1, strval='abcd')
        MyNode.objects.add_root(instance=new_node)

  .. automethod:: add_child

     Example:

     .. code-block:: python

        MyNode.objects.add_child(node, {"numval": 1, "strval": "abcd"})

     Or, to pass in an existing instance:

     .. code-block:: python

        new_node = MyNode(numval=1, strval='abcd')
        MyNode.objects.add_child(node, instance=new_node)

  .. automethod:: add_sibling

     Examples:

     .. code-block:: python

        MyNode.objects.add_sibling(node, "sorted-sibling", {"numval": 1, "strval": "abc"})

     Or, to pass in an existing instance:

     .. code-block:: python

        new_node = MyNode(numval=1, strval='abc')
        MyNode.objects.add_sibling(node, "sorted-sibling", instance=new_node)

  .. automethod:: move

     .. note:: The node can be moved under another root node.

     Examples:

     .. code-block:: python

        MyNode.objects.move(node, target=node2, pos='sorted-child')
        MyNode.objects.move(node, target=node2, pos='prev-sibling')

  .. automethod:: get_tree

  .. automethod:: get_first_root_node

     Example:

     .. code-block:: python

        MyNodeModel.objects.get_first_root_node()

  .. automethod:: get_last_root_node

     Example:

     .. code-block:: python

        MyNodeModel.objects.get_last_root_node()

  .. automethod:: get_root_nodes

     Example:

     .. code-block:: python

        MyNodeModel.objects.get_root_nodes()

  .. automethod:: get_ancestors

     Example:

     .. code-block:: python

        MyNode.objects.get_ancestors(node)

  .. automethod:: get_children

     Example:

     .. code-block:: python

        MyNode.objects.get_children(node)

  .. automethod:: get_children_count

     Example:

     .. code-block:: python

        MyNode.objects.get_children_count(node)

  .. automethod:: get_descendants

     Example:

     .. code-block:: python

        MyNode.objects.get_descendants(node)

  .. automethod:: get_descendant_count

     Example:

     .. code-block:: python

        MyNode.objects.get_descendant_count(node)

  .. automethod:: get_first_child

     Example:

     .. code-block:: python

        MyNode.objects.get_first_child(node)

  .. automethod:: get_last_child

     Example:

     .. code-block:: python

        MyNode.objects.get_last_child(node)

  .. automethod:: get_first_sibling

     Example:

     .. code-block:: python

        MyNode.objects.get_first_sibling(node)

  .. automethod:: get_last_sibling

     Example:

     .. code-block:: python

        MyNode.objects.get_last_sibling(node)

  .. automethod:: get_prev_sibling

     Example:

     .. code-block:: python

        MyNode.objects.get_prev_sibling(node)

  .. automethod:: get_next_sibling

     Example:

     .. code-block:: python

        MyNode.objects.get_next_sibling(node)

  .. automethod:: get_parent

     Example:

     .. code-block:: python

        MyNode.objects.get_parent(node)

  .. automethod:: get_root

     Example:

     .. code-block:: python

        MyNode.objects.get_root(node)

  .. automethod:: get_siblings

     Example:

     .. code-block:: python

        MyNode.object.get_siblings(node)


  .. automethod:: load_bulk

     .. note::

            Any internal data that you may have stored in your
            nodes' data (:attr:`path`, :attr:`depth`) will be
            ignored.

     .. note::

            If your node model has :attr:`node_order_by` enabled, it will
            take precedence over the order in the structure.

     Example:

     .. code-block:: python

            data = [{'data':{'desc':'1'}},
                    {'data':{'desc':'2'}, 'children':[
                      {'data':{'desc':'21'}},
                      {'data':{'desc':'22'}},
                      {'data':{'desc':'23'}, 'children':[
                        {'data':{'desc':'231'}},
                      ]},
                      {'data':{'desc':'24'}},
                    ]},
                    {'data':{'desc':'3'}},
                    {'data':{'desc':'4'}, 'children':[
                      {'data':{'desc':'41'}},
                    ]},
            ]
            # parent = None
            MyNodeModel.objects.load_bulk(data, None)

     Will create:

     .. digraph:: load_bulk_digraph

           "1";
           "2";
           "2" -> "21";
           "2" -> "22";
           "2" -> "23" -> "231";
           "2" -> "24";
           "3";
           "4";
           "4" -> "41";

  .. automethod:: dump_bulk

     Example:

     .. code-block:: python

        tree = MyNodeModel.objects.dump_bulk()
        branch = MyNodeModel.objects.dump_bulk(node_obj)

  .. automethod:: get_descendants_group_count

     Example:

     .. code-block:: python

            # get a list of the root nodes
            root_nodes = MyModel.get_descendants_group_count()

            for node in root_nodes:
                print '%s by %s (%d replies)' % (node.comment, node.author,
                                                 node.descendants_count)

  .. automethod:: get_annotated_list

     Example:

     .. code-block:: python

        annotated_list = MyModel.objects.get_annotated_list()

     With data:

     .. digraph:: get_annotated_list_digraph

              "a";
              "a" -> "ab";
              "ab" -> "aba";
              "ab" -> "abb";
              "ab" -> "abc";
              "a" -> "ac";

     Will return:

     .. code-block:: python

            [
                (a,     {'open':True,  'close':[],    'level': 0})
                (ab,    {'open':True,  'close':[],    'level': 1})
                (aba,   {'open':True,  'close':[],    'level': 2})
                (abb,   {'open':False, 'close':[],    'level': 2})
                (abc,   {'open':False, 'close':[0,1], 'level': 2})
                (ac,    {'open':False, 'close':[0],   'level': 1})
            ]

     This can be used with a template like:

     .. code-block:: django

            {% for item, info in annotated_list %}
                {% if info.open %}
                    <ul><li>
                {% else %}
                    </li><li>
                {% endif %}

                {{ item }}

                {% for close in info.close %}
                    </li></ul>
                {% endfor %}
            {% endfor %}

     .. note::

        This method was contributed originally by
        `Alexey Kinyov <rudi@05bit.com>`_, using an idea borrowed from
        `django-mptt`_.


  .. automethod:: get_annotated_list_qs


.. _django-mptt: https://github.com/django-mptt/django-mptt/