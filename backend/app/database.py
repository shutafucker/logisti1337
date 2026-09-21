"""SQLite setup kept outside the routing domain."""

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    if database_url.startswith("sqlite:///"):
        database_path = database_url.removeprefix("sqlite:///")
        if database_path and database_path != ":memory:":
            Path(database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
    )
    Base.metadata.create_all(engine)
    if database_url.startswith("sqlite"):
        _migrate_sqlite_schema(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _migrate_sqlite_schema(engine) -> None:
    """Apply the one additive migration needed by local SQLite databases."""
    with engine.begin() as connection:
        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(route_plans)"))
        }
        if "is_current" not in columns:
            connection.execute(
                text("ALTER TABLE route_plans ADD COLUMN is_current BOOLEAN NOT NULL DEFAULT 1")
            )
