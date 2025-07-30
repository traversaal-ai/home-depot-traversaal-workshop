# AI-Powered Delivery Optimization Enhancement

# -----------------------------
# Task 1: Reschedule Delivery Based on Customer Communication
# -----------------------------
# Objective:
# Use policy rules and customer communication to reschedule a delivery.
# The system should suggest a new delivery date, but only confirm it after receiving a response from the customer.
# (Currently, rescheduling defaults to the next day.)

# -----------------------------
# Task 2: Analyze & Adjust Route Using Google Maps API
# -----------------------------
# Objective:
# Use Google Maps API to retrieve live traffic data, identify delays or restricted roads,
# and suggest more efficient alternative delivery routes.

# Sample Code: Route Risk Analysis Tool
import requests

def get_live_traffic_info(origin, destination, api_key):
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": "driving",
        "departure_time": "now",
        "key": api_key
    }
    response = requests.get(url, params=params)
    return response.json()

def analyze_directions_risk(response):
    try:
        leg = response["routes"][0]["legs"][0]
        duration = leg["duration"]["value"]
        traffic = leg["duration_in_traffic"]["value"]
        traffic_delay_min = (traffic - duration) / 60

        restricted_access = any(
            "Restricted usage" in step["html_instructions"]
            for step in leg["steps"]
        )

        partial_match = any(
            wp.get("partial_match", False)
            for wp in response["geocoded_waypoints"]
        )

        return {
            "duration_min": duration // 60,
            "delay_due_to_traffic_min": traffic_delay_min,
            "restricted_road_found": restricted_access,
            "address_match_risk": partial_match,
        }
    except Exception as e:
        return {"error": str(e)}

# Example usage
source_location = "1600 Amphitheatre Parkway, Mountain View, CA"
destination = "123 Dead End Rd, Los Angeles, CA"
api_key = "<YOUR_GOOGLE_API_KEY>"
response = get_live_traffic_info(source_location, destination, api_key)
print(analyze_directions_risk(response))


# -----------------------------
# Task 3: Evaluate and Recommend Vehicle Type
# -----------------------------
# Objective:
# Based on delivery weight, volume, and pallet count, determine whether the assigned vehicle is appropriate.
# If not, suggest a more suitable vehicle using both business logic and LLM-based reasoning.

# Note:
# We're currently using LLM support for recommendation, but vehicle selection should be grounded
# in validated formulas and known vehicle capacity data.

# Sample Code: Vehicle Suitability Evaluation
def evaluate_vehicle_suitability(total_weight_lbs, total_volume_cuft, pallet_count, current_vehicle):
    vehicle_capacities = {
        "VAN": {"max_weight": 1500, "max_volume": 200, "max_pallets": 2},
        "BOX": {"max_weight": 10000, "max_volume": 1000, "max_pallets": 10},
        "FLATBED": {"max_weight": 40000, "max_volume": 2500, "max_pallets": 20},
        "CRANE": {"max_weight": float("inf"), "max_volume": float("inf"), "max_pallets": float("inf")},
    }

    current = vehicle_capacities.get(current_vehicle.upper())
    if not current:
        return {"error": f"Unknown vehicle type: {current_vehicle}"}

    # Check if current vehicle is sufficient
    if (
        total_weight_lbs <= current["max_weight"]
        and total_volume_cuft <= current["max_volume"]
        and pallet_count <= current["max_pallets"]
    ):
        return {
            "vehicle_ok": True,
            "recommended_vehicle": current_vehicle.upper(),
            "reason": "Current vehicle is suitable based on weight, volume, and pallet capacity."
        }

    # Recommend smallest suitable vehicle
    for vehicle, caps in vehicle_capacities.items():
        if (
            total_weight_lbs <= caps["max_weight"]
            and total_volume_cuft <= caps["max_volume"]
            and pallet_count <= caps["max_pallets"]
        ):
            return {
                "vehicle_ok": False,
                "recommended_vehicle": vehicle,
                "reason": f"Current vehicle '{current_vehicle}' is overloaded or inefficient. Recommended: {vehicle}."
            }

    return {
        "vehicle_ok": False,
        "recommended_vehicle": "CRANE or SPECIALIZED",
        "reason": "Order exceeds standard capacities. Requires crane or specialized transport."
    }

# Example usage
result = evaluate_vehicle_suitability(
    total_weight_lbs=3500,
    total_volume_cuft=900,
    pallet_count=6,
    current_vehicle="VAN"
)
print(result)
