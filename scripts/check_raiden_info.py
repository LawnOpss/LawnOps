import sqlite3
conn = sqlite3.connect('database.db')
c = conn.cursor()

print("=== Raiden's Info ===")

# Get all territories for raiden
c.execute('''
    SELECT tt.territory_name, t.name
    FROM technician_territories tt
    JOIN technicians t ON tt.technician_id = t.id
    WHERE t.name LIKE '%raiden%'
''')
territories = c.fetchall()
print(f"\nTerritories assigned to raiden: {len(territories)}")
for t in territories:
    print(f"  - {t[0]}")

# Check what services table exists
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in c.fetchall()]
print(f"\nTables in database: {tables}")

# Check technician_services if exists
if 'technician_services' in tables:
    c.execute('PRAGMA table_info(technician_services)')
    print(f"\ntechnician_services columns: {[col[1] for col in c.fetchall()]}")
    
    c.execute('''
        SELECT ts.service_type, s.name as location_name
        FROM technician_services ts
        JOIN technicians t ON ts.technician_id = t.id
        JOIN locations s ON ts.location_id = s.id
        WHERE t.name LIKE '%raiden%'
    ''')
    services = c.fetchall()
    print(f"\nServices raiden performs: {len(services)}")
    for s in services:
        print(f"  - {s[0]} at {s[1]}")
else:
    print("\ntechnician_services table does not exist")

# Check services table
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%service%'")
service_tables = c.fetchall()
print(f"\nService-related tables: {[t[0] for t in service_tables]}")

conn.close()
