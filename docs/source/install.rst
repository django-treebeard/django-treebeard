Installation
============


Prerequisites
-------------

``django-treebeard`` needs at least **Python 2.7/3.4** to run, and
**Django 1.8 or later**.


Installing
----------

You have several ways to install ``django-treebeard``. If you're not sure,
`just use pip <http://guide.python-distribute.org/pip.html>`_

pip (or easy_install)
~~~~~~~~~~~~~~~~~~~~~

You can install the release versions from
`django-treebeard's PyPI page`_ using ``pip``:

.. code-block:: console

  $ pip install django-treebeard

or if for some reason you can't use ``pip``, you can try ``easy_install``,
(at your own risk):

.. code-block:: console

  $ easy_install --always-unzip django-treebeard


setup.py
~~~~~~~~

Download a release from the `treebeard download page`_ and unpack it, then
run:

.. code-block:: console

   $ python setup.py install


.deb packages
~~~~~~~~~~~~~

Both Debian and Ubuntu include ``django-treebeard`` as a package, so you can
just use:

.. code-block:: console

   $ apt-get install python-django-treebeard

or:

.. code-block:: console

   $ aptitude install python-django-treebeard

Remember that the packages included in linux distributions are usually not the
most recent versions.


Configuration
-------------

Add ``'treebeard'`` to the
:django:setting:`INSTALLED_APPS` section in your django
settings file.

.. note::

   If you are going to use the :class:`~treebeard.admin.TreeAdmin`
   class, you need to add the path to treebeard's templates in
   :django:setting:`TEMPLATE_DIRS`.
   Also you need to add
   ``django.template.context_processors.request``
   to :django:setting:`TEMPLATES['OPTIONS']['contxt_processors']`
   setting in your django settings file (see https://docs.djangoproject.com/en/1.11/ref/templates/upgrading/ for how to define this setting within the TEMPLATES settings). For more recent versions of Django, use ``django.core.context_processors.request`` instead.


.. _`django-treebeard's PyPI page`:
   https://pypi.org/project/django-treebeard/

