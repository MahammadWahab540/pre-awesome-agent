import asyncio
import os
import logging
from google.cloud.sql.connector import Connector
import pymysql

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Manual smoke check for Cloud SQL connector."""
    instance_connection_name = os.getenv("CLOUD_SQL_CONNECTION_NAME", "project:region:instance")
    db_user = os.getenv("DB_USER", "user")
    db_pass = os.getenv("DB_PASS", "pass")
    db_name = os.getenv("DB_NAME", "db")

    logger.info(f"🔍 Testing Cloud SQL Connector for {instance_connection_name}")
    
    # Initialize connector
    connector = Connector()

    try:
        # We expect this to fail in local environments without a running Cloud SQL Proxy or Auth
        # but we want to catch specific connection errors, not broad exceptions.
        conn = connector.connect(
            instance_connection_name,
            "pymysql",
            user=db_user,
            password=db_pass,
            db=db_name
        )
        conn.close()
        logger.info("✅ Successfully connected to Cloud SQL!")
    except (pymysql.err.OperationalError, ValueError) as e:
        logger.info(f"ℹ️ Expected connection failure (safe to ignore if local): {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error during connector test: {type(e).__name__}: {e}")
        raise
    finally:
        connector.close()

if __name__ == "__main__":
    asyncio.run(main())
