import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect('postgresql://postgres:hamsaRaju%4012@localhost:5432/workforce_test')
    ver = await conn.fetchval('SELECT version();')
    print("Version:", ver)
    
    postgis_ext = await conn.fetch("SELECT name, default_version FROM pg_available_extensions WHERE name = 'postgis';")
    print("Available PostGIS Ext:", postgis_ext)
    
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
