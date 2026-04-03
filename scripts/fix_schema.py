import sqlite3
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

print("=== Fixing treatment_plans unique constraint ===")

# Check current schema
cursor.execute("PRAGMA index_list(treatment_plans)")
indexes = cursor.fetchall()
print(f"Current indexes: {indexes}")

# The sqlite_autoindex_treatment_plans_1 is on grass_type_name only
# We need to drop it and create a proper unique index on (grass_type_name, location_id)

try:
    # Drop the old unique index
    cursor.execute("DROP INDEX IF EXISTS sqlite_autoindex_treatment_plans_1")
    print("Dropped old unique index")
except Exception as e:
    print(f"Drop error (might be OK): {e}")

# Recreate the table with proper constraint
# SQLite doesn't support ALTER TABLE for adding composite unique constraints easily
# So we need to recreate

cursor.execute("""
    CREATE TABLE IF NOT EXISTS treatment_plans_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grass_type_name TEXT NOT NULL,
        location_id INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (location_id) REFERENCES locations (id) ON DELETE CASCADE,
        UNIQUE(grass_type_name, location_id)
    )
""")
print("Created new table with proper unique constraint")

# Copy existing data
cursor.execute("""
    INSERT INTO treatment_plans_new (id, grass_type_name, location_id, created_at)
    SELECT id, grass_type_name, COALESCE(location_id, 1), created_at FROM treatment_plans
""")
print(f"Copied {cursor.rowcount} rows")

# Drop old table
cursor.execute("DROP TABLE IF EXISTS treatment_plans")
print("Dropped old table")

# Rename new table
cursor.execute("ALTER TABLE treatment_plans_new RENAME TO treatment_plans")
print("Renamed new table")

conn.commit()
print("=== Done! ===")

# Verify
cursor.execute("PRAGMA index_list(treatment_plans)")
print(f"New indexes: {cursor.fetchall()}")

cursor.execute("PRAGMA table_info(treatment_plans)")
print(f"Schema: {cursor.fetchall()}")

conn.close()
