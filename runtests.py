#!/usr/bin/env python

""" runtests.py runs tests

Read docs/tests for help on how to run the test suite.
"""

import optparse
import os

import coverage

from django.conf import settings
from django.core.management import call_command


def runtests():
    parser = optparse.OptionParser()
    parser.add_option('--verbosity', dest='verbosity', default='1')
    parser.add_option('--coverage', dest='coverage', default='2')
    parser.add_option('--DATABASE_ENGINE', dest='DATABASE_ENGINE',
                      default='sqlite3')
    parser.add_option('--DATABASE_NAME', dest='DATABASE_NAME', default='')
    parser.add_option('--DATABASE_USER', dest='DATABASE_USER', default='')
    parser.add_option('--DATABASE_PASSWORD', dest='DATABASE_PASSWORD',
                      default='')
    parser.add_option('--DATABASE_HOST', dest='DATABASE_HOST', default='')
    parser.add_option('--DATABASE_PORT', dest='DATABASE_PORT', default='')
    options, args = parser.parse_args()

    dboptions = {}
    if options.DATABASE_ENGINE == 'mysql':
        dboptions = {
           "init_command": "SET storage_engine=INNODB,"
                           "character_set_connection=utf8,"
                           "collation_connection=utf8_unicode_ci"}
    if not options.DATABASE_NAME and options.DATABASE_ENGINE != 'sqlite3':
        options.DATABASE_NAME = 'treebeard'
    if not settings.configured:
        settings.configure(
            DATABASE_ENGINE=options.DATABASE_ENGINE,
            DATABASE_NAME=options.DATABASE_NAME,
            DATABASE_USER=options.DATABASE_USER,
            DATABASE_PASSWORD=options.DATABASE_PASSWORD,
            DATABASE_HOST=options.DATABASE_HOST,
            DATABASE_PORT=options.DATABASE_PORT,
            DATABASE_OPTIONS=dboptions,
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.admin',
                'treebeard',
                'treebeard.tests'])

    covlevel = int(options.coverage)
    if covlevel:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if covlevel == 2:
            branch = True
        else:
            branch = False
        cov = coverage.coverage(branch=branch,
                                include=[current_dir + '/treebeard/*.py'],
                                omit=[current_dir + '/treebeard/numconv.py',
                                      current_dir + '/treebeard/tests/*'])
        cov.load()
        cov.start()

    if not args:
        args = ['tests']
    call_command('test', verbosity=options.verbosity, *args)

    if covlevel:
        cov.stop()
        cov.save()


if __name__ == '__main__':
    runtests()
