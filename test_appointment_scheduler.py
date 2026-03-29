# test_appointment_scheduler.py - Test suite for appointment duration handling
"""
Comprehensive test suite for dynamic appointment duration handling,
time calculations, and conflict detection.
"""

import unittest
from datetime import datetime, timedelta
from appointment_scheduler import (
    AppointmentDurationCalculator,
    AppointmentConflictDetector,
    AppointmentScheduler,
    TimeSlot,
    ScheduleConflict
)


class TestAppointmentDurationCalculator(unittest.TestCase):
    """Test duration calculation functionality."""
    
    def test_get_service_duration_by_id(self):
        """Test getting duration by service ID."""
        self.assertEqual(AppointmentDurationCalculator.get_service_duration("cleaning"), 30)
        self.assertEqual(AppointmentDurationCalculator.get_service_duration("root_canal"), 90)
        self.assertEqual(AppointmentDurationCalculator.get_service_duration("consultation"), 15)
    
    def test_get_service_duration_default(self):
        """Test default duration for unknown service."""
        self.assertEqual(AppointmentDurationCalculator.get_service_duration("unknown_service"), 30)
    
    def test_calculate_end_time(self):
        """Test end time calculation."""
        start = datetime(2025, 12, 30, 10, 0)
        end = AppointmentDurationCalculator.calculate_end_time(start, 30)
        expected = datetime(2025, 12, 30, 10, 30)
        self.assertEqual(end, expected)
    
    def test_calculate_end_time_with_hour_rollover(self):
        """Test end time calculation across hour boundary."""
        start = datetime(2025, 12, 30, 10, 45)
        end = AppointmentDurationCalculator.calculate_end_time(start, 30)
        expected = datetime(2025, 12, 30, 11, 15)
        self.assertEqual(end, expected)
    
    def test_calculate_end_time_from_strings(self):
        """Test end time calculation from string inputs."""
        end_time_str = AppointmentDurationCalculator.calculate_end_time_from_strings(
            "2025-12-30", "02:00 PM", 45
        )
        self.assertEqual(end_time_str, "02:45 PM")
    
    def test_get_duration_description_english(self):
        """Test duration description in English."""
        desc = AppointmentDurationCalculator.get_duration_description(30, "en")
        self.assertEqual(desc, "30 minutes")
        
        desc = AppointmentDurationCalculator.get_duration_description(90, "en")
        self.assertEqual(desc, "1.5 hours")
    
    def test_get_duration_description_hindi(self):
        """Test duration description in Hindi."""
        desc = AppointmentDurationCalculator.get_duration_description(30, "hi")
        self.assertEqual(desc, "30 मिनट")
    
    def test_convert_name_to_id(self):
        """Test service name to ID conversion."""
        self.assertEqual(
            AppointmentDurationCalculator._convert_name_to_id("Teeth Cleaning"),
            "cleaning"
        )
        self.assertEqual(
            AppointmentDurationCalculator._convert_name_to_id("Root Canal Treatment"),
            "root_canal"
        )


class TestTimeSlot(unittest.TestCase):
    """Test TimeSlot data structure."""
    
    def test_timeslot_overlap_true(self):
        """Test overlapping time slots."""
        slot1 = TimeSlot(
            datetime(2025, 12, 30, 10, 0),
            datetime(2025, 12, 30, 10, 30),
            30, "Cleaning", "John"
        )
        slot2 = TimeSlot(
            datetime(2025, 12, 30, 10, 15),
            datetime(2025, 12, 30, 10, 45),
            30, "Checkup", "Jane"
        )
        self.assertTrue(slot1.overlaps_with(slot2))
    
    def test_timeslot_overlap_false(self):
        """Test non-overlapping time slots."""
        slot1 = TimeSlot(
            datetime(2025, 12, 30, 10, 0),
            datetime(2025, 12, 30, 10, 30),
            30, "Cleaning", "John"
        )
        slot2 = TimeSlot(
            datetime(2025, 12, 30, 10, 30),
            datetime(2025, 12, 30, 11, 0),
            30, "Checkup", "Jane"
        )
        self.assertFalse(slot1.overlaps_with(slot2))
    
    def test_timeslot_duration_str(self):
        """Test duration string formatting."""
        slot = TimeSlot(
            datetime(2025, 12, 30, 10, 0),
            datetime(2025, 12, 30, 10, 30),
            30, "Cleaning", "John"
        )
        self.assertEqual(slot.get_duration_str(), "30 minutes")
        
        slot = TimeSlot(
            datetime(2025, 12, 30, 10, 0),
            datetime(2025, 12, 30, 11, 0),
            60, "Whitening", "Jane"
        )
        self.assertEqual(slot.get_duration_str(), "1 hour")


class TestAppointmentConflictDetector(unittest.TestCase):
    """Test conflict detection functionality."""
    
    def test_no_conflict_empty_schedule(self):
        """Test no conflict with empty schedule."""
        result = AppointmentConflictDetector.detect_conflicts(
            [], "2025-12-30", "02:00 PM", 30
        )
        self.assertFalse(result.has_conflict)
    
    def test_conflict_detection(self):
        """Test conflict detection with existing appointment."""
        existing_appointments = [
            {
                "appointment_id": "123",
                "appointment": {
                    "date": "2025-12-30",
                    "time": "02:00 PM",
                    "duration_minutes": 30,
                    "service": "Cleaning"
                },
                "patient": {"name": "John"}
            }
        ]
        
        result = AppointmentConflictDetector.detect_conflicts(
            existing_appointments, "2025-12-30", "02:15 PM", 30
        )
        self.assertTrue(result.has_conflict)
        self.assertIn("overlaps", result.conflict_reason.lower())
    
    def test_no_conflict_different_date(self):
        """Test no conflict on different date."""
        existing_appointments = [
            {
                "appointment_id": "123",
                "appointment": {
                    "date": "2025-12-30",
                    "time": "02:00 PM",
                    "duration_minutes": 30,
                    "service": "Cleaning"
                },
                "patient": {"name": "John"}
            }
        ]
        
        result = AppointmentConflictDetector.detect_conflicts(
            existing_appointments, "2025-12-31", "02:00 PM", 30
        )
        self.assertFalse(result.has_conflict)
    
    def test_no_conflict_different_time(self):
        """Test no conflict with different time."""
        existing_appointments = [
            {
                "appointment_id": "123",
                "appointment": {
                    "date": "2025-12-30",
                    "time": "02:00 PM",
                    "duration_minutes": 30,
                    "service": "Cleaning"
                },
                "patient": {"name": "John"}
            }
        ]
        
        result = AppointmentConflictDetector.detect_conflicts(
            existing_appointments, "2025-12-30", "03:00 PM", 30
        )
        self.assertFalse(result.has_conflict)
    
    def test_suggested_slots(self):
        """Test suggested alternative slots generation."""
        existing_appointments = [
            {
                "appointment_id": "123",
                "appointment": {
                    "date": "2025-12-30",
                    "time": "02:00 PM",
                    "duration_minutes": 30,
                    "service": "Cleaning"
                },
                "patient": {"name": "John"}
            }
        ]
        
        result = AppointmentConflictDetector.detect_conflicts(
            existing_appointments, "2025-12-30", "02:00 PM", 30
        )
        
        self.assertTrue(result.has_conflict)
        self.assertIsNotNone(result.suggested_next_slots)
        self.assertGreater(len(result.suggested_next_slots), 0)


class TestAppointmentScheduler(unittest.TestCase):
    """Test main scheduler functionality."""
    
    def test_prepare_appointment_data(self):
        """Test appointment data preparation."""
        appt = {
            "service": "Teeth Cleaning",
            "service_id": "cleaning",
            "date": "2025-12-30",
            "time": "02:00 PM"
        }
        
        result = AppointmentScheduler.prepare_appointment_data(appt)
        
        self.assertEqual(result["duration_minutes"], 30)
        self.assertIsNotNone(result["duration_str"])
        self.assertEqual(result["end_time"], "02:30 PM")
    
    def test_validate_schedule_no_conflict(self):
        """Test schedule validation with no conflicts."""
        result = AppointmentScheduler.validate_schedule(
            [],
            {"date": "2025-12-30", "time": "02:00 PM"},
            "cleaning"
        )
        
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["duration_minutes"], 30)
        self.assertFalse(result["conflict"]["has_conflict"])
    
    def test_get_available_slots(self):
        """Test getting available slots."""
        available_slots = AppointmentScheduler.get_available_slots(
            [],
            "2025-12-30",
            30,
            clinic_hours=(9, 18),
            slot_interval_minutes=30
        )
        
        self.assertGreater(len(available_slots), 0)
        self.assertTrue(all(slot["available"] for slot in available_slots))
        
        # Should have approximately 18 slots (9 AM to 6 PM, 30-min intervals)
        self.assertGreater(len(available_slots), 10)
    
    def test_get_available_slots_with_conflict(self):
        """Test available slots with existing appointment."""
        existing = [
            {
                "appointment_id": "123",
                "appointment": {
                    "date": "2025-12-30",
                    "time": "10:00 AM",
                    "duration_minutes": 30,
                    "service": "Cleaning"
                },
                "patient": {"name": "John"}
            }
        ]
        
        available_slots = AppointmentScheduler.get_available_slots(
            existing,
            "2025-12-30",
            30,
            clinic_hours=(9, 18),
            slot_interval_minutes=60
        )
        
        # 10:00 AM to 10:30 AM should be occupied
        slot_times = [slot["start_time"] for slot in available_slots]
        self.assertNotIn("10:00 AM", slot_times)


class TestScheduleConflict(unittest.TestCase):
    """Test ScheduleConflict data structure."""
    
    def test_schedule_conflict_no_conflict(self):
        """Test ScheduleConflict with no conflict."""
        conflict = ScheduleConflict(has_conflict=False)
        result = conflict.to_dict()
        
        self.assertFalse(result["has_conflict"])
        self.assertEqual(result["suggested_next_slots"], [])
    
    def test_schedule_conflict_with_conflict(self):
        """Test ScheduleConflict with conflict."""
        existing_appt = {
            "start_time": "2025-12-30T14:00:00",
            "end_time": "2025-12-30T14:30:00"
        }
        
        conflict = ScheduleConflict(
            has_conflict=True,
            conflicting_appointment=existing_appt,
            conflict_reason="Time slot overlaps",
            suggested_next_slots=["02:30 PM", "03:00 PM"]
        )
        
        result = conflict.to_dict()
        self.assertTrue(result["has_conflict"])
        self.assertIsNotNone(result["conflicting_appointment"])
        self.assertEqual(len(result["suggested_next_slots"]), 2)


if __name__ == "__main__":
    unittest.main()
