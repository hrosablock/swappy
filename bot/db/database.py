from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.env import DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True,
    isolation_level="READ COMMITTED",
    pool_size=30,
    max_overflow=50,
    pool_timeout=10,
    pool_recycle=1800,
    pool_pre_ping=True,
    pool_use_lifo=True,
)

async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# async def get_db():
#     async with async_session() as session:
#         yield session
