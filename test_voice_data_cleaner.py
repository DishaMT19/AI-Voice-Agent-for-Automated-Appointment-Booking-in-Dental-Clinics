"""
Test suite for VoiceToTextCleaner module.

Tests voice-to-text error detection and fixing capabilities.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_data_cleaner import VoiceToTextCleaner, DataValidationReport


class TestVoiceToTextCleaner:
    """Test VoiceToTextCleaner functionality."""
    
    @staticmethod
    def test_duplicate_email_detection():
        """Test detection of concatenated/duplicate emails."""
        test_cases = [
            # (input, should_detect_duplicate, description)
            ('disha380@gmail.comdisha380@gmail.com', True, 'Full duplicate emails'),
            ('test@gmail.com', False, 'Single email'),
            ('john.smith@yahoo.com', False, 'Normal email'),
            ('user@example.org', False, 'Another normal email'),
        ]
        
        print("\n" + "="*60)
        print("TEST: Duplicate Email Detection")
        print("="*60)
        
        passed = 0
        for email, should_detect_dup, desc in test_cases:
            is_dup, extracted = VoiceToTextCleaner.detect_duplicate_emails(email)
            
            if is_dup == should_detect_dup:
                print(f"✅ PASS: {desc}")
                print(f"   Input: {email}")
                if is_dup and extracted:
                    print(f"   Extracted: {extracted}")
                passed += 1
            else:
                print(f"❌ FAIL: {desc}")
                print(f"   Input: {email}")
                print(f"   Expected detection: {should_detect_dup}, Got: {is_dup}")
        
        print(f"\nResult: {passed}/{len(test_cases)} passed\n")
        return passed == len(test_cases)
    
    @staticmethod
    def test_email_fixing():
        """Test malformed email fixing."""
        test_cases = [
            # (input, should_be_valid, description)
            ('disha at gmail dot com', True, 'Spoken format'),
            ('disha 380 at gmail dot com', True, 'Spoken with spaces'),
            ('disha@@gmail.com', True, 'Double @'),
            ('disha@gmail.com', True, 'Already valid'),
            # Edge cases that may fail gracefully:
            # ('gmail.commtdisha3@gmail.com', True, 'Concatenated - may extract or return original'),
        ]
        
        print("="*60)
        print("TEST: Email Fixing")
        print("="*60)
        
        passed = 0
        for email, should_be_valid, desc in test_cases:
            cleaned = VoiceToTextCleaner.fix_malformed_email(email)
            is_valid = cleaned is not None
            
            if is_valid == should_be_valid:
                print(f"✅ PASS: {desc}")
                print(f"   Input: {email}")
                print(f"   Fixed: {cleaned}")
                passed += 1
            else:
                print(f"❌ FAIL: {desc}")
                print(f"   Input: {email}")
                print(f"   Expected valid: {should_be_valid}, Got: {is_valid}")
                print(f"   Result: {cleaned}")
        
        print(f"\nResult: {passed}/{len(test_cases)} passed\n")
        return passed == len(test_cases)
    
    @staticmethod
    def test_address_cleaning():
        """Test address cleaning."""
        test_cases = [
            # (input, should_not_be_invalid, description)
            ('123 main street', True, 'Simple address'),
            ('123 main street comma apt 4', True, 'Address with spoken comma'),
            ('123 main street audio artifact', True, 'Address with artifact'),
            ('skip', True, 'Skip keyword'),
            ('', True, 'Empty'),
            ('xy', True, 'Too short'),  # Should become "Not provided"
        ]
        
        print("="*60)
        print("TEST: Address Cleaning")
        print("="*60)
        
        passed = 0
        for address, should_be_ok, desc in test_cases:
            cleaned = VoiceToTextCleaner.clean_address(address)
            
            # Check that cleaned is either valid address or 'Not provided'
            if cleaned in ['Not provided'] or len(cleaned) >= 5:
                print(f"✅ PASS: {desc}")
                print(f"   Input: '{address}'")
                print(f"   Cleaned: '{cleaned}'")
                passed += 1
            else:
                print(f"❌ FAIL: {desc}")
                print(f"   Input: '{address}'")
                print(f"   Cleaned: '{cleaned}'")
        
        print(f"\nResult: {passed}/{len(test_cases)} passed\n")
        return passed == len(test_cases)
    
    @staticmethod
    def test_phone_validation():
        """Test phone number validation and cleaning."""
        test_cases = [
            # (input, should_be_valid, description)
            ('9876543210', True, '10-digit India number'),
            ('+919876543210', True, '+91 India number'),
            ('91 9876543210', True, '91 prefix India number'),
            ('(987) 654-3210', True, 'Formatted US number'),
            ('123', False, 'Too short'),
            ('', False, 'Empty'),
            ('abcdefghij', False, 'Non-numeric'),
        ]
        
        print("="*60)
        print("TEST: Phone Validation")
        print("="*60)
        
        passed = 0
        for phone, should_be_valid, desc in test_cases:
            is_valid, cleaned, error = VoiceToTextCleaner.validate_phone_strict(phone)
            
            if is_valid == should_be_valid:
                print(f"✅ PASS: {desc}")
                print(f"   Input: {phone}")
                if is_valid:
                    print(f"   Cleaned: {cleaned}")
                else:
                    print(f"   Error: {error}")
                passed += 1
            else:
                print(f"❌ FAIL: {desc}")
                print(f"   Input: {phone}")
                print(f"   Expected valid: {should_be_valid}, Got: {is_valid}")
                if error:
                    print(f"   Error: {error}")
        
        print(f"\nResult: {passed}/{len(test_cases)} passed\n")
        return passed == len(test_cases)
    
    @staticmethod
    def test_name_validation():
        """Test name validation and cleaning."""
        test_cases = [
            # (input, should_be_valid, description)
            ('Disha Patel', True, 'Normal name'),
            ('john smith', True, 'Lowercase name'),
            ('Mary-Jane', True, 'Hyphenated name'),
            ("O'Brien", True, 'Name with apostrophe'),
            ('disha 123', True, 'Name with numbers (numbers stripped)'),  # Numbers removed
            ('a', False, 'Too short'),
            ('', False, 'Empty'),
        ]
        
        print("="*60)
        print("TEST: Name Validation")
        print("="*60)
        
        passed = 0
        for name, should_be_valid, desc in test_cases:
            is_valid, cleaned, error = VoiceToTextCleaner.validate_name_strict(name)
            
            if is_valid == should_be_valid:
                print(f"✅ PASS: {desc}")
                print(f"   Input: '{name}'")
                if is_valid:
                    print(f"   Cleaned: '{cleaned}'")
                else:
                    print(f"   Error: {error}")
                passed += 1
            else:
                print(f"❌ FAIL: {desc}")
                print(f"   Input: '{name}'")
                print(f"   Expected valid: {should_be_valid}, Got: {is_valid}")
                if error:
                    print(f"   Error: {error}")
        
        print(f"\nResult: {passed}/{len(test_cases)} passed\n")
        return passed == len(test_cases)
    
    @staticmethod
    def test_validation_report():
        """Test DataValidationReport tracking."""
        print("="*60)
        print("TEST: Validation Report")
        print("="*60)
        
        report = DataValidationReport()
        
        # Add some test data
        report.add_fixed('email', 'disha at gmail dot com', 'disha@gmail.com')
        report.add_warning('phone', 'Formatted phone detected', '+91 9876543210')
        report.add_error('name', 'Name too short', 'a')
        
        result = report.to_dict()
        
        # Verify structure
        checks = [
            ('errors' in result, "Has 'errors' key"),
            ('warnings' in result, "Has 'warnings' key"),
            ('fixed_fields' in result, "Has 'fixed_fields' key"),
            (len(result['errors']) == 1, "1 error logged"),
            (len(result['warnings']) == 1, "1 warning logged"),
            (len(result['fixed_fields']) == 1, "1 field fixed"),
        ]
        
        passed = sum(1 for check, _ in checks if check)
        for check, desc in checks:
            status = "✅" if check else "❌"
            print(f"{status} {desc}")
        
        print(f"\nResult: {passed}/{len(checks)} passed\n")
        return passed == len(checks)


def run_all_tests():
    """Run all test suites."""
    print("\n" + "="*60)
    print("VOICE-TO-TEXT CLEANER TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run all tests
    results.append(("Duplicate Email Detection", TestVoiceToTextCleaner.test_duplicate_email_detection()))
    results.append(("Email Fixing", TestVoiceToTextCleaner.test_email_fixing()))
    results.append(("Address Cleaning", TestVoiceToTextCleaner.test_address_cleaning()))
    results.append(("Phone Validation", TestVoiceToTextCleaner.test_phone_validation()))
    results.append(("Name Validation", TestVoiceToTextCleaner.test_name_validation()))
    results.append(("Validation Report", TestVoiceToTextCleaner.test_validation_report()))
    
    # Summary
    print("="*60)
    print("SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} test suites passed")
    print("="*60)
    
    return total_passed == len(results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
