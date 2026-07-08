"""
Test-DB bootstrap for the unmanaged (managed=False) warehouse models.

Django's migrations don't own this schema in production (sql/02_schema.sql
does), so the test database has no tables to run models against unless we
load that same DDL. Reusing sql/02_schema.sql instead of hand-writing a
parallel test schema keeps the test DB and production DB structurally
identical.
"""

from pathlib import Path

import pytest

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "sql" / "02_schema.sql"


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(SCHEMA_PATH.read_text())
