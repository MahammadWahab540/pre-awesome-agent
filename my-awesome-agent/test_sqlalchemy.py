import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine
import asyncio

async def test_dialect():
    try:
        # Just try to create the engine (without connecting)
        engine = create_async_engine("mysql+aiomysql://user:pass@localhost/db")
        print("✅ Dialect mysql+aiomysql is supported")
        await engine.dispose()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_dialect())
