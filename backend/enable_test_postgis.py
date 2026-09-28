import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect('postgresql://postgres:hamsaRaju%4012@localhost:5432/workforce_test_test')
    await conn.execute('CREATE EXTENSION IF NOT EXISTS postgis;')
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
