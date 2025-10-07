import logging
from logging.config import fileConfig
from flask import current_app
from alembic import context

# Alembic Config
config = context.config
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


def get_engine():
    try:
        # Flask-SQLAlchemy < 3 / Alchemical
        return current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        # Flask-SQLAlchemy >= 3
        return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace('%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


# передаём URL движка в alembic.ini
config.set_main_option('sqlalchemy.url', get_engine_url())
target_db = current_app.extensions['migrate'].db


def get_metadata():
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata


def _is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite:")


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=get_metadata(),
        literal_binds=True,
        render_as_batch=_is_sqlite_url(url),
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode'."""

    # не создавать пустые ревизии при autogenerate
    def process_revision_directives(context_, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    base_conf = current_app.extensions['migrate'].configure_args
    if base_conf.get("process_revision_directives") is None:
        base_conf["process_revision_directives"] = process_revision_directives

    connectable = get_engine()

    with connectable.connect() as connection:
        is_sqlite = connection.dialect.name == "sqlite"

        # Делаем локальную копию, чтобы не мутировать общий dict
        local_conf = dict(base_conf)
        local_conf["render_as_batch"] = is_sqlite
        local_conf.setdefault("compare_type", True)
        local_conf.setdefault("compare_server_default", True)

        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **local_conf
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
