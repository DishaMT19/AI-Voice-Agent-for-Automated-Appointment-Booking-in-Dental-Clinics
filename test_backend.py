import requests
import json

# Test if backend is responding
try:
    response = requests.get('http://localhost:5000/api/test')
    print("✅ Backend is running!")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"❌ Backend connection failed: {e}")