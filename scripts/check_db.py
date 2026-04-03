import sqlite3
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

print("=== All treatment_plans for location_id=3 (Georgia) ===")
cursor.execute("SELECT id, grass_type_name, location_id FROM treatment_plans WHERE location_id = 3")
for row in cursor.fetchall():
    print(f"  ID: {row[0]}, Name: '{row[1]}', Location: {row[2]}")

print("\n=== All treatment_plans with 'Bermuda' in name ===")
cursor.execute("SELECT id, grass_type_name, location_id FROM treatment_plans WHERE grass_type_name LIKE '%Bermuda%'")
for row in cursor.fetchall():
    print(f"  ID: {row[0]}, Name: '{row[1]}', Location: {row[2]}")

print("\n=== ALL treatment_plans in database ===")
cursor.execute("SELECT id, grass_type_name, location_id FROM treatment_plans ORDER BY location_id, grass_type_name")
for row in cursor.fetchall():
    print(f"  ID: {row[0]}, Name: '{row[1]}', Location: {row[2]}")

conn.close()
