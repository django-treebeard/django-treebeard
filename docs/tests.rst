Running the Test Suite
======================

``django-treebeard`` includes a comprehensive test suite. It is highly
recommended that you run and update the test suite when you send patches.

py.test
-------

You will need `pytest`_ to run the test suite.

To run the test suite::

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

    - py24-dj12-sqlite
    - py24-dj12-mysql
    - py24-dj12-postgres
    - py24-dj13-sqlite
    - py24-dj13-mysql
    - py24-dj13-postgres
    - py25-dj12-sqlite
    - py25-dj12-mysql
    - py25-dj12-postgres
    - py25-dj13-sqlite
    - py25-dj13-mysql
    - py25-dj13-postgres
    - py26-dj12-sqlite
    - py26-dj12-mysql
    - py26-dj12-postgres
    - py26-dj13-sqlite
    - py26-dj13-mysql
    - py26-dj13-postgres
    - py27-dj12-sqlite
    - py27-dj12-mysql
    - py27-dj12-postgres
    - py27-dj13-sqlite
    - py27-dj13-mysql
    - py27-dj13-postgres


This means that the test suite will run 24 times to test every
environment supported by ``django-treebeard``. This takes a long time.
If you want to test only one or a few environments, please use the `-e`
option in `tox`_, like::

    $ tox -e py27-dj13-postgres


.. _verbosity level:
.. _pytest: http://pytest.org/
   http://docs.djangoproject.com/en/dev/ref/django-admin/#django-admin-option---verbosity
.. _coverage: http://nedbatchelder.com/code/coverage/
.. _tox: http://codespeak.net/tox/
