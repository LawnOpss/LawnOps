import sqlite3

# Check database structure
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# List all tables
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
print('Tables:', [t[0] for t in tables])

# Check if service_schedule table exists
if any('service_schedule' in t for t in tables):
    cursor.execute('PRAGMA table_info(service_schedule)')
    columns = cursor.fetchall()
    print('service_schedule columns:', [col[1] for col in columns])

conn.close()
