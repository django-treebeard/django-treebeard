Installation
============


Prerequisites
-------------

``django-treebeard`` needs at least **Python 3.10** to run, and **Django 4.2 or later**.


Installing
----------

You can install the release versions from
`django-treebeard's PyPI page`_ using ``pip``:

.. code-block:: console

  $ pip install django-treebeard


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

Add ``'treebeard'`` to the :django:setting:`INSTALLED_APPS` section in your django settings file.

.. _`django-treebeard's PyPI page`:
   https://pypi.org/project/django-treebeard/
