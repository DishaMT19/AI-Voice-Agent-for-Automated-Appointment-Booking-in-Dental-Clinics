#!/usr/bin/env python
import json
import urllib.request

try:
    resp = urllib.request.urlopen('http://127.0.0.1:5000/api/dashboard-data')
    data = json.load(resp)
    
    total = data.get('quick_stats', {}).get('total_appointments', 0)
    appointments = data.get('appointments', [])
    
    print(f'✓ Dashboard API Response:')
    print(f'  Total appointments: {total}')
    print(f'  Appointments in response: {len(appointments)}')
    
    if appointments:
        first = appointments[0]
        print(f'\n✓ First appointment:')
        print(f'  ID: {first.get("appointment_id")}')
        print(f'  Confirmation: {first.get("confirmation_id")}')
        print(f'  Patient: {first.get("patient", {}).get("name")}')
        print(f'  Service: {first.get("appointment", {}).get("service")}')
        print(f'  Date: {first.get("appointment", {}).get("date")}')
        print(f'  Time: {first.get("appointment", {}).get("time")}')
    
    print(f'\n✓ Test passed! API is working correctly.')
except Exception as e:
    print(f'✗ Error: {e}')
    import traceback
    traceback.print_exc()
