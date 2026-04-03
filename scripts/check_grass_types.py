import sqlite3
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
print("Tables in database:")
for (table,) in tables:
    print(f"  - {table}")

# Check if locations table exists
if any(t[0] == 'locations' for t in tables):
    print("\n\nLocations table columns:")
    cursor.execute("PRAGMA table_info(locations)")
    for row in cursor.fetchall():
        print(f"  - {row[1]} ({row[2]})")
        
    print("\n\nAll locations:")
    cursor.execute("SELECT id, name FROM locations")
    for row in cursor.fetchall():
        print(f"  ID {row[0]}: {row[1]}")

# Check if treatment_plans table exists  
if any(t[0] == 'treatment_plans' for t in tables):
    print("\n\nTreatment plans table columns:")
    cursor.execute("PRAGMA table_info(treatment_plans)")
    for row in cursor.fetchall():
        print(f"  - {row[1]} ({row[2]})")
        
    print("\n\nAll grass types:")
    cursor.execute("SELECT id, grass_type_name, location_id FROM treatment_plans")
    for row in cursor.fetchall():
        print(f"  ID {row[0]}: {row[1]} (Location ID: {row[2]})")

conn.close()
