API
===

.. module:: treebeard.models
.. moduleauthor:: Gustavo Picon <tabo@tabo.pe>

.. inheritance-diagram:: Node
.. autoclass:: Node
  :show-inheritance:

  This is the base class that defines the API of all tree models in this
  library:

     - :class:`treebeard.mp_tree.MP_Node` (materialized path)
     - :class:`treebeard.ns_tree.NS_Node` (nested sets)
     - :class:`treebeard.al_tree.AL_Node` (adjacency list)

  .. warning::

     Please note that ``django-treebeard`` uses Django raw SQL queries for
     some write operations, and raw queries don't update the objects in the
     ORM since it's being bypassed.

     Because of this, if you have a node in memory and plan to use it after a
     tree modification (adding/removing/moving nodes), you need to reload it.

  .. automethod:: Node.add_root

     Example::

        MyNode.add_root(numval=1, strval='abcd')

  .. automethod:: add_child

        Example::

           node.add_child(numval=1, strval='abcd')

  .. automethod:: add_sibling

        Examples::

         node.add_sibling('sorted-sibling', numval=1, strval='abc')

  .. automethod:: delete

        .. note::

           Call our queryset's delete to handle children removal. Subclasses
           will handle extra maintenance.

  .. automethod:: get_tree
  .. automethod:: get_depth

        Example::

           node.get_depth()

  .. automethod:: get_ancestors

        Example::

           node.get_ancestors()

  .. automethod:: get_children

        Example::

           node.get_children()

  .. automethod:: get_children_count

        Example::

            node.get_children_count()

  .. automethod:: get_descendants

        Example::

           node.get_descendants()

  .. automethod:: get_descendant_count

        Example::

           node.get_descendant_count()

  .. automethod:: get_first_child

        Example::

           node.get_first_child()

  .. automethod:: get_last_child

        Example::

           node.get_last_child()

  .. automethod:: get_first_sibling

        Example::

           node.get_first_sibling()

  .. automethod:: get_last_sibling

        Example::

            node.get_last_sibling()

  .. automethod:: get_prev_sibling

        Example::

           node.get_prev_sibling()

  .. automethod:: get_next_sibling

        Example::

           node.get_next_sibling()

  .. automethod:: get_parent

        Example::

           node.get_parent()

  .. automethod:: get_root

        Example::

          node.get_root()

  .. automethod:: get_siblings

        Example::

           node.get_siblings()

  .. automethod:: is_child_of

        Example::

           node.is_child_of(node2)

  .. automethod:: is_descendant_of

        Example::

           node.is_descendant_of(node2)

  .. automethod:: is_sibling_of

        Example::

           node.is_sibling_of(node2)

  .. automethod:: is_root

        Example::

           node.is_root()

  .. automethod:: is_leaf

        Example::

           node.is_leaf()

  .. automethod:: move

        .. note:: The node can be moved under another root node.

        Examples::

           node.move(node2, 'sorted-child')

           node.move(node2, 'prev-sibling')

  .. automethod:: save
  .. automethod:: get_first_root_node

        Example::

           MyNodeModel.get_first_root_node()

  .. automethod:: get_last_root_node

        Example::

           MyNodeModel.get_last_root_node()

  .. automethod:: get_root_nodes

        Example::

           MyNodeModel.get_root_nodes()

  .. automethod:: load_bulk

        .. note::

            Any internal data that you may have stored in your
            nodes' data (:attr:`path`, :attr:`depth`) will be
            ignored.

        .. note::

            If your node model has :attr:`node_order_by` enabled, it will
            take precedence over the order in the structure.

        Example::

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
            MyNodeModel.load_data(data, None)

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

        Example::

           tree = MyNodeModel.dump_bulk()

           branch = MyNodeModel.dump_bulk(node_obj)

  .. automethod:: find_problems
  .. automethod:: fix_tree
  .. automethod:: get_descendants_group_count

        Example::

            # get a list of the root nodes
            root_nodes = MyModel.get_descendants_group_count()

            for node in root_nodes:
                print '%s by %s (%d replies)' % (node.comment, node.author,
                                                 node.descendants_count)

  .. automethod:: get_annotated_list


        Example::

            annotated_list = get_annotated_list()

        With data:

           .. digraph:: get_annotated_list_digraph

              "a";
              "a" -> "ab";
              "ab" -> "aba";
              "ab" -> "abb";
              "ab" -> "abc";
              "a" -> "ac";

        Will return::

            [
                (a,     {'open':True,  'close':[],    'level': 0})
                (ab,    {'open':True,  'close':[],    'level': 1})
                (aba,   {'open':True,  'close':[],    'level': 2})
                (abb,   {'open':False, 'close':[],    'level': 2})
                (abc,   {'open':False, 'close':[0,1], 'level': 2})
                (ac,    {'open':False, 'close':[0],   'level': 1})
            ]

        This can be used with a template like::

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

        .. note:: This method was contributed originally by
                  `Alexey Kinyov <rudi@05bit.com>`_, using an idea borrowed
                  from `django-mptt`.

        .. versionadded:: 1.55
