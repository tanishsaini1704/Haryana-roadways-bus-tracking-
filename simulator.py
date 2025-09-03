import requests
import time
import math
import sys
import random
from datetime import datetime, timedelta

# --- Configuration ---
SERVER_BASE_URL = "http://127.0.0.1:5000"
UPDATE_LOCATION_URL = f"{SERVER_BASE_URL}/update_location"
GET_ROUTE_URL = f"{SERVER_BASE_URL}/get_route"
GET_ALL_ROUTES_URL = f"{SERVER_BASE_URL}/get_all_routes"
UPDATE_INTERVAL_SECONDS = 2
DELAY_DURATION_SECONDS = 120
POINTS_PER_UPDATE = 5

def get_all_route_keys_from_server():
    try:
        response = requests.get(GET_ALL_ROUTES_URL, timeout=10)
        if response.status_code == 200:
            print(f"✅ Successfully fetched {len(response.json())} route keys from server.")
            return response.json()
        return None
    except requests.exceptions.RequestException: return None

ALL_BUSES = []

def haversine(lat1, lon1, lat2, lon2):
    R = 6371; dLat, dLon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

def get_bearing(lat1, lon1, lat2, lon2):
    dLon = math.radians(lon2 - lon1); lat1, lat2 = math.radians(lat1), math.radians(lat2)
    y = math.sin(dLon) * math.cos(lat2)
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(lat2) * math.cos(dLon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360

def setup_bus_routes(all_route_keys):
    print("Setting up simulator: Fetching routes from server...")
    bus_routes = {}
    for i, route_key in enumerate(all_route_keys):
        print(f"--> Fetching route {i+1}/{len(all_route_keys)}: {route_key}")
        try:
            start, end = route_key.split('-')
            response = requests.get(f"{GET_ROUTE_URL}?start={start}&end={end}", timeout=45)
            if response.status_code == 200:
                data = response.json()
                if data.get('route_points'):
                    bus_routes[route_key] = {
                        "points": [(p['lat'], p['lng']) for p in data['route_points']],
                        "stops": data['stops']
                    }
                else: print(f"⚠️ Route data empty for {route_key}")
            else: print(f"❌ Error fetching route '{route_key}': Server responded with {response.status_code}")
        except requests.exceptions.RequestException as e: print(f"❌ Connection error while fetching {route_key}: {e}")
        time.sleep(1.5)
    print("-" * 30)
    return bus_routes

def run_simulator():
    all_route_keys = get_all_route_keys_from_server()
    if not all_route_keys: sys.exit("Could not get routes from server. Shutting down.")

    bus_number_counter = 1001
    for route_key in all_route_keys:
        for status in ["On Time", "Delayed"]:
            ALL_BUSES.append({
                "id": f"HRBUS{bus_number_counter}", "number": f"HR-55-{bus_number_counter}",
                "routeKey": route_key, "status": status,
                "bus_type": random.choice(['Ordinary', 'AC Express', 'Volvo']),
                "seat_status": "Seats Available"
            })
            bus_number_counter += 1

    detailed_routes = setup_bus_routes(all_route_keys)
    if not detailed_routes: sys.exit("Failed to fetch any routes. Shutting down.")

    bus_progress = {}
    for bus in ALL_BUSES:
        if bus['routeKey'] in detailed_routes:
            progress = { 'point_index': 0, 'stop_index': 0 }
            if bus['status'] == 'Delayed':
                progress['departure_time'] = datetime.now() + timedelta(seconds=DELAY_DURATION_SECONDS)
            bus_progress[bus['id']] = progress

    active_buses = [bus for bus in ALL_BUSES if bus['routeKey'] in detailed_routes]
    print(f"✅ Ultimate Simulator is live! Tracking {len(active_buses)} buses...")

    while True:
        for bus in active_buses:
            bus_id, route_key = bus['id'], bus['routeKey']
            progress = bus_progress[bus_id]
            route_info = detailed_routes[route_key]
            
            if 'departure_time' in progress and datetime.now() < progress['departure_time']:
                pass 
            else:
                progress['point_index'] = (progress['point_index'] + POINTS_PER_UPDATE) % len(route_info['points'])

            current_lat, current_lon = route_info['points'][progress['point_index']]
            
            # --- BUG FIX: New, more reliable logic for finding the next stop ---
            stops = route_info['stops']
            # Find the distance from the bus to every stop on its route
            distances_to_stops = [ (i, haversine(current_lat, current_lon, stop['lat'], stop['lng'])) for i, stop in enumerate(stops) ]
            
            # Filter out stops that the bus has already passed (are too close behind it)
            # and find the index of the closest one that is still ahead.
            min_dist = float('inf')
            next_stop_index = progress['stop_index']
            
            # Start checking from the current stop index
            for i in range(len(stops)):
                potential_index = (progress['stop_index'] + i) % len(stops)
                stop_dist = distances_to_stops[potential_index][1]
                if stop_dist < min_dist:
                    min_dist = stop_dist
                    next_stop_index = potential_index

            # If the bus is very close to this "next stop", it means it has arrived.
            # So, we'll advance the target to the *following* stop.
            if min_dist < 2: # 2km arrival threshold
                next_stop_index = (next_stop_index + 1) % len(stops)
                # Change seat status on arrival
                bus['seat_status'] = random.choice(['Seats Available', 'Filling Fast', 'Full'])
            
            progress['stop_index'] = next_stop_index
            next_stop = stops[next_stop_index]
            # --- END OF BUG FIX ---

            next_point_for_bearing = route_info['points'][(progress['point_index'] + 1) % len(route_info['points'])]
            bearing = get_bearing(current_lat, current_lon, next_point_for_bearing[0], next_point_for_bearing[1])

            data_to_send = { "id": bus_id, "number": bus['number'], "routeKey": route_key, "latitude": current_lat, "longitude": current_lon, "status": bus['status'], "bearing": bearing, "bus_type": bus['bus_type'], "seat_status": bus['seat_status'], "next_stop": next_stop }
            try: requests.post(UPDATE_LOCATION_URL, json=data_to_send, timeout=2)
            except requests.exceptions.RequestException: pass

        print(f"All {len(active_buses)} bus locations updated.")
        time.sleep(UPDATE_INTERVAL_SECONDS)

if __name__ == '__main__':
    run_simulator()