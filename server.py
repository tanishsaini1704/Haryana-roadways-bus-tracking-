from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

bus_data = {}

# ================== ZYADA ROUTES WALA DATA ==================
routes = {
    ('chandigarh', 'gurgaon'): [ {"lat": 30.7333, "lng": 76.7794}, {"lat": 30.3782, "lng": 76.7767}, {"lat": 29.6857, "lng": 76.9905}, {"lat": 29.3909, "lng": 76.9635}, {"lat": 28.9931, "lng": 77.0151}, {"lat": 28.4595, "lng": 77.0266} ],
    ('ambala', 'hisar'): [ {"lat": 30.3782, "lng": 76.7767}, {"lat": 29.9697, "lng": 76.8783}, {"lat": 29.5876, "lng": 76.0987}, {"lat": 29.1492, "lng": 75.7217} ],
    ('rohtak', 'faridabad'): [ {"lat": 28.8955, "lng": 76.6066}, {"lat": 28.7234, "lng": 76.4321}, {"lat": 28.5876, "lng": 76.3456}, {"lat": 28.4595, "lng": 77.0266}, {"lat": 28.4089, "lng": 77.3178} ],
    ('karnal', 'sonipat'): [ {"lat": 29.6857, "lng": 76.9905}, {"lat": 29.3909, "lng": 76.9635}, {"lat": 28.9931, "lng": 77.0151} ],
    ('panipat', 'yamunanagar'): [ {"lat": 29.3909, "lng": 76.9635}, {"lat": 29.6857, "lng": 76.9905}, {"lat": 29.9697, "lng": 76.8783}, {"lat": 30.1678, "lng": 77.2835} ],
    ('hisar', 'sirsa'): [ {"lat": 29.1492, "lng": 75.7217}, {"lat": 29.3210, "lng": 75.8765}, {"lat": 29.5372, "lng": 75.0234} ],
    ('gurgaon', 'rewari'): [ {"lat": 28.4595, "lng": 77.0266}, {"lat": 28.3184, "lng": 76.8615}, {"lat": 28.1919, "lng": 76.6195} ]
}
# ==============================================================================

# Reverse routes automatically banayein
keys_to_add = {}
for start, end in routes:
    reverse_key = (end, start)
    if reverse_key not in routes:
        keys_to_add[reverse_key] = routes[(start, end)][::-1]
routes.update(keys_to_add)


@app.route('/get_route')
def get_route():
    start = request.args.get('start', '').lower()
    end = request.args.get('end', '').lower()
    if not start or not end:
        return jsonify({'error': 'Missing start or end city'}), 400
    
    available_cities = set([k[0] for k in routes.keys()] + [k[1] for k in routes.keys()])
    if start not in available_cities or end not in available_cities:
        return jsonify({'error': 'City not found in routes'}), 404
        
    key = (start, end)
    if key not in routes:
        return jsonify({'error': 'Direct route not found'}), 404
    return jsonify({'route': routes[key]})

@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.get_json()
    required_fields = ['bus_id', 'latitude', 'longitude', 'status', 'bearing', 'number', 'routeKey']
    if not data or not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    bus_id = data['bus_id']
    bus_data[bus_id] = {
        'id': bus_id, 'number': data['number'], 'routeKey': data['routeKey'],
        'latitude': float(data['latitude']), 'longitude': float(data['longitude']),
        'status': data['status'], 'bearing': float(data['bearing']),
        'last_updated': datetime.utcnow().isoformat() + 'Z'
    }
    return jsonify({'message': f'Location updated for bus {bus_id}'}), 200

@app.route('/get_live_buses')
def get_live_buses():
    return jsonify(list(bus_data.values()))

if __name__ == '__main__':
    print("Flask server http://127.0.0.1:5000 par chalu ho raha hai...")
    app.run(host='0.0.0.0', port=5000, debug=False)
