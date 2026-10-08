"""Guards the Alembic migrations: they must apply and roll back cleanly, and the
schema they produce must match the SQLAlchemy models (no forgotten migration)."""

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.db import Base

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def alembic_config(tmp_path):
    url = f"sqlite+pysqlite:///{(tmp_path / 'migrations.db').as_posix()}"
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["configure_logger"] = False
    return config, url


def test_upgrade_creates_tables_and_downgrade_removes_them(alembic_config):
    config, url = alembic_config
    engine = create_engine(url)

    command.upgrade(config, "head")
    tables = set(inspect(engine).get_table_names())
    assert {"products", "stock_movements", "alembic_version"} <= tables

    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    engine.dispose()


def test_migrations_match_models(alembic_config):
    config, url = alembic_config
    command.upgrade(config, "head")
    engine = create_engine(url)
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert diff == [], f"Models and migrations are out of sync: {diff}"
