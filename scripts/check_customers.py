import sqlite3
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

print("=== CUSTOMERS TABLE ===")
cursor.execute("SELECT COUNT(*) FROM customers")
count = cursor.fetchone()[0]
print(f"Total customers: {count}")

if count > 0:
    cursor.execute("SELECT id, name, address, location_id FROM customers LIMIT 5")
    print("\nFirst 5 customers:")
    for row in cursor.fetchall():
        print(f"  ID {row[0]}: {row[1]} - Location: {row[3]}")

conn.close()
