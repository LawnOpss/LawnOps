import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

print("=== SERVICES TABLE ===")
cursor.execute("SELECT id, name, service_type FROM services WHERE is_active = 1 ORDER BY name")
for row in cursor.fetchall():
    print(f"  ID {row[0]}: {row[1]} (type: {row[2]})")

print("\n=== TREATMENT_PLANS (Grass Types) ===")
cursor.execute("SELECT id, grass_type_name FROM treatment_plans ORDER BY grass_type_name")
for row in cursor.fetchall():
    print(f"  ID {row[0]}: {row[1]}")

conn.close()
