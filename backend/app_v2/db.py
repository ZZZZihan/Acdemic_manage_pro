from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def create_session_factory(database_url: str) -> tuple:
    connect_args = {}
    if database_url.startswith('sqlite'):
        connect_args['check_same_thread'] = False

    engine = create_engine(database_url, future=True, connect_args=connect_args)
    session_factory = sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return engine, session_factory
