import sqlite3
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Check if the new table structure exists
cursor.execute("PRAGMA table_info(treatment_plans)")
print("Table structure:")
for row in cursor.fetchall():
    print(f"  {row}")

# Check indexes
cursor.execute("PRAGMA index_list(treatment_plans)")
print("\nIndexes:")
for row in cursor.fetchall():
    print(f"  {row}")

# Check all data
print("\nAll treatment plans:")
cursor.execute("SELECT id, grass_type_name, location_id FROM treatment_plans")
for row in cursor.fetchall():
    print(f"  ID:{row[0]} '{row[1]}' Location:{row[2]}")

conn.close()
