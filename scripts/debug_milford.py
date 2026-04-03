#!/usr/bin/env python3
"""Debug script to check Milford Billford's service status"""
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Find Milford Billford
cursor.execute("SELECT rowid, name, last_service_date FROM customers WHERE name LIKE '%millford%'")
customer = cursor.fetchone()
if not customer:
    print("Milford Billford not found")
    exit()

customer_id, name, last_service_date = customer
print(f"Customer: {name} (ID: {customer_id})")
print(f"Last service date: {last_service_date}")
print()

# Get all active services for this customer
cursor.execute("""
    SELECT cs.service_id, cs.last_completed_date, cs.price, s.name, s.config_json
    FROM customer_services cs
    JOIN services s ON cs.service_id = s.id
    WHERE cs.customer_id = ? AND cs.is_active = 1
"", (customer_id,))

services = cursor.fetchall()
print("Active services:")
now = datetime.now().date()

for svc in services:
    svc_id, last_completed, price, svc_name, config_json = svc
    
    # Calculate if due
    frequency = 45  # default
    if config_json:
        try:
            import json
            cfg = json.loads(config_json)
            if cfg.get('frequency_days'):
                frequency = int(cfg['frequency_days'])
        except:
            pass
    
    if last_completed:
        completed_date = datetime.fromisoformat(last_completed).date()
        next_due = completed_date + timedelta(days=frequency)
        is_due = now >= next_due
        days_until = (next_due - now).days
        status = "DUE" if is_due else f"Due in {days_until} days"
        print(f"  - {svc_name}: Last completed {last_completed}, Next due {next_due} ({status})")
    else:
        print(f"  - {svc_name}: Never completed (DUE NOW)")

conn.close()
