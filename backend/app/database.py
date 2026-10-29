from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import DATABASE_URL

# Long-running ingest scripts leave a pooled connection idle for many minutes
# between database calls, and Supabase's pooler drops connections it considers
# idle.  Three settings are needed to survive that, and pool_pre_ping alone is
# not enough:
#
#   pool_pre_ping   validates a pooled connection before handing it out.
#   pool_recycle    discards connections older than this instead of pinging a
#                   corpse — the pooler's own idle timeout is in this range.
#   command_timeout bounds the wait.  Without it asyncpg waits forever, and when
#                   the pooler drops a connection without sending a RST the
#                   socket becomes a black hole: the pre-ping query itself hangs.
#                   The event loop then parks in kevent() with no timeout, which
#                   also means the process stops responding to Ctrl-C. A Gooding
#                   ingest sat in exactly that state for 48 minutes and had to be
#                   SIGKILLed.
#
# 60s is far above any real query here (the heaviest aggregation over ~22k rows
# returns in well under a second), so this only ever fires on a dead connection.
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"command_timeout": 60},
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
