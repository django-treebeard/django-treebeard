"""Django settings for testing treebeard"""

import random
import string

import os


def get_db_conf():
    conf, options = {}, {}
    for name in ('ENGINE', 'NAME', 'USER', 'PASSWORD', 'HOST', 'PORT'):
        conf[name] = os.environ.get('DATABASE_' + name, '')
    engine = conf['ENGINE']
    if engine == '':
        engine = 'sqlite3'
    elif engine in ('pgsql', 'postgres', 'postgresql', 'psycopg2'):
        engine = 'postgresql_psycopg2'
    if '.' not in engine:
        engine = 'django.db.backends.' + engine
    conf['ENGINE'] = engine
    test_name = None

    if engine == 'django.db.backends.sqlite3':
        test_name = conf['NAME'] = ':memory:'
    elif engine in ('django.db.backends.mysql',
                    'django.db.backends.postgresql_psycopg2'):
        if not conf['NAME']:
            conf['NAME'] = 'treebeard'

        # randomizing the test db name,
        # so we can safely run multiple
        # tests at the same time
        test_name = "test_%s_%s" % (
            conf['NAME'],
            ''.join(random.choice(string.ascii_letters) for _ in range(15))
        )

        if conf['USER'] == '':
            conf['USER'] = {
                'django.db.backends.mysql': 'root',
                'django.db.backends.postgresql_psycopg2': 'postgres'
            }[engine]
        if engine == 'django.db.backends.mysql':
            conf['OPTIONS'] = {
                'init_command': 'SET character_set_connection=utf8,'
                                'collation_connection=utf8_unicode_ci'}
    set_test_db_name(conf, test_name)
    return conf


def set_test_db_name(conf, test_name):
    if test_name:
        from django import VERSION
        if VERSION >= (1, 7):
            conf['TEST'] = {'NAME': test_name}
        else:
            conf['TEST_NAME'] = test_name



DATABASES = {'default': get_db_conf()}
SECRET_KEY = '7r33b34rd'


class DisableMigrations(object):

    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return "notmigrations"


MIGRATION_MODULES = DisableMigrations()

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.messages',
    'treebeard',
    'treebeard.tests']

MIDDLEWARE_CLASSES = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware'
]

ROOT_URLCONF = 'treebeard.tests.urls'
