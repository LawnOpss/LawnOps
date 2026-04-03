import sqlite3
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

print("Clearing service-related data...")

# Delete all services
cursor.execute("DELETE FROM services")
print(f"Deleted {cursor.rowcount} services")

# Delete all treatment plans (grass types)
cursor.execute("DELETE FROM treatment_plans")
print(f"Deleted {cursor.rowcount} treatment plans (grass types)")

# Delete all treatments
cursor.execute("DELETE FROM treatments")
print(f"Deleted {cursor.rowcount} treatments")

# Delete customer service assignments
cursor.execute("DELETE FROM customer_services")
print(f"Deleted {cursor.rowcount} customer service assignments")

conn.commit()
conn.close()

print("\nDatabase cleared. You can now add services fresh.")
