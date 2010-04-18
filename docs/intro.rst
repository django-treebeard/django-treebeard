Introduction
============

Everything you need to get working quickly.



Prerequisites
-------------

``django-treebeard`` needs at least **Python 2.4** to run, and
**Django 1.0 or better**.


Installation
------------

You have several ways to install ``django-treebeard``. If you're not sure,
`just use pip <http://guide.python-distribute.org/pip.html>`_

pip (or easy_install)
~~~~~~~~~~~~~~~~~~~~~

You can install the release versions from
`django-treebeard's PyPI page`_ using ``pip``::

  pip install django-treebeard

or if for some reason you can't use ``pip``, you can try ``easy_install``,
(at your own risk)::

  easy_install --always-unzip django-treebeard


setup.py
~~~~~~~~

Download a release from the `treebeard download page`_ and unpack it, then
run::

   python setup.py install


.deb packages
~~~~~~~~~~~~~

Both Debian and Ubuntu include ``django-treebeard`` as a package, so you can
just use::

   apt-get install python-django-treebeard

or::

   aptitude install python-django-treebeard

Remember that the packages included in linux distributions are usually not the
most recent versions.


Configuration
-------------

Add ``'treebeard'`` to the `INSTALLED_APPS`_ section in your django settings
file.

.. note::

   If you are going to use the :class:`Treeadmin <treebeard.admin.TreeAdmin>`
   class, you need to add the path to treebeard's templates in
   `TEMPLATE_DIRS`_.
   Also you need to enable `django-core-context-processors-request`_
   in the `TEMPLATE_CONTEXT_PROCESSORS`_ setting in your django settings file.


Basic Usage
-----------

Create a basic model for your tree. In this example we'll use a Materialized
Path tree::

    from django.db import models
    from treebeard.mp_tree import MP_Node

    class Category(MP_Node):
        name = models.CharField(max_length=30)

        node_order_by = ['name']

        def __unicode__(self):
            return 'Category: %s' % self.name



Run syncdb::

    python manage.py syncdb


Let's create some nodes::

    >>> get = lambda node_id: Category.objects.get(pk=node_id)
    >>> root = Category.add_root(name='Computer Hardware')
    >>> node = get(root.id).add_child(name='Memory')
    >>> get(node.id).add_sibling(name='Hard Drives')
    <Category: Category: Hard Drives>
    >>> get(node.id).add_sibling(name='SSD')
    <Category: Category: SSD>
    >>> get(node.id).add_child(name='Desktop Memory')
    <Category: Category: Desktop Memory>
    >>> get(node.id).add_child(name='Laptop Memory')
    <Category: Category: Laptop Memory>
    >>> get(node.id).add_child(name='Server Memory')
    <Category: Category: Server Memory>

.. note::

    Why retrieving every node again after the first operation? Because
    ``django-treebeard`` uses raw queries for most write operations,
    and raw queries don't update the django objects of the db entries they
    modify.

We just created this tree:


.. digraph:: introduction_digraph

  "Computer Hardware";
  "Computer Hardware" -> "Hard Drives";
  "Computer Hardware" -> "Memory";
  "Memory" -> "Desktop Memory";
  "Memory" -> "Laptop Memory";
  "Memory" -> "Server Memory";
  "Computer Hardware" -> "SSD";


You can see the tree structure with code::
    >>> Category.dump_bulk()
    [{'id': 1, 'data': {'name': u'Computer Hardware'},
      'children': [
         {'id': 3, 'data': {'name': u'Hard Drives'}},
         {'id': 2, 'data': {'name': u'Memory'},
          'children': [
             {'id': 5, 'data': {'name': u'Desktop Memory'}},
             {'id': 6, 'data': {'name': u'Laptop Memory'}},
             {'id': 7, 'data': {'name': u'Server Memory'}}]},
         {'id': 4, 'data': {'name': u'SSD'}}]}]
    >>> Category.get_annotated_list()
    [(<Category: Category: Computer Hardware>,
      {'close': [], 'level': 0, 'open': True}),
     (<Category: Category: Hard Drives>,
      {'close': [], 'level': 1, 'open': True}),
     (<Category: Category: Memory>,
      {'close': [], 'level': 1, 'open': False}),
     (<Category: Category: Desktop Memory>,
      {'close': [], 'level': 2, 'open': True}),
     (<Category: Category: Laptop Memory>,
      {'close': [], 'level': 2, 'open': False}),
     (<Category: Category: Server Memory>,
      {'close': [0], 'level': 2, 'open': False}),
     (<Category: Category: SSD>,
      {'close': [0, 1], 'level': 1, 'open': False})]



Read the :class:`treebeard.models.Node` API reference for detailed info.

.. _`django-treebeard's PyPI page`:
   http://pypi.python.org/pypi/django-treebeard
.. _`treebeard download page`:
   http://code.tabo.pe/django-treebeard/downloads/
.. _`treebeard mercurial repository`:
   http://code.tabo.pe/django-treebeard/src/
.. _`latest treebeard version from PyPi`:
   http://pypi.python.org/pypi/django-treebeard/
.. _`django-core-context-processors-request`:
   http://docs.djangoproject.com/en/dev/ref/templates/api/#django-core-context-processors-request
.. _`INSTALLED_APPS`:
   http://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
.. _`TEMPLATE_DIRS`:
   http://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
.. _`TEMPLATE_CONTEXT_PROCESSORS`:
   http://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors

