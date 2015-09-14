import os
import sys
import time


os.environ['DJANGO_SETTINGS_MODULE'] = 'treebeard.tests.settings'

import django
from django.conf import settings
from django.test.utils import (setup_test_environment,
                               teardown_test_environment)
from django.test.client import Client
from django.core.management import call_command
from django.core import mail
from django.db import connection


def pytest_report_header(config):
    return 'Django: ' + django.get_version()


def pytest_configure(config):
    if django.VERSION >= (1, 7):
        django.setup()
    setup_test_environment()
    connection.creation.create_test_db(verbosity=2, autoclobber=True)


def pytest_unconfigure(config):
    dbsettings = settings.DATABASES['default']
    if django.VERSION >= (1, 7):
        dbtestname = dbsettings['TEST']['NAME']
    else:
        dbtestname = dbsettings['TEST_NAME']
    connection.close()
    if dbsettings['ENGINE'].split('.')[-1] == 'postgresql_psycopg2':
        connection.connection = None
        connection.settings_dict['NAME'] = dbtestname.split('_')[1]
        cursor = connection.cursor()
        connection.autocommit = True
        if django.VERSION < (1, 6):
            connection._set_isolation_level(0)
        else:
            connection._set_autocommit(True)
        time.sleep(1)
        sys.stdout.write(
            "Destroying test database for alias '%s' (%s)...\n" % (
                connection.alias, dbtestname)
        )
        sys.stdout.flush()
        cursor.execute(
            'DROP DATABASE %s' % connection.ops.quote_name(dbtestname))
    else:
        connection.creation.destroy_test_db(dbtestname, verbosity=2)
    teardown_test_environment()


def pytest_funcarg__client(request):
    def setup():
        mail.outbox = []
        return Client()

    def teardown(client):
        call_command('flush', verbosity=0, interactive=False)

    return request.cached_setup(setup, teardown, 'function')
