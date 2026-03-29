"""
Test suite for Strict Clinic Working Hour Enforcement

Tests the centralized ClinicHoursValidator for:
- Clinic operating hours enforcement (9 AM - 6:30 PM)
- Past booking prevention
- Valid slot adjustment
- Voice response generation for clinic hours issues
"""

import unittest
from datetime import datetime, timedelta
from doctor_availability import (
    ClinicHoursValidator,
    DoctorAvailabilityValidator,
    DoctorAvailabilityManager,
    SlotAvailability
)


class TestClinicHoursValidator(unittest.TestCase):
    """Test ClinicHoursValidator functionality."""
    
    def test_clinic_hours_str(self):
        """Test clinic hours string formatting."""
        hours = ClinicHoursValidator.get_clinic_hours_str()
        self.assertIn("9:00", hours)
        self.assertIn("6:30", hours)
        self.assertIn("PM", hours)
    
    def test_is_within_clinic_hours_valid_morning(self):
        """Test valid morning time within clinic hours."""
        # 9:00 AM is valid
        self.assertTrue(ClinicHoursValidator.is_within_clinic_hours("09:00"))
        # 10:00 AM is valid
        self.assertTrue(ClinicHoursValidator.is_within_clinic_hours("10:00"))
        # 12:00 PM is valid
        self.assertTrue(ClinicHoursValidator.is_within_clinic_hours("12:00"))
    
    def test_is_within_clinic_hours_valid_afternoon(self):
        """Test valid afternoon time within clinic hours."""
        # 3:00 PM (15:00) is valid
        self.assertTrue(ClinicHoursValidator.is_within_clinic_hours("15:00"))
        # 5:00 PM (17:00) is valid
        self.assertTrue(ClinicHoursValidator.is_within_clinic_hours("17:00"))
        # 6:30 PM (18:30) is valid (at boundary)
        self.assertTrue(ClinicHoursValidator.is_within_clinic_hours("18:30"))
    
    def test_is_within_clinic_hours_invalid_before_opening(self):
        """Test times before clinic opening."""
        # 8:00 AM is before opening
        self.assertFalse(ClinicHoursValidator.is_within_clinic_hours("08:00"))
        # 8:59 AM is before opening
        self.assertFalse(ClinicHoursValidator.is_within_clinic_hours("08:59"))
    
    def test_is_within_clinic_hours_invalid_after_closing(self):
        """Test times after clinic closing."""
        # 6:31 PM (18:31) is after closing
        self.assertFalse(ClinicHoursValidator.is_within_clinic_hours("18:31"))
        # 7:00 PM (19:00) is after closing
        self.assertFalse(ClinicHoursValidator.is_within_clinic_hours("19:00"))
        # 9:00 PM (21:00) is after closing
        self.assertFalse(ClinicHoursValidator.is_within_clinic_hours("21:00"))
    
    def test_is_within_clinic_hours_invalid_format(self):
        """Test invalid time format."""
        self.assertFalse(ClinicHoursValidator.is_within_clinic_hours("25:00"))
        self.assertFalse(ClinicHoursValidator.is_within_clinic_hours("14:75"))
        self.assertFalse(ClinicHoursValidator.is_within_clinic_hours("invalid"))
    
    def test_is_past_booking_future_time(self):
        """Test future time is not past."""
        # Tomorrow at 2 PM
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        date_str = tomorrow.strftime("%Y-%m-%d")
        self.assertFalse(ClinicHoursValidator.is_past_booking(date_str, "14:00"))
    
    def test_is_past_booking_past_time(self):
        """Test past time is detected."""
        # Yesterday at 2 PM
        yesterday = (datetime.now() - timedelta(days=1)).date()
        date_str = yesterday.strftime("%Y-%m-%d")
        self.assertTrue(ClinicHoursValidator.is_past_booking(date_str, "14:00"))
    
    def test_is_past_booking_invalid_format(self):
        """Test invalid date/time format."""
        # This will raise ValueError which is caught
        result = ClinicHoursValidator.is_past_booking("invalid-date", "14:00")
        self.assertFalse(result)
    
    def test_get_next_valid_slot_from_valid_time(self):
        """Test next valid slot from a time already within clinic hours."""
        # Use tomorrow to avoid past booking issues
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        date_str = tomorrow.strftime("%Y-%m-%d")
        
        slot = ClinicHoursValidator.get_next_valid_slot(
            date_str, "10:00", duration_minutes=30
        )
        
        self.assertIsNotNone(slot)
        self.assertEqual(slot['date'], date_str)
        # Should round to 15-minute interval
        self.assertIn(slot['time'], ["10:00", "10:15"])
    
    def test_get_next_valid_slot_from_before_opening(self):
        """Test next valid slot from before clinic opens."""
        # Use tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        date_str = tomorrow.strftime("%Y-%m-%d")
        
        slot = ClinicHoursValidator.get_next_valid_slot(
            date_str, "08:00", duration_minutes=30
        )
        
        self.assertIsNotNone(slot)
        # Should move to opening time or later
        self.assertGreaterEqual(slot['time'], "09:00")
    
    def test_get_next_valid_slot_from_after_closing(self):
        """Test next valid slot from after clinic closes."""
        # Use tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        date_str = tomorrow.strftime("%Y-%m-%d")
        
        slot = ClinicHoursValidator.get_next_valid_slot(
            date_str, "19:00", duration_minutes=30
        )
        
        self.assertIsNotNone(slot)
        # Should move to next day
        next_day = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)
        self.assertGreaterEqual(slot['date'], next_day.strftime("%Y-%m-%d"))
    
    def test_get_next_valid_slot_respects_duration(self):
        """Test that next valid slot ensures appointment fits before closing."""
        # Use tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        date_str = tomorrow.strftime("%Y-%m-%d")
        
        # Request long appointment near closing time
        slot = ClinicHoursValidator.get_next_valid_slot(
            date_str, "18:00", duration_minutes=90  # Long appointment
        )
        
        self.assertIsNotNone(slot)
        # Should find slot earlier or next day
        start_time = datetime.strptime(slot['time'], "%H:%M").time()
        clinic_end = datetime.strptime("18:30", "%H:%M").time()
        # Start + duration should not exceed clinic end
        from datetime import timedelta
        end_time = datetime.combine(
            datetime.now().date(),
            start_time
        ) + timedelta(minutes=90)
        clinic_end_dt = datetime.combine(
            datetime.now().date(),
            clinic_end
        )
        self.assertLessEqual(end_time.time(), clinic_end_dt.time())
    
    def test_adjust_to_valid_slot_valid_time(self):
        """Test adjustment for valid time."""
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        date_str = tomorrow.strftime("%Y-%m-%d")
        
        is_valid, adjusted, reason = ClinicHoursValidator.adjust_to_valid_slot(
            date_str, "14:00", 30
        )
        
        self.assertTrue(is_valid)
        self.assertIsNone(adjusted)
        self.assertIsNone(reason)
    
    def test_adjust_to_valid_slot_past_booking(self):
        """Test adjustment for past booking."""
        yesterday = (datetime.now() - timedelta(days=1)).date()
        date_str = yesterday.strftime("%Y-%m-%d")
        
        is_valid, adjusted, reason = ClinicHoursValidator.adjust_to_valid_slot(
            date_str, "14:00", 30
        )
        
        self.assertFalse(is_valid)
        self.assertIsNotNone(adjusted)
        self.assertIn("past", reason.lower())
    
    def test_adjust_to_valid_slot_before_opening(self):
        """Test adjustment for time before opening."""
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        date_str = tomorrow.strftime("%Y-%m-%d")
        
        is_valid, adjusted, reason = ClinicHoursValidator.adjust_to_valid_slot(
            date_str, "08:00", 30
        )
        
        self.assertFalse(is_valid)
        self.assertIsNotNone(adjusted)
        self.assertIn("clinic hours", reason.lower())
    
    def test_adjust_to_valid_slot_after_closing(self):
        """Test adjustment for time after closing."""
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        date_str = tomorrow.strftime("%Y-%m-%d")
        
        is_valid, adjusted, reason = ClinicHoursValidator.adjust_to_valid_slot(
            date_str, "19:00", 30
        )
        
        self.assertFalse(is_valid)
        self.assertIsNotNone(adjusted)
        self.assertIn("clinic hours", reason.lower())
    
    def test_adjust_to_valid_slot_insufficient_time(self):
        """Test adjustment when appointment won't fit before closing."""
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        date_str = tomorrow.strftime("%Y-%m-%d")
        
        is_valid, adjusted, reason = ClinicHoursValidator.adjust_to_valid_slot(
            date_str, "18:00", 90  # Won't fit in remaining hour
        )
        
        self.assertFalse(is_valid)
        self.assertIsNotNone(adjusted)


class TestIntegrationWithValidator(unittest.TestCase):
    """Test clinic hours validation integration with DoctorAvailabilityValidator."""
    
    def setUp(self):
        """Set up validator."""
        self.validator = DoctorAvailabilityValidator()
    
    def test_validate_rejects_before_opening(self):
        """Test validation rejects time before clinic opens."""
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        date_str = tomorrow.strftime("%Y-%m-%d")
        
        result = self.validator.validate_appointment_slot(
            doctor_id="doc_001",
            date_str=date_str,
            time_str="08:00",
            duration_minutes=30,
            language="en"
        )
        
        self.assertFalse(result.is_available)
        self.assertIn("clinic", result.unavailability_reason.lower())
    
    def test_validate_rejects_after_closing(self):
        """Test validation rejects time after clinic closes."""
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        date_str = tomorrow.strftime("%Y-%m-%d")
        
        result = self.validator.validate_appointment_slot(
            doctor_id="doc_001",
            date_str=date_str,
            time_str="19:00",
            duration_minutes=30,
            language="en"
        )
        
        self.assertFalse(result.is_available)
        self.assertIn("clinic", result.unavailability_reason.lower())
    
    def test_validate_suggests_adjustment_with_voice_response(self):
        """Test validation suggests adjustment and provides voice response."""
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        date_str = tomorrow.strftime("%Y-%m-%d")
        
        result = self.validator.validate_appointment_slot(
            doctor_id="doc_001",
            date_str=date_str,
            time_str="08:00",
            duration_minutes=30,
            language="en"
        )
        
        self.assertFalse(result.is_available)
        self.assertIsNotNone(result.voice_response)
        self.assertIn("clinic", result.voice_response.lower())
        self.assertIn("9:00", result.voice_response)
        self.assertIn("6:30", result.voice_response)
    
    def test_validate_hindi_voice_response(self):
        """Test validation provides Hindi voice response."""
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        date_str = tomorrow.strftime("%Y-%m-%d")
        
        result = self.validator.validate_appointment_slot(
            doctor_id="doc_001",
            date_str=date_str,
            time_str="08:00",
            duration_minutes=30,
            language="hi"
        )
        
        self.assertFalse(result.is_available)
        self.assertIsNotNone(result.voice_response)
        # Hindi response should be different from English
        self.assertNotEqual(result.voice_response, "")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases for clinic hours enforcement."""
    
    def test_exactly_at_opening_time(self):
        """Test appointment exactly at 9:00 AM."""
        self.assertTrue(ClinicHoursValidator.is_within_clinic_hours("09:00"))
    
    def test_exactly_at_closing_time(self):
        """Test appointment exactly at 6:30 PM."""
        self.assertTrue(ClinicHoursValidator.is_within_clinic_hours("18:30"))
    
    def test_one_minute_before_opening(self):
        """Test appointment 1 minute before opening."""
        self.assertFalse(ClinicHoursValidator.is_within_clinic_hours("08:59"))
    
    def test_one_minute_after_closing(self):
        """Test appointment 1 minute after closing."""
        self.assertFalse(ClinicHoursValidator.is_within_clinic_hours("18:31"))
    
    def test_15_minute_slot_at_closing_boundary(self):
        """Test 15-minute appointment ending at 6:30 PM."""
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        date_str = tomorrow.strftime("%Y-%m-%d")
        
        is_valid, adjusted, reason = ClinicHoursValidator.adjust_to_valid_slot(
            date_str, "18:15", 15  # 18:15 + 15 min = 18:30
        )
        
        # Should be valid - appointment ends exactly at closing
        self.assertTrue(is_valid)
    
    def test_15_minute_slot_beyond_closing_boundary(self):
        """Test 30-minute appointment would exceed closing time."""
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        date_str = tomorrow.strftime("%Y-%m-%d")
        
        is_valid, adjusted, reason = ClinicHoursValidator.adjust_to_valid_slot(
            date_str, "18:15", 30  # 18:15 + 30 min = 18:45 (exceeds 18:30)
        )
        
        # Should be invalid - appointment extends beyond closing
        self.assertFalse(is_valid)


def run_tests():
    """Run all tests and print summary."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestClinicHoursValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationWithValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    print("CLINIC HOURS ENFORCEMENT - TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
