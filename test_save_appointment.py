#!/usr/bin/env python3
"""
Quick test script for appointment saving functionality
"""
import os
import sys
import json
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

# Test imports
try:
    from app import (
        extract_phone, validate_email, parse_date, parse_time,
        find_service_by_name, load_appointments, save_appointments,
        generate_confirmation_id, analyze_emotion_stats,
        JSON_FILE, DATA_DIR
    )
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Test 1: Data directory
print(f"\n1. Data directory: {DATA_DIR}")
if os.path.exists(DATA_DIR):
    print("   ✓ Directory exists")
else:
    print("   ✗ Directory missing")

# Test 2: JSON file
print(f"\n2. JSON file: {JSON_FILE}")
if os.path.exists(JSON_FILE):
    print("   ✓ File exists")
    try:
        with open(JSON_FILE, 'r') as f:
            data = json.load(f)
        print(f"   ✓ Valid JSON with {len(data)} records")
    except json.JSONDecodeError as e:
        print(f"   ✗ Invalid JSON: {e}")
else:
    print("   ✗ File missing")

# Test 3: Phone validation
print("\n3. Phone validation:")
test_phones = [
    ("9876543210", "9876543210"),
    ("+919876543210", "9876543210"),
    ("98-765-43210", "9876543210"),
]
for phone_in, expected in test_phones:
    result = extract_phone(phone_in)
    status = "✓" if result == expected else "✗"
    print(f"   {status} extract_phone('{phone_in}') = {result}")

# Test 4: Email validation
print("\n4. Email validation:")
test_emails = [
    ("john@gmail.com", "john@gmail.com"),
    ("skip", "Not provided"),
]
for email_in, expected in test_emails:
    result = validate_email(email_in)
    status = "✓" if result == expected else "✗"
    print(f"   {status} validate_email('{email_in}') = {result}")

# Test 5: Date parsing
print("\n5. Date parsing:")
test_dates = [
    ("today",),
    ("tomorrow",),
    ("2025-12-25",),
]
for date_in in test_dates:
    result = parse_date(date_in[0])
    status = "✓" if result else "✗"
    print(f"   {status} parse_date('{date_in[0]}') = {result}")

# Test 6: Service lookup
print("\n6. Service lookup:")
service = find_service_by_name("cleaning")
if service:
    print(f"   ✓ Found service: {service['name']}")
else:
    print(f"   ✗ Service not found")

# Test 7: Confirmation ID generation
print("\n7. Confirmation ID:")
conf_id = generate_confirmation_id()
print(f"   ✓ Generated: {conf_id}")

# Test 8: Load appointments
print("\n8. Load appointments:")
appts = load_appointments()
print(f"   ✓ Loaded {len(appts)} appointments")

# Test 9: Save appointment
print("\n9. Save test appointment:")
test_appointment = {
    "appointment_id": "test-" + datetime.now().strftime("%Y%m%d%H%M%S"),
    "confirmation_id": generate_confirmation_id(),
    "timestamp": datetime.now().isoformat(),
    "patient": {
        "name": "Test Patient",
        "phone": "9876543210",
        "email": "test@gmail.com",
        "address": "Test Address"
    },
    "appointment": {
        "service": "Teeth Cleaning",
        "service_id": "cleaning",
        "date": "2025-12-25",
        "time": "10:00 AM",
        "duration": "30 minutes",
        "duration_minutes": 30,
        "estimated_price": 800
    },
    "backend_saved": True,
    "emotions": [],
    "emotion_stats": {},
    "conversation_history": [],
    "conversation_steps": 0,
    "total_duration_seconds": 120,
    "status": "confirmed"
}

try:
    current = load_appointments()
    current.append(test_appointment)
    if save_appointments(current):
        print(f"   ✓ Appointment saved successfully")
        print(f"   ✓ Total appointments: {len(current)}")
    else:
        print(f"   ✗ Failed to save")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 10: Verify persistence
print("\n10. Verify persistence:")
try:
    reloaded = load_appointments()
    if len(reloaded) > 0:
        last_appt = reloaded[-1]
        print(f"   ✓ Data persisted: {last_appt['confirmation_id']}")
    else:
        print(f"   ✗ No appointments in file")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "="*60)
print("TESTS COMPLETE")
print("="*60)
