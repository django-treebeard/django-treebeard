"""
Py.test configuration file

Maik says: There's some magic in here that I don't fully understand. Normally, one would
use pytest-django to run the tests, which takes care of all the Django-related testcase
set up and tear down. But that doesn't work because the current tests attempt to access the
database not just in tests, but in their set up methods, which trips up the
"can't access database without mark.django_db" no matter if tests are marked as being
allowed to access the database or not.

So instead, we run the tests without pytest-django and make it work ourselves.
"""
import os


os.environ['DJANGO_SETTINGS_MODULE'] = 'treebeard.tests.settings'

import django
from django.test.utils import setup_test_environment, teardown_test_environment
from django.db import connection


def pytest_report_header(config):
    return 'Django: ' + django.get_version()


def pytest_configure(config):
    django.setup()
    setup_test_environment()
    connection.creation.create_test_db(verbosity=2, autoclobber=True)


def pytest_unconfigure(config):
    teardown_test_environment()
