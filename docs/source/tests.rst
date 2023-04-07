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

.. option:: DATABASE_USER
.. option:: DATABASE_PASSWORD
.. option:: DATABASE_HOST
.. option:: DATABASE_USER_POSTGRES
.. option:: DATABASE_PORT_POSTGRES
.. option:: DATABASE_USER_MYSQL
.. option:: DATABASE_PORT_MYSQL

   Sets the database settings to be used by the test suite. Useful if you
   want to test the same database engine/version you use in production.


tox
---

``django-treebeard`` uses `tox`_ to run the test suite in all the supported
environments - permutations of:

  - Python 3.8 - 3.11
  - Django 3.2, 4.1 and 4.2
  - Sqlite, MySQL, PostgreSQL and MSSQL

This means that there are a lot of permutations, which takes a long time.
If you want to test only one or a few environments, use the `-e`
option in `tox`_, like:

.. code-block:: console

    $ tox -e py39-dj32-postgres


.. _pytest: http://pytest.org/
.. _tox: https://tox.readthedocs.io/en/latest/index.html
