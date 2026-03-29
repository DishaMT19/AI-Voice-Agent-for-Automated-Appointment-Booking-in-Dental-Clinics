#!/usr/bin/env python3
"""Quick test of VoiceAgent system"""

import json
from pathlib import Path

print("\n" + "="*70)
print("VoiceAgent System Quick Test")
print("="*70 + "\n")

# Test JSON storage
print("[1] Testing JSON Storage...")
data_dir = Path('data')
data_dir.mkdir(exist_ok=True)
print(f"  ✓ Data directory: {data_dir.absolute()}")

appt_file = data_dir / 'appointment.json'

# Create test appointment
test_appt = {
    "appointment_id": "test-001",
    "timestamp": "2025-01-15T14:30:00",
    "language": "english",
    "patient_name": "Test Patient",
    "email": "test@example.com",
    "service": "cleaning",
    "date": "2025-01-20",
    "time": "14:30",
    "conversation_log": []
}

# Save
with open(appt_file, 'w', encoding='utf-8') as f:
    json.dump([test_appt], f, ensure_ascii=False, indent=2)
print(f"  ✓ Test appointment saved")

# Load and verify
with open(appt_file, 'r', encoding='utf-8') as f:
    loaded = json.load(f)
print(f"  ✓ Loaded {len(loaded)} appointments")

print("\n[2] Checking Flask Installation...")
try:
    import flask
    print(f"  ✓ Flask {flask.__version__} installed")
except ImportError:
    print(f"  ✗ Flask not installed - run: pip install -r requirements.txt")

try:
    import flask_cors
    print(f"  ✓ Flask-CORS installed")
except ImportError:
    print(f"  ✗ Flask-CORS not installed")

print("\n[3] Checking Frontend Files...")
frontend_dir = Path(__file__).parent.parent / "frontend"
files_to_check = [
    (frontend_dir / "index.html", "Main Voice Interface"),
    (frontend_dir / "Dashboard" / "index1.html", "Dashboard"),
]

for file_path, description in files_to_check:
    if file_path.exists():
        size = file_path.stat().st_size
        print(f"  ✓ {description}: {size} bytes")
    else:
        print(f"  ✗ {description}: NOT FOUND")

print("\n[4] Backend Configuration Check...")
try:
    with open('app.py', 'r', encoding='utf-8') as f:
        code = f.read()
        
    checks = [
        ("LANGUAGES dict", 'LANGUAGES = {'),
        ("Language: English", '"english"'),
        ("Language: Hindi", '"hindi"'),
        ("Language: Kannada", '"kannada"'),
        ("Language: Tamil", '"tamil"'),
        ("API endpoint /api/languages", '"/api/languages"'),
        ("API endpoint /api/start-session", '"/api/start-session"'),
        ("API endpoint /api/save-appointment", '"/api/save-appointment"'),
        ("API endpoint /api/appointments", '"/api/appointments"'),
        ("Email function", 'send_confirmation_email'),
    ]
    
    for check_name, check_string in checks:
        if check_string in code:
            print(f"  ✓ {check_name}")
        else:
            print(f"  ✗ {check_name}")
            
except Exception as e:
    print(f"  ✗ Error reading app.py: {e}")

print("\n" + "="*70)
print("Test Complete!")
print("="*70)
print("\nTo start the server:")
print("  python app.py")
print("\nThen visit:")
print("  http://localhost:5000/ - Voice Interface")
print("  http://localhost:5000/dashboard - Appointments Dashboard")
print("\n" + "="*70 + "\n")
