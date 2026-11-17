from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql+psycopg://app:app@localhost:5432/abandoned_luggage")


def make_engine(url: str | None = None):
    value = url or database_url()
    connect_args = {"connect_timeout": 3} if value.startswith("postgresql") else {}
    return create_engine(value, pool_pre_ping=True, connect_args=connect_args)


@contextmanager
def session_scope(url: str | None = None) -> Iterator[Session]:
    session = sessionmaker(bind=make_engine(url), expire_on_commit=False)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def database_ready(url: str | None = None) -> bool:
    try:
        with make_engine(url).connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
