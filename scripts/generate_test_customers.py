#!/usr/bin/env python3
"""
Generate 100 test customers within 50 miles of office location
Run: python generate_test_customers.py
"""

import sqlite3
import random
import time
import json
from datetime import datetime, timedelta

# Connect to database
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Get office location - geocode the office address
cursor.execute("SELECT name, address FROM locations WHERE id = 1")
office = cursor.fetchone()
if not office:
    print("ERROR: Office location not found!")
    print("Please set up your office location in the web app first.")
    exit(1)

office_name, office_address = office
print(f"Office: {office_name} at {office_address}")
print("Geocoding office location...")

# Geocode the office address
import urllib.request
import urllib.parse
import json as json_lib

try:
    full_address = f"{office_address}, Texas, USA"
    encoded = urllib.parse.quote(full_address)
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={encoded}"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'LawnCareApp/1.0'})
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json_lib.loads(response.read().decode())
        if data and len(data) > 0:
            office_lat = float(data[0]['lat'])
            office_lng = float(data[0]['lon'])
            print(f"Office geocoded to: ({office_lat}, {office_lng})")
        else:
            print("WARNING: Could not geocode office, using default Keller, TX")
            office_lat, office_lng = 32.9346, -97.2251
except Exception as e:
    print(f"WARNING: Geocoding error: {e}")
    print("Using default Keller, TX location")
    office_lat, office_lng = 32.9346, -97.2251

# Sample data for realistic names
first_names = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Dorothy", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Edward", "Deborah", "Ronald", "Stephanie", "Timothy", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
    "Nicholas", "Angela", "Eric", "Shirley", "Jonathan", "Anna", "Stephen", "Brenda",
    "Larry", "Pamela", "Justin", "Emma", "Scott", "Nicole", "Brandon", "Helen",
    "Benjamin", "Samantha", "Samuel", "Katherine", "Gregory", "Christine", "Frank", "Debra"
]

last_names = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
    "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy",
    "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson", "Bailey",
    "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson", "Watson",
    "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza", "Ruiz", "Hughes"
]

street_names = [
    "Oak", "Pine", "Maple", "Cedar", "Elm", "Willow", "Birch", "Cherry",
    "Washington", "Lincoln", "Jefferson", "Adams", "Madison", "Monroe", "Jackson",
    "Main", "Broadway", "First", "Second", "Third", "Park", "Lake", "River",
    "Hill", "Valley", "Ridge", "Meadow", "Forest", "Sunset", "Sunrise", "Highland",
    "Lowland", "Creek", "Brook", "Spring", "Summer", "Autumn", "Winter", "Pleasant",
    "Fairview", "Highland", "Greenwood", "Rosewood", "Apple", "Peach", "Pear",
    "Magnolia", "Jasmine", "Ivy", "Vine", "Garden", "Flower", "Buttercup", "Daisy"
]

street_types = ["St", "Ave", "Blvd", "Ln", "Dr", "Rd", "Ct", "Way", "Pl", "Ter"]

# Generate random offset within 50 miles (approximately 0.8 degrees max)
def random_location_within_radius(center_lat, center_lng, max_miles=50):
    # Rough conversion: 1 degree lat ≈ 69 miles, 1 degree lng ≈ 54.6 miles at 35°N
    max_lat_offset = max_miles / 69.0
    max_lng_offset = max_miles / 54.6
    
    # Random point within circle (use sqrt for uniform distribution)
    r = random.random() ** 0.5
    theta = random.uniform(0, 2 * 3.14159)
    
    lat_offset = r * max_lat_offset * random.choice([-1, 1])
    lng_offset = r * max_lng_offset * random.choice([-1, 1])
    
    return center_lat + lat_offset, center_lng + lng_offset

# Generate a realistic street address
def generate_street_address():
    number = random.randint(100, 9999)
    street = random.choice(street_names)
    sttype = random.choice(street_types)
    return f"{number} {street} {sttype}"

# Generate customer data
customers_to_insert = []
print("\nGenerating 100 test customers...")

for i in range(100):
    # Generate name
    first = random.choice(first_names)
    last = random.choice(last_names)
    name = f"{first} {last}"
    
    # Generate location within 50 miles
    lat, lng = random_location_within_radius(office_lat, office_lng, 50)
    
    # Generate address (will geocode later)
    street = generate_street_address()
    # Approximate city based on location relative to office
    address = f"{street}, Texas"
    
    # Generate phone
    phone = f"{random.randint(200, 999)}{random.randint(100, 999)}{random.randint(1000, 9999)}"
    
    # Generate sqft (realistic lawn sizes)
    sqft = random.choice([
        random.randint(2000, 4000),   # Small lawns
        random.randint(4000, 8000),   # Medium lawns  
        random.randint(8000, 12000),  # Large lawns
        random.randint(12000, 20000)  # Very large
    ])
    
    # Calculate pricing based on your formula
    base_small = 3000
    base_large = 10000
    price_small = 50
    price_large = 100
    
    if sqft <= base_small:
        price = price_small
    elif sqft >= base_large:
        price = price_large * (sqft / base_large)
    else:
        ratio = (sqft - base_small) / (base_large - base_small)
        price = price_small + ratio * (price_large - price_small)
    
    monthly_min = round(price * 0.9, 2)
    monthly_max = round(price * 1.1, 2)
    
    # Generate last service date distribution
    rand = random.random()
    if rand < 0.3:
        # Never serviced (30%)
        last_service = None
    elif rand < 0.7:
        # 30-60 days ago (40%) - should show as due
        days_ago = random.randint(35, 60)
        last_service = (datetime.now() - timedelta(days=days_ago)).isoformat()
    else:
        # Recent (30%) - not due
        days_ago = random.randint(1, 20)
        last_service = (datetime.now() - timedelta(days=days_ago)).isoformat()
    
    customers_to_insert.append({
        'name': name,
        'address': address,
        'phone': phone,
        'sqft': sqft,
        'monthly_min': monthly_min,
        'monthly_max': monthly_max,
        'notes': '',
        'last_service_date': last_service,
        'lat': lat,
        'lng': lng,
        'actual_price': None,
        'location_id': 1
    })

print(f"Generated {len(customers_to_insert)} customers")
print("\nSample customers:")
for i, c in enumerate(customers_to_insert[:5], 1):
    print(f"  {i}. {c['name']} - {c['address']} - {c['sqft']} sqft - ${c['monthly_min']:.0f}-${c['monthly_max']:.0f}")

# Insert into database
print("\nInserting into database...")
inserted = 0
for customer in customers_to_insert:
    try:
        cursor.execute("""
            INSERT INTO customers 
            (name, address, phone, sqft, monthly_min, monthly_max, notes, 
             last_service_date, lat, lng, actual_price, location_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer['name'], customer['address'], customer['phone'], 
            customer['sqft'], customer['monthly_min'], customer['monthly_max'],
            customer['notes'], customer['last_service_date'], customer['lat'],
            customer['lng'], customer['actual_price'], customer['location_id']
        ))
        inserted += 1
    except Exception as e:
        print(f"Error inserting {customer['name']}: {e}")

conn.commit()
print(f"\nSuccessfully inserted {inserted} test customers!")
print(f"\nDistribution:")
print(f"  - Never serviced: ~30 customers (will show as 'DUE NOW')")
print(f"  - Due (35-60 days): ~40 customers (will show as 'DUE NOW')")
print(f"  - Not due (recent): ~30 customers (will show as 'Not Due')")
print(f"\nAll locations are within 50 miles of your office.")
print(f"Refresh your web app to see the new customers!")

conn.close()
