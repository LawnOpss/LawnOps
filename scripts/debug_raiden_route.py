import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('database.db')
c = conn.cursor()

today = datetime.now().date()
print(f"Today: {today}")

# Get raiden's info
c.execute("SELECT id, name FROM technicians WHERE name LIKE '%raiden%'")
tech = c.fetchone()
tech_id, tech_name = tech
print(f"\nTechnician: {tech_name} (ID: {tech_id})")

# Check service_schedule for raiden
c.execute('''
    SELECT ss.id, ss.customer_id, ss.service_type, ss.scheduled_date, ss.status, ss.technician_id
    FROM service_schedule ss
    WHERE ss.technician_id = ?
    ORDER BY ss.scheduled_date
''', (tech_id,))
schedules = c.fetchall()
print(f"\nService schedules for raiden: {len(schedules)}")
for s in schedules[:10]:
    print(f"  ID:{s[0]} Cust:{s[1]} Type:{s[2]} Date:{s[3]} Status:{s[4]} Tech:{s[5]}")
if len(schedules) > 10:
    print(f"  ... and {len(schedules)-10} more")

# Check route_selection - current route
c.execute('''
    SELECT rs.id, rs.customer_id, c.name, rs.added_at
    FROM route_selection rs
    JOIN customers c ON rs.customer_id = c.id
    WHERE rs.added_by = ?
''', (tech_id,))
route = c.fetchall()
print(f"\nRoute selection for raiden: {len(route)} customers")
for r in route:
    print(f"  - {r[2]} (ID:{r[1]})")

# Check if there's a daily route generated
c.execute('''
    SELECT id, technician_id, route_date, customer_ids, status
    FROM route_clusters
    WHERE technician_id = ? AND route_date = ?
''', (tech_id, today))
clusters = c.fetchall()
print(f"\nRoute clusters for today: {len(clusters)}")
for cl in clusters:
    print(f"  ID:{cl[0]} Tech:{cl[1]} Date:{cl[2]} Status:{cl[4]}")
    if cl[3]:
        cust_ids = cl[3].split(',') if isinstance(cl[3], str) else []
        print(f"  Customers: {len(cust_ids)}")

# Check route optimization history
c.execute('''
    SELECT id, technician_id, route_date, customer_count, status
    FROM route_optimization_history
    WHERE technician_id = ? AND route_date = ?
''', (tech_id, today))
history = c.fetchall()
print(f"\nRoute optimization history: {len(history)}")
for h in history:
    print(f"  ID:{h[0]} Tech:{h[1]} Date:{h[2]} Count:{h[3]} Status:{h[4]}")

conn.close()
