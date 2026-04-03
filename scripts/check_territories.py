import sqlite3
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("Tables in database:")
for row in cursor.fetchall():
    print(f"  - {row[0]}")

# Check if technician_territories exists
try:
    cursor.execute("SELECT tt.id, tt.technician_id, t.name, tt.territory_name, tt.center_lat, tt.center_lng, tt.radius_miles, tt.polygon_coords FROM technician_territories tt JOIN technicians t ON tt.technician_id = t.id")
    rows = cursor.fetchall()
    print(f"\nFound {len(rows)} territories:")
    for r in rows:
        print(f"  Territory ID: {r[0]}, Tech ID: {r[1]}, Tech Name: {r[2]}")
        print(f"    Territory: {r[3]}")
        print(f"    Center: ({r[4]}, {r[5]})")
        print(f"    Radius: {r[6]} miles")
        print(f"    Has polygon: {'Yes' if r[7] else 'No'}")
        print()
except sqlite3.OperationalError as e:
    print(f"Error: {e}")

conn.close()
