import json
import os
from datetime import datetime

DATA_FILE = os.path.join("data", "appointments.json")

def load_appointments():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_appointment(data):
    appointments = load_appointments()
    appointments.append(data)

    with open(DATA_FILE, "w") as f:
        json.dump(appointments, f, indent=4)

    return data
