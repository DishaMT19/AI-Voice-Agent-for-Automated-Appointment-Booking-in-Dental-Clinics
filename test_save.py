import requests
import json

# Test data
test_appointment = {
    "patient": {
        "name": "John Doe",
        "phone": "123-456-7890",
        "email": "john@example.com",
        "address": "123 Main Street"
    },
    "appointment": {
        "service": "Teeth Cleaning",
        "date": "Tomorrow",
        "time": "10:00 AM",
        "duration": "45 min"
    },
    "confirmation_id": "TEST-12345"
}

# Send POST request
try:
    response = requests.post(
        'http://localhost:5000/api/save-appointment',
        json=test_appointment,
        headers={'Content-Type': 'application/json'}
    )
    
    print("Status Code:", response.status_code)
    print("Response:", response.json())
    
except Exception as e:
    print(f"Error: {e}")