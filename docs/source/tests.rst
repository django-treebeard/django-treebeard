Running the Test Suite
======================

``django-treebeard`` includes a comprehensive test suite. It is highly
recommended that you run and update the test suite when you send patches.

pytest
------

You will need `pytest`_ to run the test suite:

.. code-block:: console

    $ pip install pytest

Then just run the test suite:

.. code-block:: console

    $ pytest

You can use all the features and plugins of pytest this way.

By default the test suite will run using a sqlite3 database in RAM, but you can
change this setting environment variables:

.. option:: DATABASE_ENGINE
.. option:: DATABASE_NAME
.. option:: DATABASE_USER
.. option:: DATABASE_PASSWORD
.. option:: DATABASE_HOST
.. option:: DATABASE_PORT

   Sets the database settings to be used by the test suite. Useful if you
   want to test the same database engine/version you use in production.


tox
---

``django-treebeard`` uses `tox`_ to run the test suite in all the supported
environments - permutations of:

  - Python 3.6, 3.7 and 3.8
  - Django 2.2, 3.0 and 3.1
  - Sqlite, MySQL and PostgreSQL

This means that the test suite will run 24 times to test every
environment supported by ``django-treebeard``. This takes a long time.
If you want to test only one or a few environments, please use the `-e`
option in `tox`_, like:

.. code-block:: console

    $ tox -e py36-dj22-pgsql


.. _pytest: http://pytest.org/
.. _coverage: http://nedbatchelder.com/code/coverage/
.. _tox: http://codespeak.net/tox/
