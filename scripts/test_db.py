import sqlite3

# Update locations with proper geocoded coordinates
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Import the geocoding function from main.py
import sys
sys.path.append('.')
from main import geocode_geocodio

# Get all locations and geocode their addresses properly
cursor.execute('SELECT id, name, address FROM locations')
locations = cursor.fetchall()

print('Geocoding all locations with proper addresses:')
for loc_id, name, address in locations:
    if address:  # Only geocode if address exists
        lat, lng = geocode_geocodio(address)
        print(f'{name}: "{address}" -> ({lat}, {lng})')
        
        # Update with geocoded coordinates
        cursor.execute('UPDATE locations SET lat = ?, lng = ? WHERE id = ?', (lat, lng, loc_id))

conn.commit()

# Verify the updates
cursor.execute('SELECT id, name, address, lat, lng FROM locations')
locations = cursor.fetchall()
print('\nUpdated Locations:')
for loc in locations:
    print(f'  ID: {loc[0]}, Name: {loc[1]}, Address: {loc[2]}, Lat: {loc[3]}, Lng: {loc[4]}')

conn.close()
