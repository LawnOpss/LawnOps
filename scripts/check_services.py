import sqlite3
conn = sqlite3.connect('database.db')
c = conn.cursor()

# Check what services are assigned to raiden
print("=== Raiden's Service Assignments ===")
c.execute('''
    SELECT s.name, s.service_type
    FROM technician_services ts
    JOIN services s ON ts.service_id = s.id
    JOIN technicians t ON ts.technician_id = t.id
    WHERE t.name LIKE '%raiden%'
''')
for row in c.fetchall():
    print(f"  - {row[0]} (type: {row[1]})")

# Check all mowing services
print("\n=== All Mowing Services ===")
c.execute("SELECT id, name, service_type, location_id FROM services WHERE service_type = 'mowing' OR name LIKE '%Mowing%'")
for row in c.fetchall():
    print(f"  ID {row[0]}: {row[1]} (type: {row[2]}, location: {row[3]})")

# Check all services for location 1 (Keller)
print("\n=== All Services at Location 1 (Keller) ===")
c.execute('SELECT id, name, service_type, location_id FROM services WHERE location_id = 1 AND is_active = 1')
for row in c.fetchall():
    print(f"  ID {row[0]}: {row[1]} (type: {row[2]}, location: {row[3]})")

# Check all services for location 3 (Georgia)
print("\n=== All Services at Location 3 (Georgia) ===")
c.execute('SELECT id, name, service_type, location_id FROM services WHERE location_id = 3 AND is_active = 1')
for row in c.fetchall():
    print(f"  ID {row[0]}: {row[1]} (type: {row[2]}, location: {row[3]})")

# Get raiden's tech ID and add missing mowing service
print("\n=== Adding missing mowing service to raiden ===")
c.execute("SELECT id FROM technicians WHERE name LIKE '%raiden%'")
tech_row = c.fetchone()
if tech_row:
    tech_id = tech_row[0]
    print(f"Tech ID: {tech_id}")

    # Find mowing service ID
    c.execute("SELECT id FROM services WHERE service_type = 'mowing' OR name LIKE '%Mowing%'")
    mowing_services = c.fetchall()
    print(f"Mowing services found: {[s[0] for s in mowing_services]}")
    
    if mowing_services:
        mowing_id = mowing_services[0][0]
        print(f"Adding mowing service ID {mowing_id} to tech {tech_id}")
        try:
            c.execute('INSERT INTO technician_services (technician_id, service_id) VALUES (?, ?)', (tech_id, mowing_id))
            conn.commit()
            print("SUCCESS: Added mowing service to raiden")
        except sqlite3.IntegrityError:
            print("Already has mowing service assigned")
else:
    print("Tech not found!")

conn.close()
