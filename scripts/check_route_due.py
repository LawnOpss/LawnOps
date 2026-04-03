import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Get raiden's technician ID
c.execute("SELECT id, name FROM technicians WHERE name LIKE '%raiden%'")
tech = c.fetchone()
if not tech:
    print("Raiden not found")
    conn.close()
    exit()

tech_id, tech_name = tech
print(f"Technician: {tech_name} (ID: {tech_id})")

# Get raiden's territories
c.execute('''
    SELECT tt.id, tt.territory_name, tt.center_lat, tt.center_lng, tt.radius_miles, tt.polygon_coords
    FROM technician_territories tt
    WHERE tt.technician_id = ?
''', (tech_id,))
territories = c.fetchall()
print(f"\nTerritories: {len(territories)}")
for t in territories:
    print(f"  - {t[1]}")

# Get customers in these territories with coordinates
today = datetime.now().date()
print(f"\n=== Services Due Today ({today}) ===\n")

# Check customer_services to see what services each customer has
c.execute('''
    SELECT DISTINCT c.id, c.name, c.address, c.lat, c.lng, cs.service_id, s.name as service_name
    FROM customers c
    JOIN customer_services cs ON c.id = cs.customer_id
    JOIN services s ON cs.service_id = s.id
    WHERE c.lat IS NOT NULL AND c.lng IS NOT NULL
''')
customer_services = c.fetchall()

# Group by service type
mowing_customers = []
chem_customers = []

for cust in customer_services:
    cust_id, name, address, lat, lng, service_id, service_name = cust
    
    # Check if customer is in any of raiden's territories
    in_territory = False
    for t in territories:
        terr_id, terr_name, center_lat, center_lng, radius, polygon = t
        
        # Simple distance check for circle territories
        if center_lat and center_lng and radius:
            import math
            R = 3959  # Earth radius in miles
            lat1_rad = math.radians(center_lat)
            lat2_rad = math.radians(lat)
            delta_lat = math.radians(lat - center_lat)
            delta_lng = math.radians(lng - center_lng)
            
            a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2
            dist = 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))
            
            if dist <= radius:
                in_territory = True
                break
    
    if in_territory:
        # Check if service is mowing or chemical
        if 'mow' in service_name.lower():
            mowing_customers.append((name, address, service_name))
        elif 'chem' in service_name.lower() or 'lawn' in service_name.lower():
            chem_customers.append((name, address, service_name))

print(f"MOWING CUSTOMERS ({len(mowing_customers)}):")
for cust in mowing_customers:
    print(f"  - {cust[0]}: {cust[1]} ({cust[2]})")

print(f"\nCHEMICAL LAWN CUSTOMERS ({len(chem_customers)}):")
for cust in chem_customers:
    print(f"  - {cust[0]}: {cust[1]} ({cust[2]})")

# Also check service_schedule for what's actually due today
c.execute('''
    SELECT ss.customer_id, c.name, ss.service_type, ss.scheduled_date, ss.status
    FROM service_schedule ss
    JOIN customers c ON ss.customer_id = c.id
    WHERE ss.technician_id = ? AND ss.scheduled_date <= ? AND ss.status = 'scheduled'
    ORDER BY ss.service_type, c.name
''', (tech_id, today))
scheduled = c.fetchall()

print(f"\n=== ACTUALLY SCHEDULED FOR TODAY ({len(scheduled)}) ===")
mowing_due = []
chem_due = []
for s in scheduled:
    cust_id, name, service_type, sched_date, status = s
    if service_type == 'mowing':
        mowing_due.append(name)
    elif service_type == 'chemical':
        chem_due.append(name)

print(f"\nMowing Due Today ({len(mowing_due)}):")
for name in mowing_due:
    print(f"  - {name}")

print(f"\nChemical Due Today ({len(chem_due)}):")
for name in chem_due:
    print(f"  - {name}")

conn.close()
