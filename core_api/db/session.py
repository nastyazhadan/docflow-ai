from __future__ import annotations

import os
from typing import AsyncIterator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_engine: Optional[AsyncEngine] = None
_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def init_engine() -> AsyncEngine:
    """
    Инициализирует async SQLAlchemy engine и session_maker один раз на процесс.
    """
    global _engine, _session_maker

    if _engine is not None:
        return _engine

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    _engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
    )
    _session_maker = async_sessionmaker(
        _engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    return _engine


def _get_session_maker() -> async_sessionmaker[AsyncSession]:
    if _session_maker is None:
        init_engine()
    assert _session_maker is not None
    return _session_maker


async def get_db() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency: отдаёт AsyncSession на время запроса.
    """
    session_maker = _get_session_maker()
    async with session_maker() as session:
        yield session


async def check_db_connection() -> None:
    """
    Простой SELECT 1 для проверки доступности БД.
    """
    engine = init_engine()
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def dispose_engine() -> None:
    global _engine, _session_maker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_maker = None
