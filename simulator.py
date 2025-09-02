import requests
import time
import math
import random

# --- Configuration ---
# Yeh aapke Flask server ka address hai
SERVER_URL = "http://127.0.0.1:5000/update_location"
# Har kitne second mein location update karni hai
UPDATE_INTERVAL_SECONDS = 3
# Stops ke beech mein kitne chote steps lene hain (smoothness ke liye)
INTERMEDIATE_STEPS = 20

# ================== ZYADA BUSES AUR ROUTES WALA DATA ==================
ROUTES = {
    'chandigarh-gurgaon': [ (30.7333, 76.7794), (30.3782, 76.7767), (29.6857, 76.9905), (29.3909, 76.9635), (28.9931, 77.0151), (28.4595, 77.0266) ],
    'ambala-hisar': [ (30.3782, 76.7767), (29.9697, 76.8783), (29.5876, 76.0987), (29.1492, 75.7217) ],
    'rohtak-faridabad': [ (28.8955, 76.6066), (28.7234, 76.4321), (28.5876, 76.3456), (28.4595, 77.0266), (28.4089, 77.3178) ],
    'karnal-sonipat': [ (29.6857, 76.9905), (29.3909, 76.9635), (28.9931, 77.0151) ],
    'panipat-yamunanagar': [ (29.3909, 76.9635), (29.6857, 76.9905), (29.9697, 76.8783), (30.1678, 77.2835) ],
    'hisar-sirsa': [ (29.1492, 75.7217), (29.3210, 75.8765), (29.5372, 75.0234) ],
    'gurgaon-rewari': [ (28.4595, 77.0266), (28.3184, 76.8615), (28.1919, 76.6195) ]
}
# Reverse routes (jaise Gurgaon -> Chandigarh) apne aap banayein
route_keys = list(ROUTES.keys())
for key in route_keys:
    # Key ko string mein convert karein agar woh tuple hai
    key_str = key if isinstance(key, str) else '-'.join(key)
    start, end = key_str.split('-')
    reverse_key = f"{end}-{start}"
    if reverse_key not in ROUTES:
        ROUTES[reverse_key] = ROUTES[key_str][::-1]

ALL_BUSES = [
    # Chandigarh <-> Gurgaon Route
    { "id": "HR55A1234", "number": "HR-55-A-1234", "routeKey": "chandigarh-gurgaon", "status": "On Time" },
    { "id": "HR55C9012", "number": "HR-55-C-9012", "routeKey": "chandigarh-gurgaon", "status": "Delayed" },
    { "id": "HR56A1111", "number": "HR-56-A-1111", "routeKey": "gurgaon-chandigarh", "status": "On Time" },
    { "id": "HR56B2222", "number": "HR-56-B-2222", "routeKey": "gurgaon-chandigarh", "status": "On Time" },
    
    # Ambala <-> Hisar Route
    { "id": "HR57A6666", "number": "HR-57-A-6666", "routeKey": "ambala-hisar", "status": "On Time" },
    { "id": "HR57B7777", "number": "HR-57-B-7777", "routeKey": "hisar-ambala", "status": "Delayed" },
    
    # Rohtak <-> Faridabad Route
    { "id": "HR58A1001", "number": "HR-58-A-1001", "routeKey": "rohtak-faridabad", "status": "On Time" },
    { "id": "HR58B2002", "number": "HR-58-B-2002", "routeKey": "faridabad-rohtak", "status": "On Time" },

    # Karnal <-> Sonipat Route
    { "id": "HR59A3003", "number": "HR-59-A-3003", "routeKey": "karnal-sonipat", "status": "On Time" },
    { "id": "HR59B4004", "number": "HR-59-B-4004", "routeKey": "sonipat-karnal", "status": "Delayed" },

    # Panipat <-> Yamunanagar Route
    { "id": "HR60A5005", "number": "HR-60-A-5005", "routeKey": "panipat-yamunanagar", "status": "On Time" },
    { "id": "HR60B6006", "number": "HR-60-B-6006", "routeKey": "yamunanagar-panipat", "status": "On Time" },

    # Hisar <-> Sirsa Route
    { "id": "HR61A7007", "number": "HR-61-A-7007", "routeKey": "hisar-sirsa", "status": "On Time" },
    { "id": "HR61B8008", "number": "HR-61-B-8008", "routeKey": "sirsa-hisar", "status": "Delayed" },
    
    # Gurgaon <-> Rewari Route
    { "id": "HR62A9009", "number": "HR-62-A-9009", "routeKey": "gurgaon-rewari", "status": "On Time" },
    { "id": "HR62B1010", "number": "HR-62-B-1010", "routeKey": "rewari-gurgaon", "status": "On Time" },
]
# ==============================================================================

# --- Helper Functions ---
# Bus ki disha (direction) calculate karne ke liye
def get_bearing(lat1, lon1, lat2, lon2):
    dLon = math.radians(lon2 - lon1)
    lat1, lat2 = math.radians(lat1), math.radians(lat2)
    y = math.sin(dLon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360

# Do points ke beech ka point nikalne ke liye
def get_intermediate_point(lat1, lon1, lat2, lon2, fraction):
    lat = lat1 + (lat2 - lat1) * fraction
    lon = lon1 + (lon2 - lon1) * fraction
    return lat, lon

# --- Main Simulator Loop ---
# Har bus ke liye uski random starting progress track karein
bus_progress = {}
for bus in ALL_BUSES:
    route_key_str = bus['routeKey']
    # Start mein bus ko route ke kisi bhi hisse se shuru karein
    bus_progress[bus['id']] = {
        'leg': random.randint(0, len(ROUTES[route_key_str]) - 2), 
        'step': random.randint(0, INTERMEDIATE_STEPS)
    }

print(f"Upgraded Bus simulator chalu ho gaya hai... {len(ALL_BUSES)} buses live hain.")
print(f"Updates {SERVER_URL} par bhej raha hai...")

while True:
    for bus in ALL_BUSES:
        progress = bus_progress[bus['id']]
        
        route_key_str = bus['routeKey']
        route_points = ROUTES[route_key_str]
        
        # Current leg ke start aur end points
        start_point = route_points[progress['leg']]
        # Agla point, agar aakhri par hai to wapas pehle par aa jaye
        end_point_index = (progress['leg'] + 1) % len(route_points)
        end_point = route_points[end_point_index]

        lat1, lon1 = start_point
        lat2, lon2 = end_point
        
        # Bus ki current position calculate karein
        fraction = progress['step'] / INTERMEDIATE_STEPS
        current_lat, current_lon = get_intermediate_point(lat1, lon1, lat2, lon2, fraction)
        bearing = get_bearing(lat1, lon1, lat2, lon2)

        data_to_send = {
            "bus_id": bus['id'], "number": bus['number'], "routeKey": route_key_str,
            "latitude": current_lat, "longitude": current_lon,
            "status": bus['status'], "bearing": bearing
        }

        try:
            # Server ko data bhejein
            requests.post(SERVER_URL, json=data_to_send, timeout=2.5)
            print(f"Update: {bus['id']} ({bus['routeKey']}) | Pos: {current_lat:.2f}, {current_lon:.2f}")
        except requests.exceptions.RequestException:
            print(f"Error: Server se connect nahi ho pa raha hai. Kya server chalu hai?")
        
        # Progress ko aage badhayein
        progress['step'] += 1
        if progress['step'] > INTERMEDIATE_STEPS:
            progress['step'] = 0
            progress['leg'] = end_point_index # Agle leg par jayein
    
    print("-" * 20)
    time.sleep(UPDATE_INTERVAL_SECONDS)