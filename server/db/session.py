"""SQLite 异步数据库连接与初始化。"""

import os
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from server.db.base import Base

logger = logging.getLogger(__name__)

DATABASE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "database"

_db_name = "onetts_test.db" if os.environ.get("PYTEST_CURRENT_TEST") else "onetts.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_DIR / _db_name}"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"timeout": 30.0},
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """创建所有数据库表并启用 WAL 模式。"""
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        from sqlalchemy import text
        await conn.execute(text("PRAGMA journal_mode=WAL;"))
        await conn.execute(text("PRAGMA busy_timeout=5000;"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("OneTTS 数据库初始化完成: %s", DATABASE_URL)
