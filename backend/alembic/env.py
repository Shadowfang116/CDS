from logging.config import fileConfig
from pathlib import Path
import os
import socket
import sys
from typing import Dict

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import make_url

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.base import Base
from app.core.config import settings
from app.models import Org, User, UserOrgRole, Case, AuditLog, Document, DocumentPage, CaseDossierField, Exception_, ConditionPrecedent, ExceptionEvidenceRef, RuleRun, Export, Verification, VerificationEvidenceRef  # Import to register models

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _load_root_env_file() -> Dict[str, str]:
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return {}

    loaded: Dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        loaded[key] = value
    return loaded


ROOT_ENV = _load_root_env_file()


def _get_setting(name: str, default: str) -> str:
    return os.getenv(name) or ROOT_ENV.get(name) or default


def _resolve_host(host: str) -> str:
    if host != "db":
        return host
    try:
        socket.gethostbyname("db")
        return host
    except OSError:
        return "localhost"


def _build_default_database_url() -> str:
    user = _get_setting("POSTGRES_USER", settings.POSTGRES_USER)
    password = _get_setting("POSTGRES_PASSWORD", settings.POSTGRES_PASSWORD.get_secret_value())
    database = _get_setting("POSTGRES_DB", settings.POSTGRES_DB)
    port = _get_setting("POSTGRES_PORT", str(settings.POSTGRES_PORT))
    host = _resolve_host(_get_setting("POSTGRES_HOST", settings.POSTGRES_HOST))
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"


def _get_alembic_database_url() -> str:
    database_url = os.getenv("DATABASE_URL") or ROOT_ENV.get("DATABASE_URL")
    if not database_url:
        return _build_default_database_url()

    parsed = make_url(database_url)
    if parsed.host == "db":
        parsed = parsed.set(host=_resolve_host("db"))
    return parsed.render_as_string(hide_password=False)


ALEMBIC_DATABASE_URL = _get_alembic_database_url()
config.set_main_option("sqlalchemy.url", ALEMBIC_DATABASE_URL)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = ALEMBIC_DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    url = ALEMBIC_DATABASE_URL
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

