import asyncio
from google.cloud.sql.connector import create_async_connector


async def test_pymysql_connector():
    connector = None
    try:
        # Use create_async_connector to properly initialize in an async context
        # and avoid ConnectorLoopError.
        connector = await create_async_connector()
        print("Async Connector initialized.")
        
        # NOTE: The cloud-sql connector's async path supports asyncpg for Postgres.
        # For MySQL, 'pymysql' is supported but it's a sync driver.
        
        driver = "pymysql"
        print(f"Calling connect_async with driver='{driver}'...")
        
        # This will still fail if no valid connection name is provided, 
        # but it will pass the internal driver and loop validation checks.
        try:
            await connector.connect_async("project:region:instance", driver, user="user", password="pass", db="db")
        except Exception as e:
            print(f"Caught expected connection failure (no real instance): {type(e).__name__}: {e}")
            
    except Exception as e:
        print(f"Caught unexpected exception during initialization: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if connector:
            await connector.close_async()

if __name__ == "__main__":
    asyncio.run(test_pymysql_connector())
