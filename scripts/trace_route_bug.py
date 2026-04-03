"""
Trace exactly why raiden gets 0 customers in daily routes
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

def haversine_distance(lat1, lng1, lat2, lng2):
    R = 3959
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

target_location = 1
today = datetime.now().date()

# Get raiden's info
cursor.execute("SELECT id, name, color_hex FROM technicians WHERE name LIKE '%raiden%'")
tech_id, tech_name, tech_color = cursor.fetchone()
print(f"=== {tech_name} (ID: {tech_id}) ===\n")

# Get raiden's territories with service_type
cursor.execute("""
    SELECT id, territory_name, polygon_coords, service_type
    FROM technician_territories
    WHERE technician_id = ?
""", (tech_id,))
territories_raw = cursor.fetchall()
print(f"Territories: {len(territories_raw)}")

territories = []
for t in territories_raw:
    terr_id, name, coords_json, svc_type = t
    if coords_json:
        try:
            coords = json.loads(coords_json)
            territories.append({
                'id': terr_id,
                'name': name,
                'coords': coords,
                'service_type': svc_type or 'chemical'
            })
            print(f"  - {name}: {svc_type} ({len(coords)} coords)")
        except:
            print(f"  - {name}: ERROR parsing coords")

# Get technician's qualified services
cursor.execute("""
    SELECT s.service_type
    FROM technician_services ts
    JOIN services s ON ts.service_id = s.id
    WHERE ts.technician_id = ? AND s.is_active = 1
""", (tech_id,))
tech_services = [row[0] for row in cursor.fetchall()]
print(f"\nTech qualified services: {tech_services}")

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

print(f"\nTotal customers with services: {len(customer_services)}")

# Get rounds count for location
cursor.execute("SELECT id FROM treatment_plans WHERE location_id = ? LIMIT 1", (target_location,))
plan = cursor.fetchone()
rounds_count = 0
if plan:
    cursor.execute("SELECT COUNT(*) FROM treatments WHERE plan_id = ?", (plan[0],))
    rounds_count = cursor.fetchone()[0]
print(f"\nRounds count: {rounds_count}")

days_between = round(365 / rounds_count) if rounds_count > 0 else 30
print(f"Days between: {days_between}")

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

# Now trace through each customer step by step
print("\n=== Tracing each customer ===\n")

matched_customers = []
for row in all_due_customers:
    customer_id, name, address, sqft, actual_price, lat, lng, last_service, days_since = row
    
    print(f"Customer: {name} (ID: {customer_id})")
    print(f"  Location: ({lat}, {lng})")
    
    # Step 1: Check if in ANY territory (regardless of service type)
    in_any_territory = False
    matching_territory = None
    for t in territories:
        if point_in_polygon(lat, lng, t['coords']):
            in_any_territory = True
            matching_territory = t
            print(f"  -> In territory: {t['name']} ({t['service_type']})")
            break
    
    if not in_any_territory:
        print(f"  XX NOT in any territory - skipping")
        continue
    
    # Step 2: Get customer services
    cust_svcs = customer_services.get(customer_id, [])
    if not cust_svcs:
        print(f"  -> No services assigned, defaulting to ['chemical']")
        cust_svcs = ['chemical']
    else:
        print(f"  -> Customer services: {cust_svcs}")
    
    # Step 3: Check service + territory matching
    print(f"  -> Tech services: {tech_services}")
    
    matching_services = []
    for svc in cust_svcs:
        print(f"    Checking '{svc}':")
        
        # Check if tech is qualified for this service
        if svc not in tech_services:
            print(f"      XX Tech not qualified for '{svc}'")
            continue
        print(f"      -> Tech IS qualified for '{svc}'")
        
        # Check if there's a matching service-type territory
        found_territory = False
        for t in territories:
            print(f"      -> Territory {t['name']} is {t['service_type']} type")
            if t['service_type'] == svc:
                if point_in_polygon(lat, lng, t['coords']):
                    print(f"      -> MATCH! {svc} territory covers customer")
                    matching_services.append(svc)
                    found_territory = True
                    break
                else:
                    print(f"      XX Customer outside {svc} territory")
        
        if not found_territory:
            print(f"      XX No {svc} territory covers this customer")
    
    if matching_services:
        print(f"  ** MATCHED with: {matching_services}")
        matched_customers.append({
            'id': customer_id,
            'name': name,
            'services': matching_services
        })
    else:
        print(f"  XX No matching services after all checks")
    
    print()

print(f"\n=== FINAL RESULT ===")
print(f"Total due customers: {len(all_due_customers)}")
print(f"Matched to {tech_name}: {len(matched_customers)}")
for c in matched_customers:
    print(f"  - {c['name']}: {c['services']}")

conn.close()
