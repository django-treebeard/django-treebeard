from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):
    operations = []
    if settings.DATABASES['default']['ENGINE'] in (
            'django.db.backends.postgresql_psycopg2', 'django.db.backends.postgresql'):
        operations.append(migrations.RunSQL(
            'ALTER TABLE cms_treenode ALTER COLUMN path SET DATA TYPE varchar(255) COLLATE "C"'))
    elif settings.DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':
        operations.append(migrations.RunSQL(
            'ALTER TABLE cms_treenode MODIFY path VARCHAR(255) COLLATE ascii_general_ci'))
    elif settings.DATABASES['default']['ENGINE'] == 'django.db.backends.oracle':
        operations.append(migrations.RunSQL(
            'ALTER TABLE cms_treenode MODIFY (path VARCHAR2(255) COLLATE BINARY_CI)'))
