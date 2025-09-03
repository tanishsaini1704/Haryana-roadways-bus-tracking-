import requests
import time
import math
import sys
from datetime import datetime, timedelta

# --- Configuration ---
SERVER_BASE_URL = "http://127.0.0.1:5000"
UPDATE_LOCATION_URL = f"{SERVER_BASE_URL}/update_location"
GET_ROUTE_URL = f"{SERVER_BASE_URL}/get_route"
GET_ALL_ROUTES_URL = f"{SERVER_BASE_URL}/get_all_routes" # New endpoint
UPDATE_INTERVAL_SECONDS = 2
DELAY_DURATION_SECONDS = 120 # 2 minutes
POINTS_PER_UPDATE = 5 # Speed control

# ================== DYNAMIC BUS GENERATION ==================

def get_all_route_keys_from_server():
    """Fetch the complete list of route keys from the server."""
    try:
        response = requests.get(GET_ALL_ROUTES_URL, timeout=10)
        if response.status_code == 200:
            print(f"✅ Successfully fetched {len(response.json())} route keys from server.")
            return response.json()
        else:
            print(f"❌ Failed to fetch route keys from server. Status: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not connect to server to get route keys: {e}")
        return None

ALL_BUSES = []

# ==========================================================

def get_bearing(lat1, lon1, lat2, lon2):
    dLon = math.radians(lon2 - lon1)
    lat1, lat2 = math.radians(lat1), math.radians(lat2)
    y = math.sin(dLon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360

def setup_bus_routes(all_route_keys):
    print("Setting up simulator: Fetching routes from server...")
    bus_routes = {}
    total_routes = len(all_route_keys)
    for i, route_key in enumerate(all_route_keys):
        print(f"--> Fetching route {i+1}/{total_routes}: {route_key}")
        try:
            start, end = route_key.split('-')
            # Increased timeout for very complex routes
            response = requests.get(f"{GET_ROUTE_URL}?start={start}&end={end}", timeout=45)
            if response.status_code == 200:
                route_data = response.json().get('route_points')
                if route_data:
                    bus_routes[route_key] = [(point['lat'], point['lng']) for point in route_data]
                else: print(f"⚠️ Route data empty for {route_key}")
            else:
                print(f"❌ Error fetching route '{route_key}': Server responded with {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Connection error while fetching {route_key}: {e}")
        
        # FINAL FIX: Increased pause to 2.5 seconds to respect the API rate limit and prevent timeouts.
        time.sleep(2.5) 
    print("-" * 30)
    return bus_routes

def run_simulator():
    all_route_keys = get_all_route_keys_from_server()
    if not all_route_keys:
        print("Could not get routes from server. Is server.py running? Shutting down.")
        sys.exit(1)

    bus_number_counter = 1001
    for route_key in all_route_keys:
        for status in ["On Time", "Delayed"]:
            ALL_BUSES.append({
                "id": f"HRBUS{bus_number_counter}", "number": f"HR-55-{bus_number_counter}",
                "routeKey": route_key, "status": status
            })
            bus_number_counter += 1

    detailed_routes = setup_bus_routes(all_route_keys)
    if not detailed_routes:
        print("Failed to fetch any routes. Shutting down simulator.")
        sys.exit(1)

    bus_progress = {}
    for bus in ALL_BUSES:
        if bus['routeKey'] in detailed_routes:
            progress = { 'point_index': 0 }
            if bus['status'] == 'Delayed':
                progress['departure_time'] = datetime.now() + timedelta(seconds=DELAY_DURATION_SECONDS)
            bus_progress[bus['id']] = progress

    active_buses = [bus for bus in ALL_BUSES if bus['routeKey'] in detailed_routes]
    print(f"✅ Simulator is live! Tracking {len(active_buses)} buses...")
    print(f"Sending updates to {UPDATE_LOCATION_URL}...")
    print("-" * 30)

    while True:
        for bus in active_buses:
            bus_id = bus['id']
            route_key = bus['routeKey']
            progress = bus_progress[bus_id]
            
            if 'departure_time' in progress and datetime.now() < progress['departure_time']:
                pass 
            else:
                current_point_index = progress['point_index']
                route_length = len(detailed_routes[route_key])
                next_point_index = (current_point_index + POINTS_PER_UPDATE) % route_length
                progress['point_index'] = next_point_index

            current_point_index = progress['point_index']
            route_points = detailed_routes[route_key]
            current_lat, current_lon = route_points[current_point_index]
            
            next_point_index_for_bearing = (current_point_index + 1) % len(route_points)
            next_lat, next_lon = route_points[next_point_index_for_bearing]
            bearing = get_bearing(current_lat, current_lon, next_lat, next_lon)

            data_to_send = {"bus_id": bus_id, "number": bus['number'], "routeKey": route_key, "latitude": current_lat, "longitude": current_lon, "status": bus['status'], "bearing": bearing}
            try:
                requests.post(UPDATE_LOCATION_URL, json=data_to_send, timeout=2)
            except requests.exceptions.RequestException:
                print(f"Error: Could not connect to the server.")

        print(f"All {len(active_buses)} bus locations updated.")
        time.sleep(UPDATE_INTERVAL_SECONDS)

if __name__ == '__main__':
    run_simulator()