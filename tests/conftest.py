"""Pytest configuration file"""

import os

import pytest

os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings"

import django
from django.apps import apps
from django.db import connection
from django.db.models.signals import pre_migrate


def pytest_report_header(config):
    return "Django: " + django.get_version()


def pytest_configure(config):
    django.setup()


def _pre_migration(*args, **kwargs):
    if os.environ.get("DATABASE_ENGINE", "") == "psql":
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS ltree;")


@pytest.fixture(autouse=True, scope="session")
def django_test_environment(django_test_environment):
    pre_migrate.connect(_pre_migration, sender=apps.get_app_config("treebeard"))
