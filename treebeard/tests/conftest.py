"""Pytest configuration file
"""
import os


import pytest
os.environ['DJANGO_SETTINGS_MODULE'] = 'treebeard.tests.settings'


import django


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass


def pytest_report_header(config):
    return 'Django: ' + django.get_version()


def pytest_configure(config):
    django.setup()
