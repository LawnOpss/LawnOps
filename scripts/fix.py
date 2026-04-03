import sqlite3
import os

# Backup first
if os.path.exists('database.db'):
    import shutil
    shutil.copy('database.db', 'database.db.backup')
    print("Backed up database")

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Check current data
cursor.execute("SELECT id, grass_type_name, location_id FROM treatment_plans")
existing_data = cursor.fetchall()
print(f"Existing data: {existing_data}")

# Get full schema
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='treatment_plans'")
print(f"Current CREATE TABLE: {cursor.fetchone()}")

# Drop and recreate properly
cursor.execute("DROP TABLE IF EXISTS treatment_plans")
print("Dropped old table")

cursor.execute("""
    CREATE TABLE treatment_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grass_type_name TEXT NOT NULL,
        location_id INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (location_id) REFERENCES locations (id) ON DELETE CASCADE,
        UNIQUE(grass_type_name, location_id)
    )
""")
print("Created new table with proper unique constraint")

# Re-insert data
for row in existing_data:
    try:
        cursor.execute(
            "INSERT INTO treatment_plans (id, grass_type_name, location_id) VALUES (?, ?, ?)",
            row
        )
        print(f"Inserted: {row}")
    except Exception as e:
        print(f"Skipping duplicate: {row} - {e}")

conn.commit()

# Verify
cursor.execute("PRAGMA index_list(treatment_plans)")
print(f"\nNew indexes: {cursor.fetchall()}")

cursor.execute("SELECT * FROM treatment_plans")
print(f"Final data: {cursor.fetchall()}")

conn.close()
print("\nDone!")
