"""Database client and connection management."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import get_settings


# Create engines
_pg_engine = None
_mz_engine = None
_pg_session_factory = None
_mz_session_factory = None


def get_pg_engine():
    """Get or create PostgreSQL engine."""
    global _pg_engine
    if _pg_engine is None:
        settings = get_settings()
        _pg_engine = create_async_engine(
            settings.pg_dsn,
            echo=settings.log_level == "DEBUG",
            pool_size=5,
            max_overflow=10,
        )
    return _pg_engine


def get_mz_engine():
    """Get or create Materialize engine."""
    global _mz_engine
    if _mz_engine is None:
        settings = get_settings()
        _mz_engine = create_async_engine(
            settings.mz_dsn,
            echo=settings.log_level == "DEBUG",
            pool_size=5,
            max_overflow=10,
        )
    return _mz_engine


def get_pg_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get PostgreSQL session factory."""
    global _pg_session_factory
    if _pg_session_factory is None:
        _pg_session_factory = async_sessionmaker(
            get_pg_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _pg_session_factory


def get_mz_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get Materialize session factory."""
    global _mz_session_factory
    if _mz_session_factory is None:
        _mz_session_factory = async_sessionmaker(
            get_mz_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _mz_session_factory


@asynccontextmanager
async def get_pg_session() -> AsyncGenerator[AsyncSession, None]:
    """Get PostgreSQL session context manager."""
    factory = get_pg_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_mz_session() -> AsyncGenerator[AsyncSession, None]:
    """Get Materialize session context manager."""
    factory = get_mz_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def close_connections():
    """Close all database connections."""
    global _pg_engine, _mz_engine
    if _pg_engine:
        await _pg_engine.dispose()
        _pg_engine = None
    if _mz_engine:
        await _mz_engine.dispose()
        _mz_engine = None
