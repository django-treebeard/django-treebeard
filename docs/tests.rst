Running the Test Suite
======================

``django-treebeard`` includes a comprehensive test suite. It is highly
recommended that you run and update the test suite when you send patches.

runtests.py
-----------

The :program:`runtests.py` script runs the test suite.
It is called like this::

    $ ./runtests.py [options] [appname ...]

If no arguments are given to the script, the test suite will run using a
sqlite3 database in RAM.

The :program:`runtests.py` script has several options:

.. option:: --verbosity

   Sets the `verbosity level`_ that will be passed to the Django test runner.

.. option:: --coverage

   Sets the `coverage`_ level that will be used when analizing the test run.

     - 0 means no coverage
     - 1 means lines coverage
     - 2 means lines and branch coverage

.. option:: --DATABASE_ENGINE
.. option:: --DATABASE_NAME
.. option:: --DATABASE_USER
.. option:: --DATABASE_PASSWORD
.. option:: --DATABASE_HOST
.. option:: --DATABASE_PORT

   Sets the database settings to be used by the test suite. Useful if you
   want to test the same database engine/version you use in production.


tox
---

``django-treebeard`` uses `tox`_ to run the test suite in all the supported
environments:

    - py24django10
    - py24django11
    - py24django12
    - py24django13
    - py25django10
    - py25django11
    - py25django12
    - py25django13
    - py26django10
    - py26django11
    - py26django12
    - py26django13
    - py27django10
    - py27django11
    - py27django12
    - py27django13

In every environment listed, the test suite will run three times:

    1. SQLite
    2. MySQL with InnoDB storage. MyISAM is **NOT** supported.
    3. PostgreSQL

This means that the test suite will run **16*3=48** times to test every
environment supported by ``django-treebeard``. If you want to test only
one or a few environments, please read the `tox`_ documentation.

.. warning::

   Running the test suite 48 times like I do::

     $ coverage erase && time tox && coverage html && open htmlcov/index.html
   
   takes **50 minutes** in an early 2009 MacBook Pro.


.. _verbosity level:
   http://docs.djangoproject.com/en/dev/ref/django-admin/#django-admin-option---verbosity
.. _coverage: http://nedbatchelder.com/code/coverage/
.. _tox: http://codespeak.net/tox/
