Running the Test Suite
======================

``django-treebeard`` includes a comprehensive test suite. It is highly
recommended that you run and update the test suite when you send patches.

py.test
-------

You will need `pytest`_ to run the test suite. It's included with the
development dependencies:

.. code-block:: console

    $ pip install -r requirements.txt

Then just run the test suite:

.. code-block:: console

    $ py.test

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
environments:

    - py27-dj16-sqlite
    - py27-dj16-mysql
    - py27-dj16-pgsql
    - py27-dj17-sqlite
    - py27-dj17-mysql
    - py27-dj17-pgsql
    - py34-dj16-sqlite
    - py34-dj16-pgsql
    - py34-dj17-sqlite
    - py34-dj17-pgsql

This means that the test suite will run 10 times to test every
environment supported by ``django-treebeard``. This takes a long time.
If you want to test only one or a few environments, please use the `-e`
option in `tox`_, like:

.. code-block:: console

    $ tox -e py34-dj17-pgsql


.. _pytest: http://pytest.org/
.. _coverage: http://nedbatchelder.com/code/coverage/
.. _tox: http://codespeak.net/tox/
