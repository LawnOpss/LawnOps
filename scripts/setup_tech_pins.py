"""
Quick script to set up technician PINs for mobile app login
Run this once to add PINs to existing technicians
"""
import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Add PIN column if not exists
try:
    cursor.execute("ALTER TABLE technicians ADD COLUMN pin TEXT")
    conn.commit()
    print("✓ Added PIN column to technicians table")
except sqlite3.OperationalError:
    print("PIN column already exists")

# Show current technicians
print("\nCurrent technicians:")
cursor.execute("SELECT id, name, location_id, pin FROM technicians")
techs = cursor.fetchall()

if not techs:
    print("No technicians found! Create one in the owner panel first.")
else:
    for tech in techs:
        tech_id, name, loc_id, pin = tech
        status = f"PIN: {pin}" if pin else "No PIN set"
        print(f"  ID {tech_id}: {name} ({status})")
    
    # Set default PIN for first technician if none set
    if techs and not techs[0][3]:
        cursor.execute("UPDATE technicians SET pin = ? WHERE id = ?", ("1234", techs[0][0]))
        conn.commit()
        print(f"\n✓ Set default PIN '1234' for {techs[0][1]} (ID: {techs[0][0]})")
        print("\nYou can now log in with:")
        print(f"  Technician ID: {techs[0][0]}")
        print(f"  PIN: 1234")

conn.close()
