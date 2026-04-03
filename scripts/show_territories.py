import sqlite3
conn = sqlite3.connect('d:/python-lawn/database.db')
cursor = conn.cursor()

# Query territories with technician info
cursor.execute("""
    SELECT tt.id, tt.technician_id, t.name, tt.territory_name, 
           tt.center_lat, tt.center_lng, tt.radius_miles, tt.polygon_coords
    FROM technician_territories tt
    JOIN technicians t ON tt.technician_id = t.id
""")

rows = cursor.fetchall()
print(f"Found {len(rows)} territories:\n")

for r in rows:
    print(f"Territory ID: {r[0]}")
    print(f"Technician ID: {r[1]} | Name: {r[2]}")
    print(f"Territory Name: {r[3]}")
    print(f"Center: ({r[4]}, {r[5]})")
    print(f"Radius: {r[6]} miles")
    if r[7]:
        print(f"Has custom polygon: Yes (drawn territory)")
    else:
        print(f"Has custom polygon: No (auto-assigned circle)")
    print("-" * 40)
    
conn.close()
