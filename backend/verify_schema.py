import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect('postgresql://postgres:hamsaRaju%4012@localhost:5432/workforce_test')
    
    # Tables exist
    tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public';")
    print("Tables:", [t['tablename'] for t in tables])
    
    # Geography columns
    cols = await conn.fetch("SELECT column_name, data_type, udt_name FROM information_schema.columns WHERE table_name = 'attendance_records';")
    for c in cols:
        if 'location' in c['column_name']:
            print(f"Col: {c['column_name']} Type: {c['data_type']} UDT: {c['udt_name']}")
    
    # Foreign Keys
    fks = await conn.fetch('''
    SELECT
        tc.table_name, kcu.column_name,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_name IN ('attendance_records', 'exception_flags');
    ''')
    for fk in fks:
        print(f"FK: {fk['table_name']}.{fk['column_name']} -> {fk['foreign_table_name']}.{fk['foreign_column_name']}")
        
    # Unique Constraints
    ucs = await conn.fetch('''
    SELECT
        tc.table_name, kcu.column_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
    WHERE tc.constraint_type = 'UNIQUE'
      AND tc.table_name = 'attendance_records';
    ''')
    print("Unique Constraints on attendance_records:", ucs)
    
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
