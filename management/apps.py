from django.apps import AppConfig


class ManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "management"

    def ready(self):
        import management.signals  # noqa: F401

        # Optimize SQLite with PRAGMAs on every new connection
        from django.db.backends.signals import connection_created

        def _set_sqlite_pragmas(sender, connection, **kwargs):
            if connection.vendor == 'sqlite':
                cursor = connection.cursor()
                cursor.execute('PRAGMA journal_mode=WAL;')
                cursor.execute('PRAGMA synchronous=NORMAL;')
                cursor.execute('PRAGMA cache_size=-20000;')
                cursor.execute('PRAGMA busy_timeout=5000;')
                cursor.execute('PRAGMA temp_store=MEMORY;')
                cursor.execute('PRAGMA mmap_size=268435456;')

        connection_created.connect(_set_sqlite_pragmas)
