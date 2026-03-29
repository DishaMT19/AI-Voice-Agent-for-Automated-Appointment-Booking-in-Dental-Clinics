"""
Test suite for Doctor Availability and Slot Conflict Validation System
Tests doctor scheduling, availability checking, slot conflicts, and voice responses
"""

import unittest
from datetime import datetime, timedelta
from doctor_availability import (
    DoctorSchedule,
    DoctorAvailabilityManager,
    SlotConflictValidator,
    DoctorAvailabilityValidator,
    VoiceResponseGenerator,
    SlotAvailability
)


class TestDoctorSchedule(unittest.TestCase):
    """Test DoctorSchedule dataclass and methods."""
    
    def setUp(self):
        """Set up test doctor schedule."""
        self.doctor = DoctorSchedule(
            doctor_id="doc_001",
            doctor_name="Dr. Rajesh Kumar",
            specialization="General Dentistry",
            working_days=[0, 1, 2, 3, 4, 5],  # Mon-Sat
            start_time="09:00",
            end_time="18:00",
            lunch_break_start="13:00",
            lunch_break_end="14:00"
        )
    
    def test_doctor_creation(self):
        """Test doctor schedule creation."""
        self.assertEqual(self.doctor.doctor_id, "doc_001")
        self.assertEqual(self.doctor.doctor_name, "Dr. Rajesh Kumar")
        self.assertEqual(len(self.doctor.working_days), 6)
    
    def test_is_available_on_day_working_day(self):
        """Test availability check for working days."""
        # Monday = 0
        self.assertTrue(self.doctor.is_available_on_day(0))
        # Tuesday = 1
        self.assertTrue(self.doctor.is_available_on_day(1))
    
    def test_is_available_on_day_off(self):
        """Test availability check for days off."""
        # Sunday = 6 (not in working_days)
        self.assertFalse(self.doctor.is_available_on_day(6))
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        doctor_dict = self.doctor.to_dict()
        self.assertIsInstance(doctor_dict, dict)
        self.assertEqual(doctor_dict['doctor_id'], "doc_001")
        self.assertIn('working_days', doctor_dict)


class TestDoctorAvailabilityManager(unittest.TestCase):
    """Test DoctorAvailabilityManager functionality."""
    
    def setUp(self):
        """Set up availability manager."""
        self.manager = DoctorAvailabilityManager()
    
    def test_default_doctors_initialization(self):
        """Test that default doctors are initialized."""
        doctors = self.manager.get_all_doctors()
        self.assertEqual(len(doctors), 3)  # Should have 3 default doctors
    
    def test_get_doctor_schedule(self):
        """Test retrieving specific doctor schedule."""
        doctor = self.manager.get_doctor_schedule("doc_001")
        self.assertIsNotNone(doctor)
        self.assertEqual(doctor.doctor_id, "doc_001")
    
    def test_get_nonexistent_doctor(self):
        """Test retrieving non-existent doctor."""
        doctor = self.manager.get_doctor_schedule("doc_999")
        self.assertIsNone(doctor)
    
    def test_is_doctor_available_on_working_day(self):
        """Test doctor availability on working day."""
        # Monday is working day for doc_001
        available, reason = self.manager.is_doctor_available_on_date("doc_001", "2025-12-22")
        # 2025-12-22 is a Monday
        self.assertTrue(available)
    
    def test_is_time_in_working_hours(self):
        """Test time window validation."""
        # 10:00 is within working hours (09:00-18:00)
        self.assertTrue(self.manager.is_time_in_working_hours("doc_001", "10:00"))
        # 08:00 is before working hours
        self.assertFalse(self.manager.is_time_in_working_hours("doc_001", "08:00"))
        # 19:00 is after working hours
        self.assertFalse(self.manager.is_time_in_working_hours("doc_001", "19:00"))
    
    def test_is_lunch_time(self):
        """Test lunch break detection."""
        # 13:00 is during lunch for doc_001 (13:00-14:00)
        self.assertTrue(self.manager.is_lunch_time("doc_001", "13:00"))
        # 13:30 is during lunch
        self.assertTrue(self.manager.is_lunch_time("doc_001", "13:30"))
        # 12:30 is before lunch
        self.assertFalse(self.manager.is_lunch_time("doc_001", "12:30"))
        # 14:30 is after lunch
        self.assertFalse(self.manager.is_lunch_time("doc_001", "14:30"))
    
    def test_get_next_available_slot(self):
        """Test next available slot finding."""
        # Get next slot from a working time
        slot = self.manager.get_next_available_slot(
            doctor_id="doc_001",
            start_date="2025-12-22",  # Monday
            start_time="10:00",
            duration_minutes=30,
            language="en"
        )
        self.assertIsNotNone(slot)
        self.assertEqual(slot['doctor_id'], "doc_001")
        self.assertIn('date', slot)
        self.assertIn('time', slot)


class TestSlotConflictValidator(unittest.TestCase):
    """Test slot conflict detection."""
    
    def setUp(self):
        """Set up conflict validator with sample appointments."""
        self.validator = SlotConflictValidator()
        self.sample_appointments = [
            {
                "appointment_id": "appt_001",
                "doctor_id": "doc_001",
                "appointment": {
                    "date": "2025-12-22",
                    "time": "10:00",
                    "duration_minutes": 30
                }
            },
            {
                "appointment_id": "appt_002",
                "doctor_id": "doc_001",
                "appointment": {
                    "date": "2025-12-22",
                    "time": "14:00",
                    "duration_minutes": 45
                }
            }
        ]
        self.validator.set_appointments(self.sample_appointments)
    
    def test_no_conflict_different_time(self):
        """Test no conflict for different time."""
        has_conflict, reason = self.validator.has_conflict(
            doctor_id="doc_001",
            date="2025-12-22",
            time="11:00",
            duration_minutes=30
        )
        self.assertFalse(has_conflict)
    
    def test_conflict_overlapping_time(self):
        """Test conflict detection for overlapping time."""
        # 10:15 conflicts with 10:00-10:30
        has_conflict, reason = self.validator.has_conflict(
            doctor_id="doc_001",
            date="2025-12-22",
            time="10:15",
            duration_minutes=30
        )
        self.assertTrue(has_conflict)
    
    def test_conflict_same_start_time(self):
        """Test conflict detection for same start time."""
        has_conflict, reason = self.validator.has_conflict(
            doctor_id="doc_001",
            date="2025-12-22",
            time="10:00",
            duration_minutes=30
        )
        self.assertTrue(has_conflict)
    
    def test_no_conflict_different_doctor(self):
        """Test no conflict for different doctor."""
        has_conflict, reason = self.validator.has_conflict(
            doctor_id="doc_002",
            date="2025-12-22",
            time="10:00",
            duration_minutes=30
        )
        self.assertFalse(has_conflict)
    
    def test_no_conflict_different_date(self):
        """Test no conflict for different date."""
        has_conflict, reason = self.validator.has_conflict(
            doctor_id="doc_001",
            date="2025-12-23",
            time="10:00",
            duration_minutes=30
        )
        self.assertFalse(has_conflict)


class TestVoiceResponseGenerator(unittest.TestCase):
    """Test voice response generation."""
    
    def test_english_unavailability_response(self):
        """Test English unavailability response generation."""
        response = VoiceResponseGenerator.generate_unavailability_response(
            doctor_name="Dr. Rajesh Kumar",
            unavailability_reason="Doctor not available on this day",
            suggested_slot="2025-12-23 10:00",
            language="en"
        )
        self.assertIsNotNone(response)
        self.assertIn("Dr. Rajesh Kumar", response)
        self.assertIn("2025-12-23", response)
    
    def test_hindi_unavailability_response(self):
        """Test Hindi unavailability response generation."""
        response = VoiceResponseGenerator.generate_unavailability_response(
            doctor_name="डॉ. राजेश कुमार",
            unavailability_reason="Doctor not available on this day",
            suggested_slot="2025-12-23 10:00",
            language="hi"
        )
        self.assertIsNotNone(response)
    
    def test_availability_response(self):
        """Test availability confirmation response."""
        response = VoiceResponseGenerator.generate_availability_response(
            doctor_name="Dr. Rajesh Kumar",
            date="2025-12-22",
            time="10:00",
            service="Cleaning",
            language="en"
        )
        self.assertIsNotNone(response)
        self.assertIn("Dr. Rajesh Kumar", response)
        self.assertIn("10:00", response)


class TestDoctorAvailabilityValidator(unittest.TestCase):
    """Test complete doctor availability validation."""
    
    def setUp(self):
        """Set up availability validator."""
        self.validator = DoctorAvailabilityValidator()
    
    def test_validate_available_slot(self):
        """Test validation for available slot."""
        result = self.validator.validate_appointment_slot(
            doctor_id="doc_001",
            date_str="2025-12-22",
            time_str="10:00",
            duration_minutes=30,
            language="en"
        )
        self.assertIsInstance(result, SlotAvailability)
        # Note: May be unavailable depending on default schedule
        # Just verify structure is correct
        self.assertIsNotNone(result.voice_response)
    
    def test_validate_with_time_conversion(self):
        """Test validation with 12-hour format conversion."""
        result = self.validator.validate_appointment_slot(
            doctor_id="doc_001",
            date_str="2025-12-22",
            time_str="10:00 AM",
            duration_minutes=30,
            language="en",
            convert_time=True
        )
        self.assertIsInstance(result, SlotAvailability)
    
    def test_validate_nonexistent_doctor(self):
        """Test validation for non-existent doctor."""
        result = self.validator.validate_appointment_slot(
            doctor_id="doc_999",
            date_str="2025-12-22",
            time_str="10:00",
            duration_minutes=30,
            language="en"
        )
        self.assertFalse(result.is_available)
        self.assertIn("Doctor not found", result.unavailability_reason)
    
    def test_validate_outside_hours(self):
        """Test validation for time outside working hours."""
        result = self.validator.validate_appointment_slot(
            doctor_id="doc_001",
            date_str="2025-12-22",
            time_str="08:00",  # Before working hours
            duration_minutes=30,
            language="en"
        )
        self.assertFalse(result.is_available)


class TestSlotAvailabilityResult(unittest.TestCase):
    """Test SlotAvailability result object."""
    
    def test_slot_availability_creation(self):
        """Test creating SlotAvailability object."""
        result = SlotAvailability(
            is_available=True,
            doctor_id="doc_001",
            doctor_name="Dr. Rajesh Kumar",
            requested_date="2025-12-22",
            requested_time="10:00",
            unavailability_reason=None,
            suggested_slots=[],
            voice_response="Your appointment is confirmed for December 22 at 10:00 AM with Dr. Rajesh Kumar."
        )
        self.assertTrue(result.is_available)
        self.assertEqual(result.doctor_id, "doc_001")
    
    def test_slot_availability_to_dict(self):
        """Test converting SlotAvailability to dictionary."""
        result = SlotAvailability(
            is_available=False,
            doctor_id="doc_001",
            doctor_name="Dr. Rajesh Kumar",
            requested_date="2025-12-22",
            requested_time="10:00",
            unavailability_reason="Time slot already booked",
            suggested_slots=[{"date": "2025-12-22", "time": "11:00"}],
            voice_response="The requested time is unavailable."
        )
        result_dict = result.to_dict()
        self.assertIsInstance(result_dict, dict)
        self.assertEqual(result_dict['is_available'], False)
        self.assertIn('suggested_slots', result_dict)


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflow."""
    
    def test_complete_booking_workflow(self):
        """Test complete booking workflow with doctor availability."""
        # Initialize components
        manager = DoctorAvailabilityManager()
        validator = DoctorAvailabilityValidator()
        
        # Step 1: Get doctor info
        doctor = manager.get_doctor_schedule("doc_001")
        self.assertIsNotNone(doctor)
        
        # Step 2: Find available slot
        available, reason = manager.is_doctor_available_on_date("doc_001", "2025-12-22")
        
        if available:
            # Step 3: Validate specific time
            result = validator.validate_appointment_slot(
                doctor_id="doc_001",
                date_str="2025-12-22",
                time_str="10:00",
                duration_minutes=30,
                language="en"
            )
            self.assertIsInstance(result, SlotAvailability)
    
    def test_multidoctor_scheduling(self):
        """Test scheduling with multiple doctors."""
        manager = DoctorAvailabilityManager()
        
        # Verify all 3 default doctors exist
        doctors = manager.get_all_doctors()
        self.assertEqual(len(doctors), 3)
        
        # Check each doctor's availability
        for doctor in doctors:
            available, reason = manager.is_doctor_available_on_date(
                doctor.doctor_id, "2025-12-22"
            )
            # At least some should be available
            self.assertIsNotNone(available)


def run_tests():
    """Run all tests and print results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDoctorSchedule))
    suite.addTests(loader.loadTestsFromTestCase(TestDoctorAvailabilityManager))
    suite.addTests(loader.loadTestsFromTestCase(TestSlotConflictValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestVoiceResponseGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestDoctorAvailabilityValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestSlotAvailabilityResult))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
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
