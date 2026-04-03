import sqlite3
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

print("=== treatment_plans table schema ===")
cursor.execute("PRAGMA table_info(treatment_plans)")
for row in cursor.fetchall():
    print(f"  {row}")

print("\n=== Indexes on treatment_plans ===")
cursor.execute("PRAGMA index_list(treatment_plans)")
for row in cursor.fetchall():
    print(f"  {row}")
    # Get index info
    cursor.execute(f"PRAGMA index_info({row[1]})")
    for idx_row in cursor.fetchall():
        print(f"    Column: {idx_row}")

print("\n=== Try to insert Bermuda for location 3 ===")
try:
    cursor.execute(
        "INSERT INTO treatment_plans (grass_type_name, location_id) VALUES (?, ?)",
        ("Bermuda", 3)
    )
    conn.commit()
    print(f"SUCCESS! Inserted with ID: {cursor.lastrowid}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

conn.close()
