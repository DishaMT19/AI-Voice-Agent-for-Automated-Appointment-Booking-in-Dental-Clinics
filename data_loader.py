import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "appointments.json")

def get_appointment_by_id(appointment_id):
    if not os.path.exists(DATA_FILE):
        return None

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        appointments = json.load(f)

    for appt in appointments:
        # support both keys just in case
        if appt.get("appointment_id") == appointment_id or appt.get("confirmation_id") == appointment_id:
            return {
                "appointment_id": appointment_id,
                "patient_name": appt["patient"]["name"],
                "phone_number": appt["patient"]["phone"],
                "email_address": appt["patient"]["email"],
                "service_name": appt["appointment"]["service"],
                "appointment_date": appt["appointment"]["date"],
                "appointment_time": appt["appointment"]["time"]
            }

    return None
