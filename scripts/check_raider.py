import sqlite3
import json

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Find Raider's territory
c.execute("""
    SELECT tt.id, tt.technician_id, tt.territory_name, tt.center_lat, tt.center_lng, 
           tt.radius_miles, tt.polygon_coords, t.name, t.color_hex
    FROM technician_territories tt
    JOIN technicians t ON tt.technician_id = t.id
    WHERE t.name LIKE '%raiden%' OR t.name LIKE '%raider%'
""")
territory = c.fetchone()

if territory:
    print(f"Technician: {territory[7]}")
    print(f"Territory: {territory[2]}")
    print(f"Center: ({territory[3]}, {territory[4]})")
    print(f"Radius: {territory[5]} miles")
    print(f"Polygon: {territory[6][:200] if territory[6] else 'None'}...")
    print()
    
    # Find customers near this territory center
    center_lat, center_lng = territory[3], territory[4]
    radius = territory[5] or 50
    
    c.execute("""
        SELECT rowid, name, address, lat, lng 
        FROM customers 
        WHERE lat IS NOT NULL AND lng IS NOT NULL
    """)
    
    customers = c.fetchall()
    print(f"All customers with coordinates ({len(customers)} total):")
    
    def calc_distance(lat1, lng1, lat2, lng2):
        import math
        R = 3959  # Earth radius in miles
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    nearby = []
    for cust in customers:
        rowid, name, address, lat, lng = cust
        if lat and lng:
            dist = calc_distance(center_lat, center_lng, lat, lng)
            if dist <= radius:
                nearby.append((name, address, dist))
    
    print(f"\nCustomers within {radius} miles of territory center:")
    for name, address, dist in sorted(nearby, key=lambda x: x[2]):
        print(f"  - {name}: {address} ({dist:.1f} miles)")
else:
    print("Raider/Raiden territory not found")
    
    # List all technicians with territories
    c.execute("""
        SELECT t.name, tt.territory_name 
        FROM technicians t
        JOIN technician_territories tt ON t.id = tt.technician_id
    """)
    print("\nAll technicians with territories:")
    for row in c.fetchall():
        print(f"  - {row[0]}: {row[1]}")

conn.close()
