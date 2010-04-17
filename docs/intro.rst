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

1. Run :command:`easy_install django-treebeard` to install the
   `latest treebeard version from PyPi`_

   1.1. If you don't like easy_install, download a release from the
   `treebeard download page`_ or get a development version
   from the `treebeard mercurial repository`_ and run
   :command:`python setup.py install`
2. Add ``'treebeard'`` to the ``INSTALLED_APPS`` section in your
   django settings file.
3. Create a new model that inherits from one of ``django-treebeard``'s
   abstract tree models: :class:`MP_Node <treebeard.mp_tree.MP_Node>`
   (materialized path), :class:`NS_Node <treebeard.ns_tree.NS_Node>`
   (nested sets) or :class:`AL_Node <treebeard.al_tree.AL_Node>`
   (adjacency list).
4. Run :command:`python manage.py syncdb`


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

