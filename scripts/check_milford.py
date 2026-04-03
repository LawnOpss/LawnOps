import sqlite3
conn = sqlite3.connect('database.db')
c = conn.cursor()
c.execute("SELECT rowid, name, last_service_date FROM customers WHERE name LIKE '%millford%'")
row = c.fetchone()
if row:
    print(f"Customer ID: {row[0]}, Name: {row[1]}, Last service: {row[2]}")
    c.execute("SELECT cs.last_completed_date, s.name FROM customer_services cs JOIN services s ON cs.service_id = s.id WHERE cs.customer_id = ? AND cs.is_active = 1", (row[0],))
    for svc in c.fetchall():
        print(f"  Service: {svc[1]}, Last completed: {svc[0]}")
else:
    print("Customer not found")
conn.close()
