import requests

try:
    # Test main backend
    print("Testing main backend on port 5000...")
    response = requests.get('http://localhost:5000/api/test', timeout=5)
    print(f"✅ Main backend: {response.json()}")
    
    # Test if we can save data
    print("\nTesting data save...")
    test_data = {
        "patient": {"name": "Test User", "phone": "1234567890"},
        "appointment": {"service": "Test Service", "date": "Today", "time": "Now"}
    }
    
    save_response = requests.post('http://localhost:5000/api/save-appointment', 
                                 json=test_data, 
                                 timeout=5)
    print(f"✅ Save test: {save_response.json()}")
    
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to backend on port 5000")
    print("Make sure 'python dental_backend.py' is running")
except Exception as e:
    print(f"❌ Error: {e}")