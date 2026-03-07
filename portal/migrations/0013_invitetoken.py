from django.db import migrations, models
import django.db.models.deletion


def _create_invitetoken_table_if_missing(apps, schema_editor):
    table_name = 'portal_invitetoken'
    existing = set(schema_editor.connection.introspection.table_names())
    if table_name in existing:
        return

    vendor = schema_editor.connection.vendor
    if vendor == 'postgresql':
        schema_editor.execute(
            """
            CREATE TABLE portal_invitetoken (
                id BIGSERIAL PRIMARY KEY,
                token VARCHAR(128) NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                used BOOLEAN NOT NULL DEFAULT FALSE,
                used_at TIMESTAMPTZ NULL,
                employee_id BIGINT NOT NULL
                    REFERENCES portal_employee (id)
                    DEFERRABLE INITIALLY DEFERRED
            );
            """
        )
        schema_editor.execute(
            "CREATE INDEX portal_invitetoken_employee_id_idx ON portal_invitetoken (employee_id);"
        )
        return

    # SQLite / fallback path for local and other simple engines.
    schema_editor.execute(
        """
        CREATE TABLE portal_invitetoken (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token VARCHAR(128) NOT NULL UNIQUE,
            created_at DATETIME NOT NULL,
            expires_at DATETIME NOT NULL,
            used BOOLEAN NOT NULL DEFAULT 0,
            used_at DATETIME NULL,
            employee_id BIGINT NOT NULL
                REFERENCES portal_employee (id)
                DEFERRABLE INITIALLY DEFERRED
        );
        """
    )
    schema_editor.execute(
        "CREATE INDEX portal_invitetoken_employee_id_idx ON portal_invitetoken (employee_id);"
    )


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0012_workzone_employeeworkzone_worksession'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='InviteToken',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('token', models.CharField(db_index=True, max_length=128, unique=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('expires_at', models.DateTimeField()),
                        ('used', models.BooleanField(default=False)),
                        ('used_at', models.DateTimeField(blank=True, null=True)),
                        ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invite_tokens', to='portal.employee')),
                    ],
                ),
            ],
            database_operations=[
                migrations.RunPython(_create_invitetoken_table_if_missing, _noop_reverse),
            ],
        ),
    ]
