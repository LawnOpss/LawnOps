import sqlite3
import json
import math
from datetime import datetime

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

def point_in_polygon(lat, lng, polygon):
    if not polygon or len(polygon) < 3:
        return False
    x, y = lng, lat
    inside = False
    n = len(polygon)
    p1x, p1y = polygon[0][1], polygon[0][0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n][1], polygon[i % n][0]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

target_location = 1
today = datetime.now().date()

# Get Alan's info
cursor.execute("SELECT id, name, color_hex FROM technicians WHERE name LIKE '%alan%'")
alan = cursor.fetchone()
if not alan:
    print("Alan not found")
    exit()

tech_id, tech_name, tech_color = alan
print(f"=== {tech_name} (ID: {tech_id}) ===\n")

# Get Alan's territories
cursor.execute("""
    SELECT id, territory_name, polygon_coords, service_type
    FROM technician_territories
    WHERE technician_id = ?
""", (tech_id,))
territories_raw = cursor.fetchall()
print(f"Territories: {len(territories_raw)}")
for t in territories_raw:
    print(f"  - {t[1]}: {t[3] or 'chemical'}")

territories = []
for t in territories_raw:
    if t[2]:
        try:
            coords = json.loads(t[2])
            territories.append({'coords': coords, 'service_type': t[3] or 'chemical'})
        except:
            pass

# Get Alan's qualified services
cursor.execute("""
    SELECT s.service_type
    FROM technician_services ts
    JOIN services s ON ts.service_id = s.id
    WHERE ts.technician_id = ? AND s.is_active = 1
""", (tech_id,))
tech_services = [row[0] for row in cursor.fetchall()]
print(f"\nQualified services: {tech_services}")

# Get customer services
cursor.execute("""
    SELECT cs.customer_id, s.service_type
    FROM customer_services cs
    JOIN services s ON cs.service_id = s.id
    WHERE s.is_active = 1
""")
customer_services = {}
for row in cursor.fetchall():
    cust_id, svc_type = row
    if cust_id not in customer_services:
        customer_services[cust_id] = []
    customer_services[cust_id].append(svc_type)

# Get rounds count
cursor.execute("SELECT id FROM treatment_plans WHERE location_id = ? LIMIT 1", (target_location,))
plan = cursor.fetchone()
rounds_count = 0
if plan:
    cursor.execute("SELECT COUNT(*) FROM treatments WHERE plan_id = ?", (plan[0],))
    rounds_count = cursor.fetchone()[0]
days_between = round(365 / rounds_count) if rounds_count > 0 else 30
print(f"\nDays between services: {days_between}")

# Get due customers
cursor.execute("""
    SELECT c.id, c.name, c.address, c.sqft, c.actual_price, c.lat, c.lng
    FROM customers c
    WHERE c.location_id = ? AND c.lat IS NOT NULL AND c.lng IS NOT NULL
        AND (c.last_service_date IS NULL OR julianday('now') - julianday(c.last_service_date) > ?)
""", (target_location, days_between))

due_customers = cursor.fetchall()
print(f"\nTotal due customers: {len(due_customers)}")

# Find mowing customers in Alan's territory
mowing_customers = []
for row in due_customers:
    cust_id, name, address, sqft, price, lat, lng = row
    
    # Check if in any territory
    in_territory = False
    territory_service = None
    for t in territories:
        if point_in_polygon(lat, lng, t['coords']):
            in_territory = True
            territory_service = t['service_type']
            break
    
    if not in_territory:
        continue
    
    # Get customer services
    cust_svcs = customer_services.get(cust_id, [])
    
    # Check if mowing is in customer services AND tech has mowing
    if 'mowing' in cust_svcs and 'mowing' in tech_services:
        mowing_customers.append({
            'id': cust_id,
            'name': name,
            'address': address,
            'sqft': sqft,
            'territory_service': territory_service
        })

print(f"\n=== Alan's Mowing Customers Due Today: {len(mowing_customers)} ===")
for c in mowing_customers:
    print(f"  - {c['name']}: {c['address']} ({c['sqft']:,} sqft)")

conn.close()
