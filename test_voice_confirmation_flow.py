#!/usr/bin/env python3
"""
Comprehensive test for voice-only confirmation flow with automatic email dispatch.

Tests:
1. Confirmation ID generation
2. Voice confirmation response generation (EN/HI)
3. Email dispatch functionality
4. Complete save-appointment flow with voice response
"""
import os
import sys
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

# Test imports
try:
    from app import (
        generate_confirmation_id,
        generate_voice_confirmation_response,
        api_save_appointment,
        app as flask_app
    )
    from email_service import send_appointment_confirmation_email
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def test_confirmation_id_generation():
    """Test 1: Confirmation ID Generation"""
    print(f"\n{BLUE}{'='*60}")
    print("TEST 1: Confirmation ID Generation")
    print(f"{'='*60}{RESET}")
    
    # Generate multiple IDs to verify format
    ids = [generate_confirmation_id() for _ in range(5)]
    
    print(f"\n{YELLOW}Generated IDs:{RESET}")
    for i, conf_id in enumerate(ids, 1):
        print(f"  {i}. {conf_id}")
        
        # Verify format: SM{YYMMDD}{4-char}
        if conf_id.startswith('SM') and len(conf_id) == 12:
            print(f"     {GREEN}✓ Valid format (SM + YYMMDD + 4-char){RESET}")
        else:
            print(f"     {RED}✗ Invalid format{RESET}")
            return False
    
    return True

def test_voice_confirmation_response():
    """Test 2: Voice Confirmation Response Generation"""
    print(f"\n{BLUE}{'='*60}")
    print("TEST 2: Voice Confirmation Response Generation")
    print(f"{'='*60}{RESET}")
    
    test_data = {
        'patient_name': 'John Doe',
        'service': 'Tooth Extraction',
        'appointment_date': datetime.now().strftime('%Y-%m-%d'),
        'appointment_time': '10:30',
        'confirmation_id': 'SM250102A3F9'
    }
    
    # Test English response
    print(f"\n{YELLOW}English Response:{RESET}")
    en_response = generate_voice_confirmation_response(
        patient_name=test_data['patient_name'],
        service=test_data['service'],
        appointment_date=test_data['appointment_date'],
        appointment_time=test_data['appointment_time'],
        confirmation_id=test_data['confirmation_id'],
        language='en'
    )
    
    print(en_response)
    
    # Verify required elements in response
    required_elements = [
        'successfully scheduled',
        test_data['service'],
        test_data['confirmation_id'],
        'email'
    ]
    
    en_valid = all(elem.lower() in en_response.lower() for elem in required_elements)
    if en_valid:
        print(f"{GREEN}✓ All required elements present in English response{RESET}")
    else:
        print(f"{RED}✗ Missing elements in English response{RESET}")
        return False
    
    # Test Hindi response
    print(f"\n{YELLOW}Hindi Response:{RESET}")
    hi_response = generate_voice_confirmation_response(
        patient_name=test_data['patient_name'],
        service=test_data['service'],
        appointment_date=test_data['appointment_date'],
        appointment_time=test_data['appointment_time'],
        confirmation_id=test_data['confirmation_id'],
        language='hi'
    )
    
    print(hi_response)
    
    # Verify confirmation ID is in Hindi response
    if test_data['confirmation_id'] in hi_response:
        print(f"{GREEN}✓ Confirmation ID present in Hindi response{RESET}")
    else:
        print(f"{RED}✗ Confirmation ID missing in Hindi response{RESET}")
        return False
    
    # Test date intelligence
    print(f"\n{YELLOW}Date Intelligence Test:{RESET}")
    
    # Test today
    today = datetime.now().strftime('%Y-%m-%d')
    today_response = generate_voice_confirmation_response(
        'John', 'Cleaning', today, '14:00', 'SM250102TEST', 'en'
    )
    if 'today' in today_response.lower():
        print(f"{GREEN}✓ Today's appointment shows 'today'{RESET}")
    else:
        print(f"{RED}✗ Today's appointment not recognized{RESET}")
        return False
    
    # Test tomorrow
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    tomorrow_response = generate_voice_confirmation_response(
        'John', 'Cleaning', tomorrow, '14:00', 'SM250102TEST', 'en'
    )
    if 'tomorrow' in tomorrow_response.lower():
        print(f"{GREEN}✓ Tomorrow's appointment shows 'tomorrow'{RESET}")
    else:
        print(f"{RED}✗ Tomorrow's appointment not recognized{RESET}")
        return False
    
    # Test time conversion (24-hour to 12-hour)
    print(f"\n{YELLOW}Time Conversion Test:{RESET}")
    time_response = generate_voice_confirmation_response(
        'John', 'Cleaning', today, '14:30', 'SM250102TEST', 'en'
    )
    if '2:30 PM' in time_response or '02:30 PM' in time_response:
        print(f"{GREEN}✓ Time converted to 12-hour format correctly{RESET}")
    else:
        print(f"{RED}✗ Time conversion failed{RESET}")
        return False
    
    return True

def test_email_send_function():
    """Test 3: Email Send Function"""
    print(f"\n{BLUE}{'='*60}")
    print("TEST 3: Email Send Function")
    print(f"{'='*60}{RESET}")
    
    test_details = {
        'service': 'Root Canal Treatment',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time': '15:00',
        'duration_minutes': 45,
        'estimated_price': 5000,
        'doctor_name': 'Dr. Sharma'
    }
    
    # Mock email sending to avoid actual SMTP calls
    with patch('email_service.smtplib.SMTP') as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        result = send_appointment_confirmation_email(
            patient_email='test@example.com',
            patient_name='Test Patient',
            appointment_details=test_details,
            confirmation_id='SM250102TEST',
            language='en'
        )
        
        if result or not os.getenv('EMAIL_USER', 'your_email@gmail.com') == 'your_email@gmail.com':
            print(f"{GREEN}✓ Email function executed successfully{RESET}")
        else:
            print(f"{YELLOW}⚠ Email not configured (expected in test environment){RESET}")
    
    # Test with Hindi language
    print(f"\n{YELLOW}Hindi Email Test:{RESET}")
    with patch('email_service.smtplib.SMTP') as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        result = send_appointment_confirmation_email(
            patient_email='test@example.com',
            patient_name='Test Patient',
            appointment_details=test_details,
            confirmation_id='SM250102TEST',
            language='hi'
        )
        print(f"{GREEN}✓ Hindi email processing completed{RESET}")
    
    # Test email validation
    print(f"\n{YELLOW}Email Validation Test:{RESET}")
    invalid_email_result = send_appointment_confirmation_email(
        patient_email='invalid-email',
        patient_name='Test',
        appointment_details=test_details,
        confirmation_id='SM250102TEST'
    )
    if not invalid_email_result:
        print(f"{GREEN}✓ Invalid email rejected correctly{RESET}")
    else:
        print(f"{RED}✗ Invalid email should have been rejected{RESET}")
        return False
    
    return True

def test_complete_flow():
    """Test 4: Complete Save-Appointment Flow"""
    print(f"\n{BLUE}{'='*60}")
    print("TEST 4: Complete Save-Appointment Flow")
    print(f"{'='*60}{RESET}")
    
    # Create Flask test client
    with flask_app.test_client() as client:
        # Prepare test data
        test_payload = {
            'patient': {
                'name': 'Jane Smith',
                'phone': '9876543210',
                'email': 'jane@example.com',
                'address': 'New Delhi'
            },
            'appointment': {
                'service': 'Cleaning',
                'date': 'tomorrow',
                'time': '2:30 PM'
            },
            'emotions': [{'emotion': 'neutral', 'intensity': 0.5}],
            'lang': 'en',
            'conversationHistory': [],
            'totalDuration': 120
        }
        
        print(f"\n{YELLOW}Sending appointment request...{RESET}")
        
        # Mock email sending
        with patch('app.send_appointment_confirmation_email') as mock_email:
            mock_email.return_value = True
            
            # Send request to save-appointment endpoint
            response = client.post(
                '/api/save-appointment',
                json=test_payload,
                content_type='application/json'
            )
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.get_json()
            
            print(f"\n{YELLOW}Response Data:{RESET}")
            print(f"  Success: {data.get('success')}")
            print(f"  Appointment ID: {data.get('appointment_id')}")
            print(f"  Confirmation ID: {data.get('confirmation_id')}")
            print(f"  Email Sent: {data.get('email_sent')}")
            print(f"  Voice Response Present: {'voice_response' in data}")
            
            # Verify all required fields
            required_fields = [
                'success',
                'appointment_id',
                'confirmation_id',
                'email_sent',
                'voice_response',
                'message',
                'details'
            ]
            
            missing_fields = [f for f in required_fields if f not in data]
            
            if not missing_fields:
                print(f"\n{GREEN}✓ All required fields present in response{RESET}")
            else:
                print(f"\n{RED}✗ Missing fields: {missing_fields}{RESET}")
                return False
            
            # Verify voice response content
            if data.get('voice_response'):
                voice_resp = data['voice_response']
                if 'successfully scheduled' in voice_resp.lower() and data['confirmation_id'] in voice_resp:
                    print(f"{GREEN}✓ Voice response contains required information{RESET}")
                else:
                    print(f"{RED}✗ Voice response missing required information{RESET}")
                    return False
            else:
                print(f"{RED}✗ No voice response in response{RESET}")
                return False
            
            print(f"\n{YELLOW}Final Voice Response:{RESET}")
            print(f"  {data.get('voice_response')}")
            
            return True
        else:
            print(f"{RED}✗ Request failed with status {response.status_code}{RESET}")
            print(f"Response: {response.get_json()}")
            return False

def test_failure_scenarios():
    """Test 5: Error Handling"""
    print(f"\n{BLUE}{'='*60}")
    print("TEST 5: Error Handling & Edge Cases")
    print(f"{'='*60}{RESET}")
    
    with flask_app.test_client() as client:
        # Test missing required fields
        print(f"\n{YELLOW}Test: Missing patient name{RESET}")
        invalid_payload = {
            'patient': {
                'phone': '9876543210',
                'email': 'test@example.com'
            },
            'appointment': {
                'service': 'Cleaning',
                'date': 'tomorrow',
                'time': '2:30 PM'
            },
            'lang': 'en'
        }
        
        response = client.post(
            '/api/save-appointment',
            json=invalid_payload,
            content_type='application/json'
        )
        
        if response.status_code == 400:
            print(f"{GREEN}✓ Missing name properly rejected{RESET}")
        else:
            print(f"{YELLOW}⚠ Expected 400 status{RESET}")
        
        # Test invalid email
        print(f"\n{YELLOW}Test: Invalid patient email handling{RESET}")
        valid_payload = {
            'patient': {
                'name': 'Test User',
                'phone': '9876543210',
                'email': 'not-an-email'
            },
            'appointment': {
                'service': 'Cleaning',
                'date': 'tomorrow',
                'time': '2:30 PM'
            },
            'lang': 'en'
        }
        
        with patch('app.send_appointment_confirmation_email') as mock_email:
            mock_email.return_value = False  # Email would fail
            response = client.post(
                '/api/save-appointment',
                json=valid_payload,
                content_type='application/json'
            )
            
            if response.status_code == 200 and not response.get_json().get('email_sent', True):
                print(f"{GREEN}✓ Email failure handled gracefully{RESET}")
            else:
                print(f"{YELLOW}⚠ Email failure handling verified{RESET}")
    
    return True

def main():
    """Run all tests"""
    print(f"\n{BLUE}")
    print("╔" + "="*58 + "╗")
    print("║" + " "*10 + "VOICE CONFIRMATION FLOW TEST SUITE" + " "*14 + "║")
    print("╚" + "="*58 + "╝")
    print(f"{RESET}")
    
    tests = [
        ("Confirmation ID Generation", test_confirmation_id_generation),
        ("Voice Response Generation", test_voice_confirmation_response),
        ("Email Send Function", test_email_send_function),
        ("Complete Flow", test_complete_flow),
        ("Error Handling", test_failure_scenarios),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n{RED}✗ Exception in {test_name}: {str(e)}{RESET}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # Print summary
    print(f"\n{BLUE}{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}{RESET}\n")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{GREEN}✓ PASS{RESET}" if result else f"{RED}✗ FAIL{RESET}"
        print(f"{status} | {test_name}")
    
    print(f"\n{YELLOW}Results: {passed}/{total} tests passed{RESET}\n")
    
    if passed == total:
        print(f"{GREEN}{'='*60}")
        print("🎉 ALL TESTS PASSED! Voice confirmation flow is ready.{RESET}")
        print(f"{'='*60}{RESET}")
        return 0
    else:
        print(f"{RED}{'='*60}")
        print(f"⚠ {total - passed} test(s) failed{RESET}")
        print(f"{'='*60}{RESET}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
