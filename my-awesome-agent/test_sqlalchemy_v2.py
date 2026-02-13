
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import make_url

async def test():
    url = "mysql+aiomysql://user:pass@localhost/db"
    print(f"Testing URL: {url}")
    try:
        engine = create_async_engine(url)
        print("Engine created.")
        
        dialect = engine.dialect
        print(f"Dialect: {dialect.name}")
        print(f"Driver: {dialect.driver}")
        
        # Try to load the dialect class explicitly
        u = make_url(url)
        cls = u.get_dialect()
        print(f"Dialect class loaded: {cls}")
        
    except Exception as e:
        print(f"Caught exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
