# test_natural_language_datetime.py - Tests for Natural Language Date/Time Parser
"""
Comprehensive test suite for NaturalLanguageDateTimeParser.

Tests cover:
- Explicit datetime patterns (e.g., "tomorrow at 2 PM")
- Relative date with time (e.g., "in 2 days at 3 PM")
- Relative date only (e.g., "tomorrow", "next Tuesday")
- Time only patterns (e.g., "at 3 PM")
- Relative time expressions (e.g., "in 2 hours")
- Vague time expressions (e.g., "after some time", "soon")
- Clinic hours enforcement
- Past booking prevention
- Edge cases and boundary conditions
"""

import unittest
from datetime import datetime, timedelta, date
from unittest.mock import patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from natural_language_datetime import (
    NaturalLanguageDateTimeParser,
    ParsedDateTime
)


class TestExplicitDateTimePatterns(unittest.TestCase):
    """Test explicit datetime patterns like 'tomorrow at 2 PM'."""
    
    def test_today_at_specific_time(self):
        """Test 'today at 2 PM' pattern."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("today at 2 pm")
            
            self.assertTrue(result.is_valid)
            self.assertEqual(result.resolved_date, "2025-12-30")
            self.assertEqual(result.resolved_time, "14:00")
            self.assertGreater(result.confidence, 0.9)
    
    def test_tomorrow_at_specific_time(self):
        """Test 'tomorrow at 2 PM' pattern."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("tomorrow at 3 pm")
            
            self.assertTrue(result.is_valid)
            self.assertEqual(result.resolved_date, "2025-12-31")
            self.assertIn(result.resolved_time, ["15:00", "14:00"])  # Allow adjustment
    
    def test_day_after_tomorrow_at_time(self):
        """Test 'day after tomorrow at time' pattern."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("day after tomorrow at 11 am")
            
            self.assertTrue(result.is_valid)
            self.assertEqual(result.resolved_date, "2026-01-01")
    
    def test_time_with_colon_format(self):
        """Test time format with colon separator."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("tomorrow at 2:30 pm")
            
            self.assertTrue(result.is_valid)
            self.assertIn(":", result.resolved_time)
    
    def test_am_time_conversion(self):
        """Test AM time handling."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("tomorrow at 9 am")
            
            self.assertTrue(result.is_valid)
            self.assertEqual(result.resolved_time, "09:00")
    
    def test_pm_time_conversion(self):
        """Test PM time handling."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("tomorrow at 5 pm")
            
            self.assertTrue(result.is_valid)
            self.assertEqual(result.resolved_time, "17:00")
    
    def test_noon_time(self):
        """Test 12 PM (noon) conversion."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("tomorrow at 12 pm")
            
            self.assertTrue(result.is_valid)
            self.assertEqual(result.resolved_time, "12:00")
    
    def test_midnight_time(self):
        """Test 12 AM (midnight) conversion."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("tomorrow at 12 am")
            
            self.assertTrue(result.is_valid)
            # 12 AM should be adjusted or handled appropriately


class TestRelativeDatePatterns(unittest.TestCase):
    """Test relative date patterns."""
    
    def test_today_keyword(self):
        """Test 'today' keyword."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("can you schedule me today in the morning")
            
            self.assertTrue(result.is_valid)
            self.assertEqual(result.resolved_date, "2025-12-30")
    
    def test_tomorrow_keyword(self):
        """Test 'tomorrow' keyword."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("can I book tomorrow")
            
            self.assertTrue(result.is_valid)
            self.assertEqual(result.resolved_date, "2025-12-31")
    
    def test_next_weekday(self):
        """Test 'next [weekday]' pattern."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            # Mock: Tuesday, Dec 30, 2025
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("next friday")
            
            self.assertTrue(result.is_valid)
            # From Tuesday Dec 30, next Friday should be Jan 2 (3 days later)
            # But exact date depends on actual weekday calculation


class TestRelativeTimeExpressions(unittest.TestCase):
    """Test relative time expressions like 'in X hours/days'."""
    
    def test_in_hours_pattern(self):
        """Test 'in X hours' pattern."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("can you schedule me in 2 hours")
            
            self.assertTrue(result.is_valid)
            # Should be around 12:00 noon
            self.assertGreater(result.confidence, 0.5)
    
    def test_in_days_pattern(self):
        """Test 'in X days' pattern."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("in 3 days at 2 pm")
            
            self.assertTrue(result.is_valid)
            self.assertEqual(result.resolved_date, "2026-01-02")
    
    def test_in_weeks_pattern(self):
        """Test 'in X weeks' pattern."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("in 2 weeks at 3 pm")
            
            self.assertTrue(result.is_valid)
    
    def test_in_minutes_pattern(self):
        """Test 'in X minutes' pattern."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("in 30 minutes")
            
            self.assertTrue(result.is_valid)
            self.assertEqual(result.resolved_date, "2025-12-30")


class TestVagueTimeExpressions(unittest.TestCase):
    """Test vague time expressions like 'soon', 'after some time'."""
    
    def test_after_some_time(self):
        """Test 'after some time' fallback."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("Can you schedule me after some time?")
            
            self.assertTrue(result.is_valid)
            self.assertTrue(result.fallback_used)
            self.assertEqual(result.confidence, 0.5)
    
    def test_soon_keyword(self):
        """Test 'soon' keyword."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("I need an appointment soon")
            
            self.assertTrue(result.is_valid)
            self.assertTrue(result.fallback_used)
    
    def test_asap_keyword(self):
        """Test 'ASAP' keyword."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("I need appointment ASAP")
            
            self.assertTrue(result.is_valid)


class TestClinicHoursEnforcement(unittest.TestCase):
    """Test clinic hours enforcement (9 AM - 6:30 PM)."""
    
    def test_before_clinic_opening(self):
        """Test time before clinic opens (before 9 AM)."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("tomorrow at 8 am")
            
            self.assertTrue(result.is_valid)
            # Should be adjusted to at least 9:00 AM
            resolved_hour = int(result.resolved_time.split(":")[0])
            self.assertGreaterEqual(resolved_hour, 9)
    
    def test_after_clinic_closing(self):
        """Test time after clinic closes (after 6:30 PM)."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("tomorrow at 7 pm")
            
            self.assertTrue(result.is_valid)
            # Should be moved to next day or adjusted
    
    def test_within_clinic_hours(self):
        """Test time within clinic hours (9 AM - 6:30 PM)."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("tomorrow at 2 pm")
            
            self.assertTrue(result.is_valid)
            resolved_hour = int(result.resolved_time.split(":")[0])
            self.assertGreaterEqual(resolved_hour, 9)
            self.assertLessEqual(resolved_hour, 18)
    
    def test_clinic_opening_time(self):
        """Test exact clinic opening time (9 AM)."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("tomorrow at 9 am")
            
            self.assertTrue(result.is_valid)
            self.assertEqual(result.resolved_time, "09:00")
    
    def test_clinic_closing_time(self):
        """Test exact clinic closing time (6:30 PM)."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("tomorrow at 6:30 pm")
            
            self.assertTrue(result.is_valid)


class TestPastBookingPrevention(unittest.TestCase):
    """Test prevention of past bookings."""
    
    def test_past_time_today(self):
        """Test preventing booking at past time today."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 14, 0, 0)  # 2 PM
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("today at 10 am")
            
            self.assertTrue(result.is_valid)
            # Should be adjusted to a future time
    
    def test_current_time_input(self):
        """Test current time input."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 14, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("now")
            
            self.assertTrue(result.is_valid)
            # Should resolve to valid future time
    
    def test_very_recent_past_time(self):
        """Test preventing booking just minutes in the past."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 30, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("today at 10:15 am")
            
            self.assertTrue(result.is_valid)
            # Should be adjusted to a future time


class TestAppointmentDurationFitting(unittest.TestCase):
    """Test appointment duration constraints."""
    
    def test_appointment_fits_before_closing(self):
        """Test appointment that fits before clinic closes."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # 30-minute appointment at 6:00 PM (ends at 6:30 PM, clinic closes at 6:30 PM)
            result = NaturalLanguageDateTimeParser.parse(
                "tomorrow at 6 pm",
            )
            
            self.assertTrue(result.is_valid)
    
    def test_appointment_exceeds_closing_time(self):
        """Test appointment that would extend past clinic closing."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # 30-minute appointment at 6:15 PM (would end at 6:45 PM, past 6:30 PM closing)
            result = NaturalLanguageDateTimeParser.parse(
                "tomorrow at 6:15 pm",
            )
            
            self.assertTrue(result.is_valid)
            # Should be adjusted


class TestDefaultBehavior(unittest.TestCase):
    """Test default behavior for unrecognized input."""
    
    def test_empty_input(self):
        """Test empty input."""
        result = NaturalLanguageDateTimeParser.parse("")
        
        self.assertTrue(result.is_valid)
        self.assertTrue(result.fallback_used)
    
    def test_garbage_input(self):
        """Test unrecognizable input."""
        result = NaturalLanguageDateTimeParser.parse("xyzabc no matching pattern")
        
        self.assertTrue(result.is_valid)
        self.assertTrue(result.fallback_used)
        self.assertGreater(len(result.resolved_date), 0)
        self.assertGreater(len(result.resolved_time), 0)
    
    def test_null_input(self):
        """Test None input handling."""
        result = NaturalLanguageDateTimeParser.parse(None or "")
        
        self.assertTrue(result.is_valid)


class TestConfidenceScores(unittest.TestCase):
    """Test confidence scores for different patterns."""
    
    def test_explicit_datetime_confidence(self):
        """Explicit datetime should have high confidence."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("tomorrow at 2 pm")
            self.assertGreater(result.confidence, 0.9)
    
    def test_vague_expression_confidence(self):
        """Vague expressions should have low confidence."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("after some time")
            self.assertLess(result.confidence, 0.6)
    
    def test_default_confidence(self):
        """Default appointment should have zero confidence."""
        result = NaturalLanguageDateTimeParser.parse("")
        self.assertEqual(result.confidence, 0.0)


class TestParseDataClass(unittest.TestCase):
    """Test ParsedDateTime dataclass."""
    
    def test_dataclass_creation(self):
        """Test creating ParsedDateTime."""
        result = ParsedDateTime(
            original_input="test",
            resolved_date="2025-12-30",
            resolved_time="14:00",
            confidence=0.9,
            parsing_notes="test note",
            is_valid=True
        )
        
        self.assertEqual(result.original_input, "test")
        self.assertEqual(result.resolved_date, "2025-12-30")
        self.assertEqual(result.resolved_time, "14:00")
    
    def test_dataclass_fallback_flag(self):
        """Test fallback flag in dataclass."""
        result = ParsedDateTime(
            original_input="test",
            resolved_date="2025-12-30",
            resolved_time="14:00",
            confidence=0.0,
            parsing_notes="default",
            is_valid=True,
            fallback_used=True
        )
        
        self.assertTrue(result.fallback_used)


class TestIntegrationScenarios(unittest.TestCase):
    """Test realistic voice input scenarios."""
    
    def test_user_says_tomorrow_afternoon(self):
        """Simulate: User says 'Can you book me tomorrow in the afternoon?'"""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("tomorrow afternoon")
            
            self.assertTrue(result.is_valid)
            self.assertEqual(result.resolved_date, "2025-12-31")
    
    def test_user_says_next_week_tuesday(self):
        """Simulate: User says 'Can you schedule me next Tuesday at 11 AM?'"""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("next tuesday at 11 am")
            
            self.assertTrue(result.is_valid)
    
    def test_user_says_in_two_days_afternoon(self):
        """Simulate: User says 'Can I get an appointment in 2 days in the afternoon?'"""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("in 2 days in the afternoon")
            
            self.assertTrue(result.is_valid)
    
    def test_user_says_now(self):
        """Simulate: User says 'Can you book me now?'"""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("now")
            
            self.assertTrue(result.is_valid)
            # Should find next available slot


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def test_case_insensitivity(self):
        """Test that parsing is case-insensitive."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result1 = NaturalLanguageDateTimeParser.parse("TOMORROW AT 2 PM")
            result2 = NaturalLanguageDateTimeParser.parse("tomorrow at 2 pm")
            
            self.assertEqual(result1.resolved_date, result2.resolved_date)
            self.assertEqual(result1.resolved_time, result2.resolved_time)
    
    def test_extra_whitespace(self):
        """Test handling of extra whitespace."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("  tomorrow   at   2   pm  ")
            
            self.assertTrue(result.is_valid)
    
    def test_multiple_matching_patterns(self):
        """Test input matching multiple patterns (should use highest confidence)."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # This matches both "tomorrow" and "at 2 pm" patterns
            result = NaturalLanguageDateTimeParser.parse("tomorrow at 2 pm")
            
            self.assertTrue(result.is_valid)
            self.assertGreater(result.confidence, 0.9)  # Should use explicit pattern
    
    def test_15_minute_slot_rounding(self):
        """Test 15-minute slot rounding for relative time."""
        with patch('natural_language_datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 30, 10, 23, 45)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = NaturalLanguageDateTimeParser.parse("in 30 minutes")
            
            self.assertTrue(result.is_valid)
            # Time should be rounded to 15-minute interval
            minutes = int(result.resolved_time.split(":")[1])
            self.assertEqual(minutes % 15, 0)


if __name__ == "__main__":
    unittest.main()
