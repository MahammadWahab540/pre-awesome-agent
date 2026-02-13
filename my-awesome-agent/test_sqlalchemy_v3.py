
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

async def test():
    async def get_conn():
        # Dummy connection function
        return None

    try:
        # Exact pattern from fast_api_app.py for Cloud SQL
        url = "mysql+aiomysql://"
        print(f"Testing partial URL with async_creator: {url}")
        engine = create_async_engine(url, async_creator=get_conn)
        print("Engine created successfully.")
        
        print(f"Dialect: {engine.dialect.name}")
        print(f"Driver: {engine.dialect.driver}")
        
    except Exception as e:
        print(f"Caught exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
