"""
Test script for EmailCaptureHandler implementation.
Tests the EMAIL CAPTURE RULES and EMAIL RECONSTRUCTION RULES implementation.
"""

import sys
sys.path.insert(0, '/c:/Users/disha/VoiceAgent/backend')

from email_capture_handler import EmailCaptureHandler

def print_result(name, result):
    """Pretty print email capture result."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print(f"Valid:       {result.is_valid}")
    print(f"Fragment:    {result.is_fragment}")
    if result.is_fragment:
        print(f"Fragment Type: {result.fragment_type}")
    print(f"Email:       {result.email}")
    if result.domain_found:
        print(f"Domain Found: {result.domain_found}")
    if result.username_provided:
        print(f"Username:    {result.username_provided}")
    print(f"Message:     {result.message}")


def test_email_capture():
    """Test various email capture scenarios."""
    
    print("\n" + "="*60)
    print("EMAIL CAPTURE HANDLER - COMPREHENSIVE TESTS")
    print("="*60)
    
    # Test 1: Complete email with voice format
    result = EmailCaptureHandler.process_email_input("disha380 at gmail dot com")
    print_result("Complete email (voice format)", result)
    assert result.is_valid == True
    assert result.email == "disha380@gmail.com"
    
    # Test 2: Complete email with written format
    result = EmailCaptureHandler.process_email_input("disha380@gmail.com")
    print_result("Complete email (written format)", result)
    assert result.is_valid == True
    assert result.email == "disha380@gmail.com"
    
    # Test 3: FRAGMENT - Only domain (gmail)
    result = EmailCaptureHandler.process_email_input("gmail")
    print_result("FRAGMENT: Domain only (gmail)", result)
    assert result.is_valid == False
    assert result.is_fragment == True
    assert result.fragment_type == "domain_only"
    assert result.domain_found == "gmail"
    
    # Test 4: FRAGMENT - Only domain (yahoo)
    result = EmailCaptureHandler.process_email_input("yahoo dot com")
    print_result("FRAGMENT: Domain only (yahoo.com)", result)
    assert result.is_valid == False
    assert result.is_fragment == True
    assert result.domain_found == "yahoo"
    
    # Test 5: FRAGMENT - Domain with @ symbol
    result = EmailCaptureHandler.process_email_input("at gmail dot com")
    print_result("FRAGMENT: @gmail.com only", result)
    assert result.is_valid == False
    assert result.is_fragment == True
    assert result.domain_found == "gmail"
    
    # Test 6: FRAGMENT - Username only, no domain (CRITICAL RULE)
    result = EmailCaptureHandler.process_email_input("disha380")
    print_result("FRAGMENT: Username only (NO DOMAIN - CRITICAL)", result)
    assert result.is_valid == False
    assert result.is_fragment == True
    assert result.fragment_type == "no_domain"
    
    # Test 7: FRAGMENT - Username too short
    result = EmailCaptureHandler.process_email_input("di at gmail dot com")
    print_result("FRAGMENT: Username too short", result)
    assert result.is_valid == False
    assert result.is_fragment == True
    assert result.username_provided == "di"
    
    # Test 8: Different domain (Yahoo)
    result = EmailCaptureHandler.process_email_input("john smith at yahoo dot com")
    print_result("Complete email (Yahoo)", result)
    assert result.is_valid == True
    assert result.email == "johnsmith@yahoo.com"
    
    # Test 9: Different domain (Outlook)
    result = EmailCaptureHandler.process_email_input("alice123 at outlook dot com")
    print_result("Complete email (Outlook)", result)
    assert result.is_valid == True
    assert result.email == "alice123@outlook.com"
    
    # Test 10: Email with dots in username
    result = EmailCaptureHandler.process_email_input("john dot smith at gmail dot com")
    print_result("Complete email (with dots in username)", result)
    assert result.is_valid == True
    assert result.email == "john.smith@gmail.com"
    
    # Test 11: Missing TLD but known domain (auto-completes)
    result = EmailCaptureHandler.process_email_input("test at gmail")
    print_result("Auto-complete: Missing TLD with known domain", result)
    assert result.is_valid == True
    assert result.email == "test@gmail.com"  # Auto-completed to gmail.com
    
    # Test 12: Empty input
    result = EmailCaptureHandler.process_email_input("")
    print_result("Empty input", result)
    assert result.is_valid == False
    
    # Test 13: Hotmail domain
    result = EmailCaptureHandler.process_email_input("bob123 at hotmail dot com")
    print_result("Complete email (Hotmail)", result)
    assert result.is_valid == True
    assert result.email == "bob123@hotmail.com"
    
    # Test 14: Multiple spaces (should be removed)
    result = EmailCaptureHandler.process_email_input("disha   380   at   gmail   dot   com")
    print_result("Complete email (multiple spaces)", result)
    assert result.is_valid == True
    assert result.email == "disha380@gmail.com"
    
    # Test 15: With slash (should handle properly)
    result = EmailCaptureHandler.process_email_input("email at aol dot com")
    print_result("Complete email (AOL)", result)
    assert result.is_valid == True
    assert result.email == "email@aol.com"
    
    print("\n" + "="*60)
    print("✅ ALL CAPTURE TESTS PASSED!")
    print("="*60)


def test_email_reconstruction():
    """Test EMAIL RECONSTRUCTION RULES - stitching fragments together."""
    
    print("\n" + "="*60)
    print("EMAIL RECONSTRUCTION - FRAGMENT STITCHING TESTS")
    print("="*60)
    
    # Test 1: RECONSTRUCTION - Both username and domain provided
    fragments = {
        'username': 'disha380',
        'domain': 'gmail'
    }
    result = EmailCaptureHandler.reconstruct_from_fragments(fragments)
    print_result("RECONSTRUCTION: Both username and domain", result)
    assert result.is_valid == True
    assert result.email == "disha380@gmail.com"
    
    # Test 2: RECONSTRUCTION - Domain only (missing username)
    fragments = {'domain': 'gmail'}
    result = EmailCaptureHandler.reconstruct_from_fragments(fragments)
    print_result("RECONSTRUCTION: Domain only (missing username)", result)
    assert result.is_valid == False
    assert result.is_fragment == True
    assert result.fragment_type == "username_missing"
    
    # Test 3: RECONSTRUCTION - Username only (missing domain)
    fragments = {'username': 'disha380'}
    result = EmailCaptureHandler.reconstruct_from_fragments(fragments)
    print_result("RECONSTRUCTION: Username only (missing domain)", result)
    assert result.is_valid == False
    assert result.is_fragment == True
    assert result.fragment_type == "domain_missing"
    
    # Test 4: RECONSTRUCTION - Username too short
    fragments = {'username': 'di', 'domain': 'gmail'}
    result = EmailCaptureHandler.reconstruct_from_fragments(fragments)
    print_result("RECONSTRUCTION: Username too short", result)
    assert result.is_valid == False
    assert result.is_fragment == True
    assert result.fragment_type == "username_too_short"
    
    # Test 5: RECONSTRUCTION - Invalid domain
    fragments = {'username': 'disha380', 'domain': 'invalid'}
    result = EmailCaptureHandler.reconstruct_from_fragments(fragments)
    print_result("RECONSTRUCTION: Invalid domain", result)
    assert result.is_valid == False
    assert result.is_fragment == True
    assert result.fragment_type == "invalid_domain"
    
    # Test 6: RECONSTRUCTION - Yahoo domain
    fragments = {'username': 'john123', 'domain': 'yahoo'}
    result = EmailCaptureHandler.reconstruct_from_fragments(fragments)
    print_result("RECONSTRUCTION: Yahoo domain", result)
    assert result.is_valid == True
    assert result.email == "john123@yahoo.com"
    
    # Test 7: RECONSTRUCTION - Outlook domain
    fragments = {'username': 'alice.smith', 'domain': 'outlook'}
    result = EmailCaptureHandler.reconstruct_from_fragments(fragments)
    print_result("RECONSTRUCTION: Outlook domain", result)
    assert result.is_valid == True
    assert result.email == "alice.smith@outlook.com"
    
    # Test 8: RECONSTRUCTION - Empty fragments
    fragments = {}
    result = EmailCaptureHandler.reconstruct_from_fragments(fragments)
    print_result("RECONSTRUCTION: Empty fragments", result)
    assert result.is_valid == False
    
    print("\n" + "="*60)
    print("✅ ALL RECONSTRUCTION TESTS PASSED!")
    print("="*60)


def test_extract_domain():
    """Test domain extraction from text."""
    
    print("\n" + "="*60)
    print("DOMAIN EXTRACTION TESTS")
    print("="*60)
    
    # Test 1: Extract domain from "gmail.com"
    domain = EmailCaptureHandler.extract_domain_from_text("gmail.com")
    print(f"\nTEST: Extract domain from 'gmail.com'")
    print(f"Result: {domain}")
    assert domain == "gmail"
    
    # Test 2: Extract domain from spoken format
    domain = EmailCaptureHandler.extract_domain_from_text("at gmail dot com")
    print(f"\nTEST: Extract domain from 'at gmail dot com'")
    print(f"Result: {domain}")
    assert domain == "gmail"
    
    # Test 3: Extract domain from just "yahoo"
    domain = EmailCaptureHandler.extract_domain_from_text("yahoo")
    print(f"\nTEST: Extract domain from 'yahoo'")
    print(f"Result: {domain}")
    assert domain == "yahoo"
    
    # Test 4: Extract domain from "outlook dot com"
    domain = EmailCaptureHandler.extract_domain_from_text("outlook dot com")
    print(f"\nTEST: Extract domain from 'outlook dot com'")
    print(f"Result: {domain}")
    assert domain == "outlook"
    
    print("\n" + "="*60)
    print("✅ ALL DOMAIN EXTRACTION TESTS PASSED!")
    print("="*60)


def test_extract_username():
    """Test username extraction from text."""
    
    print("\n" + "="*60)
    print("USERNAME EXTRACTION TESTS")
    print("="*60)
    
    # Test 1: Extract username with spaces
    username = EmailCaptureHandler.extract_username_from_text("disha 3 8 0")
    print(f"\nTEST: Extract username from 'disha 3 8 0'")
    print(f"Result: {username}")
    assert username == "disha380"
    
    # Test 2: Extract username from "MT Disha 3"
    username = EmailCaptureHandler.extract_username_from_text("MT Disha 3")
    print(f"\nTEST: Extract username from 'MT Disha 3'")
    print(f"Result: {username}")
    assert username == "mtdisha3"
    
    # Test 3: Username with dots/underscores
    username = EmailCaptureHandler.extract_username_from_text("john dot smith")
    print(f"\nTEST: Extract username from 'john dot smith'")
    print(f"Result: {username}")
    # This should handle the dot as a separator
    
    # Test 4: Should NOT extract if domain present
    username = EmailCaptureHandler.extract_username_from_text("disha380 at gmail dot com")
    print(f"\nTEST: Should NOT extract if domain present")
    print(f"Result: {username}")
    assert username is None
    
    # Test 5: Username too short (less than 3 chars)
    username = EmailCaptureHandler.extract_username_from_text("di")
    print(f"\nTEST: Username too short")
    print(f"Result: {username}")
    assert username is None
    
    print("\n" + "="*60)
    print("✅ ALL USERNAME EXTRACTION TESTS PASSED!")
    print("="*60)


if __name__ == "__main__":
    test_email_capture()
    test_email_reconstruction()
    test_extract_domain()
    test_extract_username()
    
    print("\n" + "="*90)
    print("🎉 ALL TESTS PASSED - EMAIL CAPTURE & RECONSTRUCTION FULLY TESTED!")
    print("="*90)
