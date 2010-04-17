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


Now run syncdb::

    python manage.py syncdb


Now you can use your tree to store or retrieve data::

    >>> Category.add_root(name='Computer Hardware')
    <Category: Category object>
                             
    >>> Category.objects.all()
    [<Category: Category object>]



Read the :class:`models.Node` API reference for detailed info.

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

