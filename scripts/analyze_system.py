import sqlite3
import json

conn = sqlite3.connect('d:/python-lawn/database.db')
cursor = conn.cursor()

print("=" * 60)
print("TECHNICIANS AND THEIR ASSIGNED SERVICES")
print("=" * 60)

# Get all technicians with their services
cursor.execute("""
    SELECT t.id, t.name, t.location_id, t.color_hex, t.is_active, l.name as loc_name
    FROM technicians t
    JOIN locations l ON t.location_id = l.id
    ORDER BY t.name
""")

techs = cursor.fetchall()
for tech in techs:
    tech_id, name, loc_id, color, is_active, loc_name = tech
    status = "ACTIVE" if is_active else "INACTIVE"
    print(f"\n>> {name} (ID: {tech_id}) - {status}")
    print(f"   Location: {loc_name}")
    print(f"   Color: {color}")
    
    # Get services for this technician
    cursor.execute("""
        SELECT s.name, s.service_type, s.id
        FROM technician_services ts
        JOIN services s ON ts.service_id = s.id
        WHERE ts.technician_id = ?
    """, (tech_id,))
    
    services = cursor.fetchall()
    if services:
        print(f"   Assigned Services:")
        for svc in services:
            print(f"      • {svc[0]} (type: {svc[1]}, id: {svc[2]})")
    else:
        print(f"   Assigned Services: NONE (WARNING)")

print("\n" + "=" * 60)
print("CUSTOMERS AND THEIR SERVICE STATUS")
print("=" * 60)

# Get customers with services
# Check what tables we need
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%customer%'")
print(f"\nCustomer-related tables: {[r[0] for r in cursor.fetchall()]}")

# Get customer services
cursor.execute("""
    SELECT c.rowid, c.name, c.address, c.location_id, c.grass_type_id,
           cs.service_id, s.name as service_name, s.service_type
    FROM customers c
    LEFT JOIN customer_services cs ON c.rowid = cs.customer_id
    LEFT JOIN services s ON cs.service_id = s.id
    ORDER BY c.name
    LIMIT 20
""")

rows = cursor.fetchall()
print(f"\nFirst 20 customers and their services:")
for row in rows:
    cust_id, name, address, loc_id, grass_id, svc_id, svc_name, svc_type = row
    services = f"{svc_name} ({svc_type})" if svc_name else "NO SERVICES"
    print(f"  {name[:30]:<30} | {services}")

print("\n" + "=" * 60)
print("SERVICES AVAILABLE IN SYSTEM")
print("=" * 60)

cursor.execute("SELECT id, name, service_type, location_id FROM services ORDER BY service_type, name")
for svc in cursor.fetchall():
    print(f"  ID: {svc[0]:<3} | {svc[1]:<25} | Type: {svc[2]:<12} | Location: {svc[3]}")

conn.close()
