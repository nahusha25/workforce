import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect('postgresql://postgres:hamsaRaju%4012@localhost:5432/workforce_test')
    
    # Verify postgis available
    ext = await conn.fetch("SELECT name, default_version FROM pg_available_extensions WHERE name = 'postgis';")
    print("Available PostGIS Ext:", ext)
    
    # Enable postgis
    await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    
    # Verify version
    pg_ver = await conn.fetchval("SELECT PostGIS_Version();")
    print("PostGIS Version:", pg_ver)
    
    # Verify extension created
    ext_created = await conn.fetch("SELECT extname FROM pg_extension WHERE extname = 'postgis';")
    print("Created Extension:", ext_created)
    
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
