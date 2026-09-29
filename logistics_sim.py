# logistics_sim.py
# Mock Antarctic Logistics Data Stream for PolarTwin-OS
#
# Generates JSON Lines (JSONL) events for:
# 1. Vessel AIS tracking
# 2. Field Team Iridium satellite pings
# 3. CHP fuel consumption
# 4. Emergency anomalies

import json
import random
import time
import math
from datetime import datetime, timezone


# ============================================================
# CONFIGURATION
# ============================================================

STATION = {
    "name": "Bharati Station",
    "latitude": -69.4082,
    "longitude": 76.1873
}

VESSEL = {
    "name": "RRS Sir David Attenborough",
    "mmsi": "740123456",
    "latitude": -69.75,
    "longitude": 75.20,
    "heading": 65.0,
    "speed_knots": 10.5
}

FUEL_FARM_CAPACITY = 300_000  # litres
fuel_remaining = FUEL_FARM_CAPACITY

CHP_UNITS = {
    "CHP-01": 0.0,
    "CHP-02": 0.0,
    "CHP-03": 0.0
}

FIELD_TEAMS = [
    {
        "id": "FIELD-TEAM-01",
        "latitude": STATION["latitude"],
        "longitude": STATION["longitude"],
        "heading": 135.0,
        "distance_from_station_km": 0.0
    },
    {
        "id": "FIELD-TEAM-02",
        "latitude": STATION["latitude"],
        "longitude": STATION["longitude"],
        "heading": 225.0,
        "distance_from_station_km": 0.0
    }
]


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def timestamp():
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def emit_event(event):
    """Print one JSON event to stdout."""
    print(json.dumps(event), flush=True)


def move_coordinate(lat, lon, heading, distance_km):
    """
    Approximate movement from a latitude/longitude coordinate.

    This is a mock simulation, so high-precision geodesic
    calculations are unnecessary.
    """

    earth_radius_km = 6371.0

    heading_rad = math.radians(heading)
    lat_rad = math.radians(lat)

    distance_rad = distance_km / earth_radius_km

    new_lat = math.asin(
        math.sin(lat_rad) * math.cos(distance_rad)
        + math.cos(lat_rad)
        * math.sin(distance_rad)
        * math.cos(heading_rad)
    )

    new_lon = math.radians(lon) + math.atan2(
        math.sin(heading_rad)
        * math.sin(distance_rad)
        * math.cos(lat_rad),
        math.cos(distance_rad)
        - math.sin(lat_rad) * math.sin(new_lat)
    )

    return math.degrees(new_lat), math.degrees(new_lon)


# ============================================================
# 1. VESSEL TRACKING
# ============================================================

def generate_vessel_event():
    """
    Simulate RRS Sir David Attenborough approaching Bharati Station.
    """

    global VESSEL

    # Small heading variation to make AIS data realistic
    VESSEL["heading"] += random.uniform(-3, 3)
    VESSEL["heading"] %= 360

    # Convert knots to km travelled per simulation interval.
    # Assuming one simulated update = 1 minute.
    distance_km = VESSEL["speed_knots"] * 1.852 / 60

    VESSEL["latitude"], VESSEL["longitude"] = move_coordinate(
        VESSEL["latitude"],
        VESSEL["longitude"],
        VESSEL["heading"],
        distance_km
    )

    # Occasionally generate an off-course event
    anomaly = None

    if random.random() < 0.05:
        anomaly = {
            "type": "VESSEL_OFF_COURSE",
            "severity": "HIGH",
            "message": "Vessel has deviated from planned route.",
            "recommended_action": "Verify navigation and contact vessel."
        }

    event = {
        "timestamp": timestamp(),
        "event_type": "VESSEL_AIS",
        "vessel": {
            "name": VESSEL["name"],
            "mmsi": VESSEL["mmsi"],
            "latitude": round(VESSEL["latitude"], 6),
            "longitude": round(VESSEL["longitude"], 6),
            "heading": round(VESSEL["heading"], 2),
            "speed_knots": round(VESSEL["speed_knots"], 2),
            "destination": STATION["name"]
        }
    }

    if anomaly:
        event["anomaly"] = anomaly

    emit_event(event)


# ============================================================
# 2. FIELD TEAM TRACKING
# ============================================================

def generate_field_team_event(team):
    """
    Simulate an Antarctic field team travelling away from
    Bharati Station and sending Iridium satellite pings.
    """

    # Travel approximately 0.2–0.5 km per simulated ping
    distance = random.uniform(0.2, 0.5)

    team["latitude"], team["longitude"] = move_coordinate(
        team["latitude"],
        team["longitude"],
        team["heading"],
        distance
    )

    team["distance_from_station_km"] += distance

    anomaly = None

    # Small probability of SOS
    if random.random() < 0.03:
        anomaly = {
            "type": "FIELD_TEAM_SOS",
            "severity": "CRITICAL",
            "message": "Emergency SOS signal received from field team.",
            "recommended_action": "Initiate emergency response protocol."
        }

    event = {
        "timestamp": timestamp(),
        "event_type": "IRIDIUM_FIELD_PING",
        "field_team": {
            "id": team["id"],
            "latitude": round(team["latitude"], 6),
            "longitude": round(team["longitude"], 6),
            "heading": team["heading"],
            "distance_from_station_km": round(
                team["distance_from_station_km"], 2
            ),
            "communication": "IRIDIUM",
            "signal_status": "CONNECTED"
        }
    }

    if anomaly:
        event["anomaly"] = anomaly

    emit_event(event)


# ============================================================
# 3. INVENTORY / FUEL CONSUMPTION
# ============================================================

def generate_fuel_event():
    """
    Simulate fuel consumption by the three CHP generators.
    """

    global fuel_remaining

    total_consumption = 0

    for chp in CHP_UNITS:

        # Simulated generator load
        load_percentage = random.uniform(45, 95)

        # Approximate fuel consumption:
        # 15–30 litres/hour depending on load
        consumption = random.uniform(15, 30) * (load_percentage / 100)

        CHP_UNITS[chp] += consumption
        total_consumption += consumption

    fuel_remaining -= total_consumption

    # Prevent negative inventory
    fuel_remaining = max(0, fuel_remaining)

    event = {
        "timestamp": timestamp(),
        "event_type": "FUEL_CONSUMPTION",
        "inventory": {
            "fuel_farm_capacity_litres": FUEL_FARM_CAPACITY,
            "fuel_remaining_litres": round(fuel_remaining, 2),
            "fuel_consumed_this_interval_litres": round(
                total_consumption, 2
            ),
            "fuel_remaining_percentage": round(
                (fuel_remaining / FUEL_FARM_CAPACITY) * 100,
                2
            )
        },
        "CHP_generators": {
            chp: {
                "cumulative_consumption_litres": round(
                    consumption,
                    2
                )
            }
            for chp, consumption in CHP_UNITS.items()
        }
    }

    emit_event(event)


# ============================================================
# 4. SYSTEM STATUS
# ============================================================

def generate_system_status():
    """Generate a periodic overall station status event."""

    event = {
        "timestamp": timestamp(),
        "event_type": "STATION_STATUS",
        "station": STATION["name"],
        "operational_status": "ONLINE",
        "fuel_remaining_litres": round(fuel_remaining, 2),
        "fuel_level_percentage": round(
            (fuel_remaining / FUEL_FARM_CAPACITY) * 100,
            2
        ),
        "vessel_tracked": VESSEL["name"],
        "field_teams_tracked": len(FIELD_TEAMS)
    }

    emit_event(event)


# ============================================================
# MAIN SIMULATION LOOP
# ============================================================

def main():

    print("# PolarTwin-OS Antarctic Logistics Mock Stream")

    iteration = 0

    while True:

        iteration += 1

        # Vessel AIS update
        generate_vessel_event()

        # Field team satellite pings
        for team in FIELD_TEAMS:
            generate_field_team_event(team)

        # Fuel inventory update
        generate_fuel_event()

        # Station status every 5 iterations
        if iteration % 5 == 0:
            generate_system_status()

        # Wait before next simulated update
        time.sleep(2)


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print("\n# Simulation stopped.")
