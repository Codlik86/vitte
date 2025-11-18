from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.engine.url import make_url

from .config import settings


class Base(DeclarativeBase):
    pass


def _build_engine_url():
    url = make_url(settings.database_url)
    # Ensure asyncpg driver and strip unsupported params
    if url.drivername in ("postgresql", "postgres"):
        url = url.set(drivername="postgresql+asyncpg")
    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    # Remove params asyncpg doesn't accept
    query.pop("channel_binding", None)
    query.pop("target_session_attrs", None)
    url = url.set(query=query)
    connect_args = {}
    if sslmode and sslmode.lower() in ("require", "verify-full"):
        connect_args["ssl"] = "require"
    return url, connect_args


url, connect_args = _build_engine_url()
engine = create_async_engine(url, echo=False, future=True, connect_args=connect_args)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
