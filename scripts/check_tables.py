import sqlite3
conn = sqlite3.connect('d:/python-lawn/database.db')
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
print("Tables in database:")
for row in cursor.fetchall():
    print(f"  - {row[0]}")

# Check for any table with 'territor' in the name
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%territor%'")
print("\nTerritory-related tables:")
for row in cursor.fetchall():
    print(f"  - {row[0]}")
    
conn.close()
