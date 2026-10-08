"""Container start-up tasks, run before Uvicorn (see the Dockerfile CMD):

1. wait for PostgreSQL to accept connections (it may still be booting),
2. apply Alembic migrations (`alembic upgrade head`),
3. optionally load demo data into an empty database.
"""

import logging
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from .config import settings
from .db import engine
from .seed import seed_demo_data

log = logging.getLogger("stockpilot.prestart")
ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def wait_for_database(timeout_seconds: int, interval_seconds: float = 2.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    attempt = 0
    while True:
        attempt += 1
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            log.info("database reachable after %d attempt(s)", attempt)
            return
        except OperationalError as exc:
            if time.monotonic() >= deadline:
                log.error("database still unreachable after %ss, giving up", timeout_seconds)
                raise
            log.warning("database not ready yet (%s), retrying in %ss", exc.__class__.__name__, interval_seconds)
            time.sleep(interval_seconds)


def run_migrations() -> None:
    log.info("applying database migrations")
    config = Config(str(ALEMBIC_INI))
    config.attributes["configure_logger"] = False  # keep the logging set up in main()
    command.upgrade(config, "head")


def main() -> None:
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    wait_for_database(settings.db_wait_timeout_seconds)
    run_migrations()
    if settings.seed_demo_data:
        seed_demo_data()


if __name__ == "__main__":
    main()
