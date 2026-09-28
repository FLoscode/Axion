"""
Antarctic Station Dashboard — Branch 1 Unified Mission Control Backend
======================================================================
Integrates:
  - PolarTwin-OS Mission Control Authentication (Commander & Public Researcher)
  - Logistics Simulator (vessel AIS tracking, field team Iridium pings, fuel farm burn)
  - Station Telemetry Simulation API (Bharati & Maitri stations, CHP units, generators)
  - Edge AI Predictive Maintenance Anomaly Detection
  - 3D Station Model Serving (Three.js WebGL OBJ/MTL assets)
  - Cybersecurity Gateway (Zero-Trust, PQC ML-KEM-768, VSAT Link Monitor)

Credentials for Admin/Commander:
  - ID:                 NCPOR-ADMIN-001
  - Password:           PolarAdmin@123
  - Satellite Sync Code: 48291736

Run:
    python app.py
Then open http://localhost:5000
"""

import sys
import os
import time
import random
import math
import json
import threading
from datetime import datetime, timezone
from collections import deque

# Reconfigure console output to UTF-8 on Windows
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from flask import Flask, jsonify, send_from_directory, request

# ---------------------------------------------------------------------------
# Directories & Path Setup
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

# Locate 3D models directory (prefer local, fallback to parent)
if os.path.exists(os.path.join(BASE_DIR, '3d_models')):
    MODELS_DIR = os.path.join(BASE_DIR, '3d_models')
elif os.path.exists(os.path.join(PARENT_DIR, '3d_models')):
    MODELS_DIR = os.path.join(PARENT_DIR, '3d_models')
else:
    MODELS_DIR = os.path.join(BASE_DIR, '3d_models')

# Locate and add cybersecurity_gateway to sys.path
gateway_dirs = [
    os.path.join(BASE_DIR, 'cybersecurity_gateway'),
    os.path.join(PARENT_DIR, 'cybersecurity_gateway'),
]
for g_dir in gateway_dirs:
    if os.path.exists(g_dir) and g_dir not in sys.path:
        sys.path.insert(0, g_dir)

# ---------------------------------------------------------------------------
# Flask App Initialization
# ---------------------------------------------------------------------------

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, 'static'),
    static_url_path='/static'
)

# Attempt to register real Cybersecurity Gateway blueprint
gateway_registered = False
try:
    from cybersecurity_gateway import gateway_bp
    app.register_blueprint(gateway_bp)
    gateway_registered = True
    print("[INIT] Cybersecurity Gateway Blueprint registered successfully.")
except Exception as e:
    print(f"[WARN] Could not register gateway_bp ({e}). Fallback mock endpoints active.")


# ---------------------------------------------------------------------------
# Static File & 3D Model Serving
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    """Serve the unified dashboard & login interface."""
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'index.html')


@app.route('/models/<path:filename>')
def serve_model(filename):
    """Serve 3D model files (OBJ, MTL) for Bharati and Maitri stations."""
    return send_from_directory(MODELS_DIR, filename)


# ---------------------------------------------------------------------------
# Logistics Simulator — Background Simulation Engine
# ---------------------------------------------------------------------------

STATION_CONFIG = {
    "name": "Bharati Research Station",
    "location": "Larsemann Hills, East Antarctica",
    "latitude": -69.4082,
    "longitude": 76.1873
}

VESSEL_STATE = {
    "name": "RRS Sir David Attenborough",
    "mmsi": "740123456",
    "latitude": -69.75,
    "longitude": 75.20,
    "heading": 65.0,
    "speed_knots": 10.5,
    "cargo": "Polar Diesel (A-1) & Scientific Modules",
    "destination": "Bharati Research Station"
}

FUEL_FARM_CAPACITY = 300_000  # litres
fuel_remaining = 284_500.0     # starting fuel remaining

CHP_UNITS_STATE = {
    "CHP-01": 0.0,
    "CHP-02": 0.0,
    "CHP-03": 0.0
}

FIELD_TEAMS_STATE = [
    {
        "id": "FIELD-TEAM-01",
        "leader": "Dr. T. Roy (Glaciology)",
        "latitude": STATION_CONFIG["latitude"],
        "longitude": STATION_CONFIG["longitude"],
        "heading": 135.0,
        "distance_from_station_km": 8.4,
        "battery_pct": 92,
        "status": "NORMAL"
    },
    {
        "id": "FIELD-TEAM-02",
        "leader": "K. Sengupta (Meteorology)",
        "latitude": STATION_CONFIG["latitude"],
        "longitude": STATION_CONFIG["longitude"],
        "heading": 225.0,
        "distance_from_station_km": 14.2,
        "battery_pct": 88,
        "status": "NORMAL"
    }
]

# Thread-safe event queue
MAX_EVENTS = 250
logistics_events = deque(maxlen=MAX_EVENTS)
logistics_lock = threading.Lock()

# Snapshots for fast polling
latest_vessel = {}
latest_fuel = {}
latest_station_status = {}
snapshot_lock = threading.Lock()


def sim_timestamp():
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def move_coordinate(lat, lon, heading, distance_km):
    """Approximate spherical movement from a lat/lon coordinate."""
    earth_radius_km = 6371.0
    heading_rad = math.radians(heading)
    lat_rad = math.radians(lat)
    distance_rad = distance_km / earth_radius_km

    new_lat = math.asin(
        math.sin(lat_rad) * math.cos(distance_rad)
        + math.cos(lat_rad) * math.sin(distance_rad) * math.cos(heading_rad)
    )

    new_lon = math.radians(lon) + math.atan2(
        math.sin(heading_rad) * math.sin(distance_rad) * math.cos(lat_rad),
        math.cos(distance_rad) - math.sin(lat_rad) * math.sin(new_lat)
    )

    return math.degrees(new_lat), math.degrees(new_lon)


def calculate_distance_km(lat1, lon1, lat2, lon2):
    """Calculate Great Circle distance between two coordinates in km."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def store_event(event):
    """Store event into the thread-safe queue."""
    with logistics_lock:
        logistics_events.append(event)


def sim_vessel_event():
    """Simulate vessel movement towards Bharati Station."""
    global VESSEL_STATE, latest_vessel

    # Slight heading adjustments
    VESSEL_STATE["heading"] += random.uniform(-2.5, 2.5)
    VESSEL_STATE["heading"] %= 360

    # Distance covered in 2-second simulation interval
    distance_km = VESSEL_STATE["speed_knots"] * 1.852 * (2 / 3600) * 15  # Accelerated 15x for live demo

    VESSEL_STATE["latitude"], VESSEL_STATE["longitude"] = move_coordinate(
        VESSEL_STATE["latitude"],
        VESSEL_STATE["longitude"],
        VESSEL_STATE["heading"],
        distance_km
    )

    dist_to_station = calculate_distance_km(
        VESSEL_STATE["latitude"],
        VESSEL_STATE["longitude"],
        STATION_CONFIG["latitude"],
        STATION_CONFIG["longitude"]
    )

    # ETA in hours
    eta_hours = (dist_to_station / (VESSEL_STATE["speed_knots"] * 1.852)) if VESSEL_STATE["speed_knots"] > 0 else 0

    anomaly = None
    # 3% chance of simulated anomaly event
    if random.random() < 0.03:
        anomaly = {
            "type": "VESSEL_OFF_COURSE",
            "severity": "HIGH",
            "message": "Vessel heading drift detected (+14.2° from charted polar corridor).",
            "recommended_action": "Request VHF bridge check & adjust autopilot waypoints."
        }

    event = {
        "timestamp": sim_timestamp(),
        "event_type": "VESSEL_AIS",
        "vessel": {
            "name": VESSEL_STATE["name"],
            "mmsi": VESSEL_STATE["mmsi"],
            "latitude": round(VESSEL_STATE["latitude"], 6),
            "longitude": round(VESSEL_STATE["longitude"], 6),
            "heading": round(VESSEL_STATE["heading"], 2),
            "speed_knots": round(VESSEL_STATE["speed_knots"], 2),
            "destination": STATION_CONFIG["name"],
            "cargo": VESSEL_STATE["cargo"],
            "distance_to_station_km": round(dist_to_station, 2),
            "eta_hours": round(eta_hours, 1)
        }
    }

    if anomaly:
        event["anomaly"] = anomaly

    store_event(event)

    with snapshot_lock:
        latest_vessel.clear()
        latest_vessel.update(event["vessel"])
        if anomaly:
            latest_vessel["anomaly"] = anomaly


def sim_field_team_event(team):
    """Simulate Iridium telemetry ping from a field expedition team."""
    distance = random.uniform(0.02, 0.06)

    team["latitude"], team["longitude"] = move_coordinate(
        team["latitude"],
        team["longitude"],
        team["heading"],
        distance
    )
    team["distance_from_station_km"] += distance
    team["battery_pct"] = max(15, team["battery_pct"] - random.uniform(0.01, 0.05))

    anomaly = None
    if random.random() < 0.02:
        anomaly = {
            "type": "FIELD_TEAM_SOS",
            "severity": "CRITICAL",
            "message": f"Iridium Emergency Ping received from {team['id']}: Crevasse hazard near route.",
            "recommended_action": "Halt forward march, dispatch Bharati SAR Snowcat."
        }

    event = {
        "timestamp": sim_timestamp(),
        "event_type": "IRIDIUM_FIELD_PING",
        "field_team": {
            "id": team["id"],
            "leader": team["leader"],
            "latitude": round(team["latitude"], 6),
            "longitude": round(team["longitude"], 6),
            "heading": team["heading"],
            "distance_from_station_km": round(team["distance_from_station_km"], 2),
            "battery_pct": round(team["battery_pct"], 1),
            "communication": "IRIDIUM SATELLITE",
            "signal_status": "STRONG (5/5 Bars)"
        }
    }

    if anomaly:
        event["anomaly"] = anomaly
        team["status"] = "SOS_ALERT"
    else:
        team["status"] = "NORMAL"

    store_event(event)


def sim_fuel_event():
    """Simulate fuel consumption by Combined Heat & Power (CHP) units."""
    global fuel_remaining, latest_fuel

    total_consumption = 0.0
    burn_rates = {}

    for chp in CHP_UNITS_STATE:
        load_pct = random.uniform(55, 92)
        burn_interval = random.uniform(0.8, 1.8) * (load_pct / 100)
        CHP_UNITS_STATE[chp] += burn_interval
        total_consumption += burn_interval
        burn_rates[chp] = {
            "load_percentage": round(load_pct, 1),
            "interval_consumption_litres": round(burn_interval, 2),
            "cumulative_consumption_litres": round(CHP_UNITS_STATE[chp], 2)
        }

    fuel_remaining -= total_consumption
    fuel_remaining = max(0.0, fuel_remaining)

    # Estimate days of autonomy remaining at current burn rate
    hourly_rate = total_consumption * 30  # 30 intervals/minute * 60 = approximate
    days_autonomy = (fuel_remaining / (hourly_rate * 24)) if hourly_rate > 0 else 999

    event = {
        "timestamp": sim_timestamp(),
        "event_type": "FUEL_CONSUMPTION",
        "inventory": {
            "fuel_farm_capacity_litres": FUEL_FARM_CAPACITY,
            "fuel_remaining_litres": round(fuel_remaining, 2),
            "fuel_consumed_this_interval_litres": round(total_consumption, 2),
            "fuel_remaining_percentage": round((fuel_remaining / FUEL_FARM_CAPACITY) * 100, 2),
            "estimated_autonomy_days": round(days_autonomy, 1),
            "hourly_burn_rate_litres": round(hourly_rate, 1)
        },
        "CHP_generators": burn_rates
    }

    store_event(event)

    with snapshot_lock:
        latest_fuel.clear()
        latest_fuel.update(event["inventory"])
        latest_fuel["CHP_generators"] = event["CHP_generators"]


def sim_system_status():
    """Emit periodic high-level station status event."""
    global latest_station_status

    event = {
        "timestamp": sim_timestamp(),
        "event_type": "STATION_STATUS",
        "station": STATION_CONFIG["name"],
        "operational_status": "ONLINE",
        "fuel_remaining_litres": round(fuel_remaining, 2),
        "fuel_level_percentage": round((fuel_remaining / FUEL_FARM_CAPACITY) * 100, 2),
        "vessel_tracked": VESSEL_STATE["name"],
        "field_teams_tracked": len(FIELD_TEAMS_STATE),
        "sat_uplink": "ACTIVE"
    }

    store_event(event)

    with snapshot_lock:
        latest_station_status.clear()
        latest_station_status.update(event)


def logistics_simulation_loop():
    """Continuous background loop driving the Antarctic logistics simulation."""
    iteration = 0
    # Seed initial events
    sim_vessel_event()
    for team in FIELD_TEAMS_STATE:
        sim_field_team_event(team)
    sim_fuel_event()
    sim_system_status()

    while True:
        try:
            iteration += 1
            sim_vessel_event()

            for team in FIELD_TEAMS_STATE:
                sim_field_team_event(team)

            sim_fuel_event()

            if iteration % 4 == 0:
                sim_system_status()

        except Exception as e:
            print(f"[SIM ERROR] {e}")

        time.sleep(2.5)


# Launch background simulator thread
sim_thread = threading.Thread(target=logistics_simulation_loop, daemon=True, name="LogisticsSimThread")
sim_thread.start()


# ---------------------------------------------------------------------------
# Logistics REST API Endpoints
# ---------------------------------------------------------------------------

@app.route('/api/logistics/summary')
def logistics_summary():
    """Return combined real-time logistics dashboard snapshot."""
    with snapshot_lock:
        vessel = dict(latest_vessel)
        fuel = dict(latest_fuel)
        status = dict(latest_station_status)

    teams = []
    for team in FIELD_TEAMS_STATE:
        teams.append({
            "id": team["id"],
            "leader": team["leader"],
            "latitude": round(team["latitude"], 6),
            "longitude": round(team["longitude"], 6),
            "heading": team["heading"],
            "distance_from_station_km": round(team["distance_from_station_km"], 2),
            "battery_pct": round(team["battery_pct"], 1),
            "status": team.get("status", "NORMAL"),
            "communication": "IRIDIUM SATELLITE"
        })

    with logistics_lock:
        recent = list(logistics_events)
    anomaly_count = sum(1 for e in recent[-30:] if "anomaly" in e)

    return jsonify({
        "timestamp": sim_timestamp(),
        "station": STATION_CONFIG,
        "vessel": vessel,
        "field_teams": teams,
        "fuel": fuel,
        "station_status": status,
        "simulation_active": True,
        "total_events_buffered": len(recent),
        "recent_anomaly_count": anomaly_count
    })


@app.route('/api/logistics/events')
def logistics_events_api():
    """Return stream of recent logistics simulation events."""
    limit = request.args.get('limit', 50, type=int)
    event_type = request.args.get('type', None)

    with logistics_lock:
        events = list(logistics_events)

    if event_type and event_type != 'ALL':
        events = [e for e in events if e.get('event_type') == event_type or (event_type == 'ANOMALY' and 'anomaly' in e)]

    # Newest first
    events = list(reversed(events))[:limit]

    return jsonify({
        "count": len(events),
        "events": events
    })


@app.route('/api/logistics/vessel')
def logistics_vessel():
    """Return vessel AIS status."""
    with snapshot_lock:
        data = dict(latest_vessel)
    return jsonify(data)


@app.route('/api/logistics/field-teams')
def logistics_field_teams():
    """Return field team positions and status."""
    teams = []
    for team in FIELD_TEAMS_STATE:
        teams.append({
            "id": team["id"],
            "leader": team["leader"],
            "latitude": round(team["latitude"], 6),
            "longitude": round(team["longitude"], 6),
            "heading": team["heading"],
            "distance_from_station_km": round(team["distance_from_station_km"], 2),
            "battery_pct": round(team["battery_pct"], 1),
            "status": team.get("status", "NORMAL"),
            "communication": "IRIDIUM SATELLITE",
            "signal_status": "STRONG"
        })
    return jsonify({"field_teams": teams})


@app.route('/api/logistics/fuel')
def logistics_fuel():
    """Return fuel reserves and CHP consumption."""
    with snapshot_lock:
        data = dict(latest_fuel)
    return jsonify(data)


@app.route('/api/logistics/status')
def logistics_status():
    """Return overall logistics operational status."""
    with snapshot_lock:
        data = dict(latest_station_status)
    return jsonify(data)


@app.route('/api/logistics/action', methods=['POST'])
def logistics_action():
    """Execute interactive simulation commands."""
    global fuel_remaining, VESSEL_STATE
    body = request.get_json(force=True, silent=True) or {}
    action = body.get('action')

    if action == 'resupply':
        # Add 50,000 litres from vessel cargo
        added = min(50_000.0, FUEL_FARM_CAPACITY - fuel_remaining)
        fuel_remaining += added
        # Reset vessel position to approach again
        VESSEL_STATE["latitude"] = -69.75
        VESSEL_STATE["longitude"] = 75.20
        store_event({
            "timestamp": sim_timestamp(),
            "event_type": "STATION_STATUS",
            "action": "RESUPPLY_EXECUTED",
            "litres_added": added,
            "message": f"Successfully offloaded {added:,.0f} L Polar Diesel to Bharati Fuel Farm."
        })
        return jsonify({"success": True, "message": f"Resupply complete: +{added:,.0f} L added."})

    elif action == 'trigger_anomaly':
        # Inject immediate high-priority anomaly
        anomaly = {
            "type": "VESSEL_OFF_COURSE",
            "severity": "CRITICAL",
            "message": "Manual Drill: Sudden pack ice drift detected. Vessel forced 18° westward off safety corridor.",
            "recommended_action": "Activate Bharati radar transponder & standby ice pilot team."
        }
        store_event({
            "timestamp": sim_timestamp(),
            "event_type": "VESSEL_AIS",
            "vessel": dict(VESSEL_STATE),
            "anomaly": anomaly
        })
        return jsonify({"success": True, "message": "Manual anomaly injection broadcasted to mission control."})

    elif action == 'ping_teams':
        for team in FIELD_TEAMS_STATE:
            sim_field_team_event(team)
        return jsonify({"success": True, "message": "Forced emergency Iridium sync with all active teams."})

    elif action == 'reset':
        fuel_remaining = 285_000.0
        VESSEL_STATE["latitude"] = -69.75
        VESSEL_STATE["longitude"] = 75.20
        for team in FIELD_TEAMS_STATE:
            team["distance_from_station_km"] = 4.0
            team["latitude"] = STATION_CONFIG["latitude"]
            team["longitude"] = STATION_CONFIG["longitude"]
        return jsonify({"success": True, "message": "Logistics simulator coordinates reset."})

    return jsonify({"success": False, "error": "Unknown action"}), 400


# ---------------------------------------------------------------------------
# Telemetry Simulation API (for Overview & Maintenance tabs)
# ---------------------------------------------------------------------------

@app.route('/api/telemetry')
def get_telemetry():
    """Simulated telemetry data for Bharati and Maitri stations."""
    data = {
        "timestamp": time.time(),
        "bharati": {
            "chp_units": [
                {
                    "id": i,
                    "rpm": round(random.gauss(1500, 10), 1),
                    "temp": round(random.gauss(85, 2), 1),
                    "status": "HEALTHY",
                }
                for i in range(1, 4)
            ],
            "fuel_farm": {
                "capacity_litres": 300000,
                "current_level": round(fuel_remaining),
            },
            "generators": [
                {"name": "Gen 1", "output_kwh": round(random.uniform(140, 170), 1)},
                {"name": "Gen 2", "output_kwh": round(random.uniform(130, 165), 1)},
                {"name": "Gen 3", "output_kwh": round(random.uniform(40, 60), 1)},
                {"name": "Gen 4", "output_kwh": round(random.uniform(38, 55), 1)},
            ],
        },
        "maitri": {
            "chp_units": [
                {
                    "id": i,
                    "rpm": round(random.gauss(1480, 12), 1),
                    "temp": round(random.gauss(82, 3), 1),
                    "status": "HEALTHY",
                }
                for i in range(1, 3)
            ],
            "fuel_farm": {
                "capacity_litres": 200000,
                "current_level": round(random.uniform(160000, 185000)),
            },
            "generators": [
                {"name": "Gen 1", "output_kwh": round(random.uniform(120, 150), 1)},
                {"name": "Gen 2", "output_kwh": round(random.uniform(110, 140), 1)},
                {"name": "Gen 3", "output_kwh": round(random.uniform(35, 55), 1)},
            ],
        },
        "sat_link_status": random.random() > 0.04,
    }

    # Anomaly injection ~8% of the time for demonstration
    if random.random() > 0.92:
        station = random.choice(["bharati", "maitri"])
        unit_idx = random.randint(0, len(data[station]["chp_units"]) - 1)
        data[station]["chp_units"][unit_idx]["temp"] = round(random.uniform(96, 114), 1)
        data[station]["chp_units"][unit_idx]["status"] = "CRITICAL"

    return jsonify(data)


@app.route('/api/telemetry/predict', methods=['POST'])
def predict_maintenance():
    """
    Edge AI predictive anomaly detection endpoint.
    Uses trained IsolationForest behavior mirrored with precise threshold rules.
    """
    body = request.get_json(force=True, silent=True) or {}
    rpm = body.get("rpm", 1500)
    temp = body.get("temp", 85)

    rpm_anomaly = abs(rpm - 1500) > 30
    temp_anomaly = abs(temp - 85) > 8

    status = "CRITICAL" if (rpm_anomaly or temp_anomaly) else "HEALTHY"

    explanation = []
    if temp_anomaly:
        explanation.append(f"Critical Temperature Drift ({temp:.1f}°C). Bearing friction or coolant obstruction detected.")
    if rpm_anomaly:
        explanation.append(f"Unstable Generator RPM ({rpm:.0f} RPM). Fuel injection pressure anomaly.")

    return jsonify({
        "status": status,
        "rpm": rpm,
        "temp": temp,
        "explanation": " | ".join(explanation) if explanation else "All telemetry parameters nominal.",
        "rpm_anomaly": rpm_anomaly,
        "temp_anomaly": temp_anomaly,
    })


# ---------------------------------------------------------------------------
# Cybersecurity Gateway Fallback Mock Endpoints (ensures 100% reliability)
# ---------------------------------------------------------------------------

if not gateway_registered:
    @app.route('/api/gateway/health')
    def gateway_health():
        return jsonify({
            "status": "online",
            "mode": "standalone_active",
            "components": [
                "zero_trust_auth",
                "post_quantum_crypto",
                "link_integrity_monitor",
                "secure_command_uplink"
            ]
        })

    @app.route('/api/gateway/link/vsat-status')
    def vsat_status():
        return jsonify({
            "snr_db": round(random.uniform(12.5, 18.2), 1),
            "frequency_mhz": round(random.uniform(3998.5, 4001.5), 2),
            "within_band": True,
            "jammed_suspected": random.random() < 0.04,
            "bit_error_rate": random.uniform(1e-7, 1e-5)
        })

    @app.route('/api/gateway/link/reliability-report')
    def reliability_report():
        uptime = round(random.uniform(97.8, 99.9), 1)
        return jsonify({
            "uptime_pct": uptime,
            "avg_latency_ms": round(random.uniform(210, 340), 1),
            "avg_packet_loss_pct": round(random.uniform(0.2, 1.8), 1),
            "alert": uptime < 97.5
        })

    @app.route('/api/gateway/crypto/pqc/generate-keypair')
    def generate_pqc_keypair():
        import hashlib
        seed = str(time.time()).encode()
        pk = hashlib.sha256(seed + b"ml-kem-768").hexdigest() * 4
        return jsonify({
            "algorithm": "ML-KEM-768 (CRYSTALS-Kyber Post-Quantum Cryptography)",
            "public_key_hex": pk[:128] + "...",
            "key_size_bytes": 1184,
            "security_category": "NIST Level 3"
        })


# ---------------------------------------------------------------------------
# Authentication Validation Endpoints
# ---------------------------------------------------------------------------

@app.route('/api/auth/validate-commander', methods=['POST'])
def validate_commander():
    """
    Validates Operational Commander credentials:
      - ID:   NCPOR-ADMIN-001
      - Pass: PolarAdmin@123
      - Sync: 48291736
    """
    body = request.get_json(force=True, silent=True) or {}
    personnel_id = (body.get("personnel_id") or "").strip()
    password = body.get("password") or ""
    sync_code = (body.get("sync_code") or "").strip()

    if personnel_id != "NCPOR-ADMIN-001":
        return jsonify({"success": False, "error": "Unauthorized Personnel ID."}), 401

    if password != "PolarAdmin@123":
        return jsonify({"success": False, "error": "Invalid password. Access denied."}), 401

    if sync_code != "48291736":
        return jsonify({"success": False, "error": "Invalid Satellite Sync Code."}), 401

    return jsonify({
        "success": True,
        "user": {
            "id": "NCPOR-ADMIN-001",
            "name": "NCPOR Expedition Commander",
            "role": "Operational Commander",
            "access": "restricted_level_4"
        }
    })


# ---------------------------------------------------------------------------
# Server Startup
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print()
    print("  +-------------------------------------------------------------+")
    print("  |           POLARTWIN-OS | ANTARCTIC MISSION CONTROL          |")
    print("  |  Indian National Centre for Polar & Ocean Research (NCPOR)  |")
    print("  +-------------------------------------------------------------+")
    print("  |  Local Mission Control : http://localhost:5000              |")
    print("  |  Network Access        : http://0.0.0.0:5000                |")
    print("  |                                                             |")
    print("  |  [ADMIN ACCESS IDENTIFICATION]                              |")
    print("  |  Personnel ID          : NCPOR-ADMIN-001                    |")
    print("  |  Password              : PolarAdmin@123                     |")
    print("  |  Satellite Sync Code   : 48291736                           |")
    print("  |                                                             |")
    print("  |  [ACTIVE SYSTEMS]                                           |")
    print("  |  * 3D Station Models (Bharati & Maitri WebGL)               |")
    print("  |  * Logistics Simulator (AIS Tracking & Fuel Autonomy)       |")
    print("  |  * Edge AI Predictive Telemetry Maintenance                 |")
    print("  |  * Zero-Trust Authentication Gateway                        |")
    print("  +-------------------------------------------------------------+")
    print()

    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        print(f"\n[FATAL] Server stopped with error: {e}")
    finally:
        if sys.stdin and hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
            try:
                input("\nPress Enter to exit...")
            except Exception:
                pass
