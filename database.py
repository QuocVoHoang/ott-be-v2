from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os
DATABASE_URL = "postgresql+asyncpg://neondb_owner:npg_LSsi8wP1cUmA@ep-bitter-cloud-a1mre7ly-pooler.ap-southeast-1.aws.neon.tech/neondb"
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session