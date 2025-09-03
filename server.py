from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import openrouteservice
import json
import os
import math

app = Flask(__name__)
CORS(app)

# ================== CONFIGURATION ==================
ors_client = openrouteservice.Client(key='eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjUxMmNkZDYxZmNhMzRjYzRiODViYjg1MGUwMDg1YzRjIiwiaCI6Im11cm11cjY0In0=')
CACHE_FILE = 'route_cache.json'
# ===================================================

bus_data = {}

# --- Caching Logic ---
def load_cache_from_disk():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            print(f"Loading existing routes from {CACHE_FILE}...")
            return json.load(f)
    return {}

def save_route_to_cache(key, data):
    route_cache[key] = data
    with open(CACHE_FILE, 'w') as f:
        json.dump(route_cache, f, indent=2)
    print(f"Route '{key}' saved to persistent cache.")

route_cache = load_cache_from_disk()

# --- Data Dictionaries (Complete) ---
BUS_STAND_COORDINATES = {
    'chandigarh': (76.7849, 30.7426), 'gurgaon': (77.0315, 28.4698), 'ambala': (76.8188, 30.3622),
    'hisar': (75.7135, 29.1575), 'rohtak': (76.6215, 28.8951), 'faridabad': (77.307, 28.3965),
    'karnal': (76.9838, 29.6934), 'sonipat': (77.0143, 28.9953), 'panipat': (76.9748, 29.3881),
    'yamunanagar': (77.2798, 30.133), 'sirsa': (75.0318, 29.5358), 'rewari': (76.6242, 28.1918),
    'kurukshetra': (76.8370, 29.9690), 'kaithal': (76.3965, 29.8000), 'jind': (76.3160, 29.3200),
    'jhajjar': (76.6550, 28.6100), 'fatehabad': (75.4540, 29.5130), 'manesar': (76.9400, 28.3500),
    'maheshnagar':(76.8430, 30.3550), 'saha': (76.9850, 30.2930), 'mullana': (77.0315, 30.2520),
    'dosarka': (77.1000, 30.2200), 'dhin': (77.1550, 30.2000), 'thanachappar':(77.1850, 30.1950),
    'kail': (77.2400, 30.1800), 'jagadhri': (77.2950, 30.1700)
}
HIGHWAY_WAYPOINT_COORDINATES = {
    'ambala': (76.853, 30.349), 'kurukshetra': (76.871, 29.967), 'karnal': (76.990, 29.722),
    'panipat': (76.971, 29.414), 'sonipat': (77.022, 29.015), 'hisar': (75.71, 29.15),
    'rohtak': (76.62, 28.89), 'faridabad': (77.31, 28.40), 'sirsa': (75.03, 29.53),
    'rewari': (76.62, 28.19), 'kaithal': (76.41, 29.79), 'jind': (76.32, 29.31),
    'jhajjar': (76.66, 28.61), 'fatehabad': (75.46, 29.51), 'manesar': (76.94, 28.35),
    'gurgaon': (77.03, 28.46), 'yamunanagar': (77.28, 30.13), 'maheshnagar':(76.8465, 30.3520),
    'saha': (76.9845, 30.2925), 'mullana': (77.031, 30.252), 'dosarka': (77.1020, 30.2185),
    'dhin': (77.1550, 30.2000), 'thanachappar':(77.185, 30.195), 'kail': (77.2400, 30.1800),
    'jagadhri': (77.2980, 30.1690)
}
ROUTE_WAYPOINTS = { # User's Special Route (Preserved)
    'ambala-yamunanagar': ['maheshnagar', 'saha', 'mullana', 'dosarka', 'dhin', 'thanachappar', 'kail', 'jagadhri'],
    # Mainline Routes
    'chandigarh-gurgaon': ['ambala', 'kurukshetra', 'karnal', 'panipat', 'sonipat'],
    'hisar-sirsa': ['fatehabad'], 'gurgaon-rewari': ['manesar'],
    # Expanded Network
    'ambala-chandigarh': [], 'ambala-faridabad': ['kurukshetra', 'karnal', 'panipat', 'sonipat'],
    'ambala-fatehabad': ['kaithal', 'hisar'], 'ambala-gurgaon': ['kurukshetra', 'karnal', 'panipat', 'sonipat'],
    'ambala-hisar': ['kaithal', 'jind'], 'ambala-jhajjar': ['kurukshetra', 'panipat', 'rohtak'],
    'ambala-jind': ['kaithal'], 'ambala-kaithal': [], 'ambala-karnal': ['kurukshetra'],
    'ambala-kurukshetra': [], 'ambala-manesar': ['kurukshetra', 'karnal', 'panipat', 'sonipat', 'gurgaon'],
    'ambala-panipat': ['kurukshetra', 'karnal'], 'ambala-rewari': ['kurukshetra', 'karnal', 'panipat', 'sonipat', 'gurgaon'],
    'ambala-rohtak': ['kurukshetra', 'panipat'], 'ambala-sirsa': ['kaithal', 'hisar', 'fatehabad'],
    'ambala-sonipat': ['kurukshetra', 'karnal', 'panipat'],
    'chandigarh-faridabad': ['ambala', 'karnal', 'panipat', 'sonipat'], 'chandigarh-fatehabad': ['ambala', 'kaithal', 'hisar'],
    'chandigarh-hisar': ['ambala', 'kaithal'], 'chandigarh-jhajjar': ['ambala', 'panipat', 'rohtak'],
    'chandigarh-jind': ['ambala', 'kaithal'], 'chandigarh-kaithal': ['ambala'],
    'chandigarh-karnal': ['ambala', 'kurukshetra'], 'chandigarh-kurukshetra': ['ambala'],
    'chandigarh-manesar': ['ambala', 'karnal', 'panipat', 'sonipat', 'gurgaon'], 'chandigarh-panipat': ['ambala', 'kurukshetra', 'karnal'],
    'chandigarh-rewari': ['ambala', 'karnal', 'panipat', 'sonipat', 'gurgaon'], 'chandigarh-rohtak': ['ambala', 'panipat'],
    'chandigarh-sirsa': ['ambala', 'kaithal', 'hisar', 'fatehabad'], 'chandigarh-sonipat': ['ambala', 'karnal', 'panipat'],
    'chandigarh-yamunanagar': ['ambala'],
    'faridabad-fatehabad': ['gurgaon', 'rohtak', 'hisar'], 'faridabad-hisar': ['gurgaon', 'rohtak'],
    'faridabad-jhajjar': ['gurgaon', 'rohtak'], 'faridabad-jind': ['gurgaon', 'rohtak', 'hisar'],
    'faridabad-kaithal': ['gurgaon', 'rohtak', 'hisar', 'jind'], 'faridabad-karnal': ['gurgaon', 'sonipat', 'panipat'],
    'faridabad-kurukshetra': ['gurgaon', 'sonipat', 'panipat', 'karnal'], 'faridabad-manesar': ['gurgaon'],
    'faridabad-panipat': ['gurgaon', 'sonipat'], 'faridabad-rewari': ['gurgaon', 'manesar'],
    'faridabad-rohtak': ['gurgaon'], 'faridabad-sirsa': ['gurgaon', 'rohtak', 'hisar', 'fatehabad'],
    'faridabad-sonipat': ['gurgaon'], 'faridabad-yamunanagar': ['gurgaon', 'sonipat', 'panipat', 'karnal'],
    'fatehabad-gurgaon': ['hisar', 'rohtak', 'gurgaon'], 'fatehabad-jhajjar': ['hisar', 'rohtak'],
    'fatehabad-jind': ['hisar'], 'fatehabad-kaithal': ['hisar'], 'fatehabad-karnal': ['hisar', 'jind', 'panipat'],
    'fatehabad-kurukshetra': ['hisar', 'kaithal', 'kurukshetra'], 'fatehabad-manesar': ['hisar', 'rohtak', 'gurgaon'],
    'fatehabad-panipat': ['hisar', 'jind'], 'fatehabad-rewari': ['hisar', 'rohtak', 'jhajjar'],
    'fatehabad-rohtak': ['hisar'], 'fatehabad-sonipat': ['hisar', 'rohtak'],
    'gurgaon-fatehabad': ['rohtak', 'hisar'], 'gurgaon-hisar': ['rohtak'],
    'gurgaon-jhajjar': ['rohtak'], 'gurgaon-jind': ['rohtak', 'hisar'],
    'gurgaon-kaithal': ['rohtak', 'hisar', 'jind'], 'gurgaon-karnal': ['sonipat', 'panipat'],
    'gurgaon-kurukshetra': ['sonipat', 'panipat', 'karnal'], 'gurgaon-panipat': ['sonipat'],
    'gurgaon-rohtak': [], 'gurgaon-sirsa': ['rohtak', 'hisar', 'fatehabad'],
    'gurgaon-sonipat': [], 'gurgaon-yamunanagar': ['sonipat', 'panipat', 'karnal'],
    'hisar-jhajjar': ['rohtak'], 'hisar-jind': [], 'hisar-kaithal': [],
    'hisar-karnal': ['jind', 'panipat'], 'hisar-kurukshetra': ['kaithal'],
    'hisar-manesar': ['rohtak', 'gurgaon'], 'hisar-panipat': ['jind'],
    'hisar-rewari': ['rohtak', 'jhajjar'], 'hisar-rohtak': [],
    'hisar-sonipat': ['rohtak'], 'hisar-yamunanagar': ['jind', 'panipat', 'karnal'],
    'jhajjar-jind': ['rohtak'], 'jhajjar-kaithal': ['rohtak', 'hisar'],
    'jhajjar-karnal': ['rohtak', 'panipat'], 'jhajjar-kurukshetra': ['rohtak', 'panipat', 'karnal'],
    'jhajjar-manesar': ['gurgaon'], 'jhajjar-panipat': ['rohtak'],
    'jhajjar-rewari': [], 'jhajjar-sirsa': ['rohtak', 'hisar', 'fatehabad'],
    'jhajjar-sonipat': ['rohtak'], 'jhajjar-yamunanagar': ['rohtak', 'panipat', 'karnal'],
    'jind-kaithal': [], 'jind-karnal': ['panipat'], 'jind-kurukshetra': ['kaithal'],
    'jind-manesar': ['rohtak', 'gurgaon'], 'jind-panipat': [], 'jind-rewari': ['rohtak', 'jhajjar'],
    'jind-rohtak': [], 'jind-sirsa': ['hisar', 'fatehabad'], 'jind-sonipat': ['rohtak'],
    'jind-yamunanagar': ['panipat', 'karnal'], 'kaithal-karnal': ['kurukshetra'],
    'kaithal-kurukshetra': [], 'kaithal-manesar': ['jind', 'rohtak', 'gurgaon'],
    'kaithal-panipat': ['jind'], 'kaithal-rewari': ['jind', 'rohtak', 'jhajjar'],
    'kaithal-rohtak': ['jind'], 'kaithal-sirsa': ['hisar', 'fatehabad'],
    'kaithal-sonipat': ['jind', 'rohtak'], 'kaithal-yamunanagar': ['kurukshetra', 'karnal'],
    'karnal-kurukshetra': [], 'karnal-manesar': ['panipat', 'sonipat', 'gurgaon'],
    'karnal-panipat': [], 'karnal-rewari': ['panipat', 'sonipat', 'gurgaon'],
    'karnal-rohtak': ['panipat'], 'karnal-sirsa': ['panipat', 'jind', 'hisar', 'fatehabad'],
    'kurukshetra-manesar': ['karnal', 'panipat', 'sonipat', 'gurgaon'], 'kurukshetra-panipat': ['karnal'],
    'kurukshetra-rewari': ['karnal', 'panipat', 'sonipat', 'gurgaon'], 'kurukshetra-rohtak': ['karnal', 'panipat'],
    'kurukshetra-sirsa': ['kaithal', 'hisar', 'fatehabad'], 'kurukshetra-sonipat': ['karnal', 'panipat'],
    'manesar-panipat': ['gurgaon', 'sonipat'], 'manesar-rewari': [],
    'manesar-rohtak': ['jhajjar'], 'manesar-sirsa': ['gurgaon', 'jhajjar', 'rohtak', 'hisar', 'fatehabad'],
    'manesar-sonipat': ['gurgaon'], 'manesar-yamunanagar': ['gurgaon', 'sonipat', 'panipat', 'karnal'],
    'panipat-rewari': ['sonipat', 'gurgaon'], 'panipat-rohtak': [], 'panipat-sirsa': ['jind', 'hisar', 'fatehabad'],
    'rewari-rohtak': ['jhajjar'], 'rewari-sirsa': ['jhajjar', 'rohtak', 'hisar', 'fatehabad'],
    'rewari-sonipat': ['gurgaon'], 'rewari-yamunanagar': ['gurgaon', 'sonipat', 'panipat', 'karnal'],
    'rohtak-sirsa': ['hisar', 'fatehabad'], 'rohtak-sonipat': [],
    'sirsa-sonipat': ['hisar','rohtak'], }

# --- Automatically generate reverse routes ---
final_waypoints = {}
for key, waypoints in ROUTE_WAYPOINTS.items():
    final_waypoints[key] = waypoints; start, end = key.split('-'); reverse_key = f"{end}-{start}"
    if reverse_key not in ROUTE_WAYPOINTS: final_waypoints[reverse_key] = waypoints[::-1]
ROUTE_WAYPOINTS = final_waypoints

# --- Data for extra features ---
BUS_STAND_INFO = {
    'chandigarh': { 'name': 'Chandigarh ISBT-17', 'facilities': 'AC Waiting Room, Food Court, Cloak Room', 'routes': ['Gurgaon', 'Delhi', 'Hisar', 'Yamunanagar'] },
    'gurgaon':    { 'name': 'Gurugram ISBT', 'facilities': 'Metro Connectivity, Food Stalls, Washrooms', 'routes': ['Chandigarh', 'Jaipur', 'Faridabad', 'Rohtak'] },
    'hisar':      { 'name': 'Hisar ISBT', 'facilities': 'Waiting Hall, Book Stall, Local Bus Service', 'routes': ['Sirsa', 'Chandigarh', 'Delhi', 'Rohtak'] },
    'rohtak':     { 'name': 'Rohtak ISBT', 'facilities': 'Medical Room, Police Booth, Food Court', 'routes': ['Faridabad', 'Hisar', 'Delhi', 'Gurgaon'] },
    'ambala':     { 'name': 'Ambala Cantt', 'facilities': 'Railway Station Nearby, Food Stalls', 'routes': ['Chandigarh', 'Delhi', 'Yamunanagar'] },
}

# --- Helper functions ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371; dLat, dLon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

# --- API Endpoints ---
@app.route('/get_all_routes')
def get_all_routes(): return jsonify(list(ROUTE_WAYPOINTS.keys()))

@app.route('/get_route')
def get_route():
    start_city, end_city = request.args.get('start', '').lower(), request.args.get('end', '').lower()
    cache_key = f"{start_city}-{end_city}"
    if cache_key in route_cache: return jsonify(route_cache[cache_key])
    try:
        waypoint_cities = ROUTE_WAYPOINTS.get(cache_key, [])
        all_cities = [start_city] + waypoint_cities + [end_city]
        coords = []
        for i, city in enumerate(all_cities):
            if city not in BUS_STAND_COORDINATES: continue
            coords.append(BUS_STAND_COORDINATES[city] if i == 0 or i == len(all_cities) - 1 else HIGHWAY_WAYPOINT_COORDINATES.get(city, BUS_STAND_COORDINATES[city]))
        
        print(f"Fetching '{cache_key}' from API...")
        directions_result = ors_client.directions(coordinates=coords, profile='driving-hgv', format='geojson', instructions=False)
        summary = directions_result['features'][0]['properties']['summary']
        
        stops_info = []
        for i, city_name in enumerate(all_cities):
            if city_name in BUS_STAND_COORDINATES:
                lon, lat = BUS_STAND_COORDINATES[city_name] if i == 0 or i == len(all_cities) - 1 else HIGHWAY_WAYPOINT_COORDINATES.get(city_name, BUS_STAND_COORDINATES[city_name])
                stops_info.append({"name": city_name.capitalize(), "lat": lat, "lng": lon})
        
        final_response = {
            "route_points": [{"lat": lat, "lng": lon} for lon, lat in directions_result['features'][0]['geometry']['coordinates']],
            "stops": stops_info, "total_duration_seconds": summary['duration'], "total_distance_meters": summary['distance']
        }
        save_route_to_cache(cache_key, final_response)
        return jsonify(final_response)
    except Exception as e:
        print(f"Error fetching directions for {cache_key}: {e}")
        return jsonify({'error': 'An error occurred while fetching the route.'}), 500

@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.get_json(); bus_id = data.get('id')
    bus_data[bus_id] = {**data, 'last_updated': datetime.utcnow().isoformat() + 'Z'}
    return jsonify({'message': f'Location updated for bus {bus_id}'}), 200

@app.route('/get_live_buses')
def get_live_buses(): return jsonify(list(bus_data.values()))

@app.route('/find_nearby_stops')
def find_nearby_stops():
    try: user_lat, user_lon = float(request.args.get('lat')), float(request.args.get('lon'))
    except (TypeError, ValueError): return jsonify({'error': 'Invalid latitude/longitude'}), 400
    
    # Corrected list comprehension to handle the tuple format of BUS_STAND_COORDINATES
    stops_with_distance = [{"name": city.capitalize(), "id": city, "lat": coords[1], "lng": coords[0], 'distance_km': haversine(user_lat, user_lon, coords[1], coords[0])} for city, coords in BUS_STAND_COORDINATES.items()]
    
    return jsonify(sorted(stops_with_distance, key=lambda x: x['distance_km'])[:5])

@app.route('/calculate_fare')
def calculate_fare():
    start, end = request.args.get('start', '').lower(), request.args.get('end', '').lower()
    if not all(c in BUS_STAND_COORDINATES for c in [start, end]): return jsonify({'error': 'Invalid city names'}), 400
    start_coords, end_coords = BUS_STAND_COORDINATES[start], BUS_STAND_COORDINATES[end]
    distance = haversine(start_coords[1], start_coords[0], end_coords[1], end_coords[0])
    fares = {'Ordinary': distance * 1.25, 'AC Express': distance * 1.75, 'Volvo': distance * 2.50}
    return jsonify({'distance_km': round(distance), 'fares': fares})

@app.route('/get_bus_stand_details')
def get_bus_stand_details():
    city = request.args.get('city', '').lower()
    if city not in BUS_STAND_COORDINATES: return jsonify({'error': 'Invalid city name'}), 400
    info = BUS_STAND_INFO.get(city, { 'name': city.capitalize() + ' ISBT', 'facilities': 'Basic amenities available.', 'routes': ['Local and long-distance routes.'] })
    return jsonify({**info, 'lat': BUS_STAND_COORDINATES[city][1], 'lng': BUS_STAND_COORDINATES[city][0]})

if __name__ == '__main__':
    print("Ultimate Haryana Network Server is running on http://127.0.0.1:5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)