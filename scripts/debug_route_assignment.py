"""
Debug script to trace why raiden gets 0 customers in daily routes
"""
import sqlite3
import json
import math
from datetime import datetime

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

def point_in_polygon(lat, lng, polygon):
    """Ray casting algorithm to check if point is inside polygon"""
    if not polygon or len(polygon) < 3:
        return False
    
    x, y = lng, lat  # Note: polygon is [lat, lng] but we need [lng, lat] for algorithm
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

target_location = 1  # Assuming location 1 (Keller)
today = datetime.now().date()

# Get raiden's info
cursor.execute("SELECT id, name, color_hex FROM technicians WHERE name LIKE '%raiden%'")
tech = cursor.fetchone()
if not tech:
    print("Raiden not found!")
    exit()

tech_id, tech_name, tech_color = tech
print(f"=== Debugging {tech_name} (ID: {tech_id}) ===\n")

# Get raiden's territories
cursor.execute("""
    SELECT id, territory_name, polygon_coords, service_type
    FROM technician_territories
    WHERE technician_id = ?
""", (tech_id,))
territories_raw = cursor.fetchall()
print(f"Territories found: {len(territories_raw)}")

territories = []
for t in territories_raw:
    terr_id, name, coords_json, svc_type = t
    print(f"  - {name} (service_type: {svc_type})")
    if coords_json:
        try:
            coords = json.loads(coords_json)
            print(f"    Coords count: {len(coords)}")
            territories.append({
                'id': terr_id,
                'name': name,
                'coords': coords,
                'service_type': svc_type or 'chemical'
            })
        except Exception as e:
            print(f"    ERROR parsing coords: {e}")

print(f"\nValid territories with coords: {len(territories)}")

# Get technician's qualified services
cursor.execute("""
    SELECT s.service_type
    FROM technician_services ts
    JOIN services s ON ts.service_id = s.id
    WHERE ts.technician_id = ? AND s.is_active = 1
""", (tech_id,))
tech_services = [row[0] for row in cursor.fetchall()]
print(f"\nTechnician qualified services: {tech_services}")

# Get rounds count for location
cursor.execute("SELECT id FROM treatment_plans WHERE location_id = ? LIMIT 1", (target_location,))
plan = cursor.fetchone()
if plan:
    cursor.execute("SELECT COUNT(*) FROM treatments WHERE plan_id = ?", (plan[0],))
    rounds_count = cursor.fetchone()[0]
else:
    rounds_count = 0
print(f"\nRounds count for location {target_location}: {rounds_count}")

if rounds_count == 0:
    print("ERROR: No rounds configured - this would cause 'Add treatment rounds to show due customers' message")

days_between = round(365 / rounds_count) if rounds_count > 0 else 30
print(f"Days between services: {days_between}")

# Get due customers
cursor.execute("""
    SELECT 
        c.id, c.name, c.address, c.sqft, c.actual_price, 
        c.lat, c.lng, c.last_service_date,
        julianday('now') - julianday(c.last_service_date) as days_since_service
    FROM customers c
    WHERE c.location_id = ? AND c.lat IS NOT NULL AND c.lng IS NOT NULL
        AND (c.last_service_date IS NULL OR julianday('now') - julianday(c.last_service_date) > ?)
""", (target_location, days_between))

all_due_customers = cursor.fetchall()
print(f"\nTotal due customers at location: {len(all_due_customers)}")

# Get customer services mapping
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

# Now trace through each customer
print(f"\n=== Checking each due customer ===\n")

matched_customers = []
for row in all_due_customers:
    customer_id, name, address, sqft, actual_price, lat, lng, last_service, days_since = row
    
    print(f"Customer: {name} (ID: {customer_id})")
    print(f"  Location: ({lat}, {lng})")
    
    # Check if in ANY territory
    in_any_territory = False
    for t in territories:
        if point_in_polygon(lat, lng, t['coords']):
            in_any_territory = True
            print(f"  ✓ Inside territory: {t['name']} (service_type: {t['service_type']})")
            break
    
    if not in_any_territory:
        print(f"  ✗ Not in any territory - skipping")
        continue
    
    # Get customer services
    cust_svcs = customer_services.get(customer_id, [])
    print(f"  Customer services: {cust_svcs}")
    
    if not cust_svcs:
        print(f"  ✗ No services assigned - defaulting to 'chemical'")
        cust_svcs = ['chemical']
    
    # Check service matching
    matching_services = []
    for svc in cust_svcs:
        print(f"    Checking service '{svc}':")
        if svc not in tech_services:
            print(f"      ✗ Tech not qualified for '{svc}'")
            continue
        
        print(f"      ✓ Tech qualified for '{svc}'")
        
        # Check if this specific service-type territory covers the customer
        found_matching_territory = False
        for t in territories:
            if t['service_type'] == svc:
                if point_in_polygon(lat, lng, t['coords']):
                    print(f"      ✓ Found matching {svc} territory: {t['name']}")
                    matching_services.append(svc)
                    found_matching_territory = True
                    break
                else:
                    print(f"      ✗ Territory {t['name']} is {svc} type but customer outside")
        
        if not found_matching_territory:
            print(f"      ✗ No {svc} territory covers this customer")
    
    if matching_services:
        print(f"  ✓✓✓ MATCHED with services: {matching_services}")
        matched_customers.append({
            'id': customer_id,
            'name': name,
            'services': matching_services
        })
    else:
        print(f"  ✗ No matching services after territory check")
    
    print()

print(f"\n=== SUMMARY ===")
print(f"Total due customers: {len(all_due_customers)}")
print(f"Matched to {tech_name}: {len(matched_customers)}")
for c in matched_customers:
    print(f"  - {c['name']}: {c['services']}")

conn.close()
