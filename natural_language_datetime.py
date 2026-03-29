# natural_language_datetime.py - Natural Language Date and Time Interpretation
"""
Natural language date and time interpretation for voice input.

Converts conversational phrases into valid appointment date and time values.

Features:
- Handles common phrases: "today", "tomorrow", "now", "after some time"
- Understands relative time expressions: "in X hours/minutes/days"
- Parses time descriptions: "afternoon", "morning", "evening"
- Ensures all results fall within clinic working hours (9 AM - 6:30 PM)
- Ensures all results are in the future (no past bookings)
- Provides deterministic behavior suitable for clinical scheduling
- Integration with ClinicHoursValidator for time constraint enforcement

Voice Input Examples:
- "Today at 2 PM"
- "Tomorrow in the morning"
- "Can you schedule me after some time?"
- "Next Tuesday at 3 PM"
- "In two hours"
- "This afternoon"
"""

import logging
import re
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParsedDateTime:
    """Represents parsed natural language date/time."""
    original_input: str
    resolved_date: str  # YYYY-MM-DD format
    resolved_time: str  # HH:MM format (24-hour)
    confidence: float  # 0.0 to 1.0
    parsing_notes: str
    is_valid: bool
    fallback_used: bool = False


class NaturalLanguageDateTimeParser:
    """
    Parses natural language date and time expressions into structured format.
    
    Handles conversational voice input patterns and converts them to
    precise date/time values suitable for clinic scheduling.
    """
    
    # Time period mappings
    MORNING_HOUR = 10  # Default morning: 10:00 AM
    AFTERNOON_HOUR = 14  # Default afternoon: 2:00 PM
    EVENING_HOUR = 17  # Default evening: 5:00 PM
    DEFAULT_APPOINTMENT_HOUR = 11  # Default time: 11:00 AM
    
    # Clinic hours constraints
    CLINIC_START_HOUR = 9
    CLINIC_END_HOUR = 18
    CLINIC_END_MIN = 30
    
    # Default appointment duration
    DEFAULT_DURATION_MINUTES = 30
    
    # Relative time keywords
    RELATIVE_KEYWORDS = {
        "today": 0,
        "tomorrow": 1,
        "day after tomorrow": 2,
        "day after": 2,
        "next week": 7,
        "next monday": None,  # Calculated
        "next tuesday": None,
        "next wednesday": None,
        "next thursday": None,
        "next friday": None,
        "next saturday": None,
        "next sunday": None,
        "this week": None,  # Not a specific day
        "in a week": 7,
        "in two weeks": 14,
        "after some time": None,  # User undefined duration
        "soon": None,  # Vague, use default
        "asap": None,  # Next available
    }
    
    # Time period keywords
    TIME_PERIOD_KEYWORDS = {
        "morning": MORNING_HOUR,
        "forenoon": MORNING_HOUR,
        "midday": 12,
        "noon": 12,
        "afternoon": AFTERNOON_HOUR,
        "evening": EVENING_HOUR,
        "night": 19,  # After clinic hours, will be adjusted
    }
    
    # Day of week mapping
    DAY_OF_WEEK_NAMES = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    
    @classmethod
    def parse(
        cls,
        input_text: str,
        duration_minutes: int = DEFAULT_DURATION_MINUTES
    ) -> ParsedDateTime:
        """
        Parse natural language date/time input.
        
        Args:
            input_text: Voice input string (e.g., "Tomorrow at 2 PM")
            duration_minutes: Appointment duration for fitting checks
        
        Returns:
            ParsedDateTime object with resolved date/time or defaults
        """
        input_text = input_text.strip().lower()
        logger.info(f"Parsing natural language: {input_text}")
        
        # Handle empty input
        if not input_text:
            return cls._default_appointment()
        
        # Try specific parsers in order of confidence
        result = (
            cls._parse_explicit_datetime(input_text, duration_minutes) or
            cls._parse_relative_date_with_time(input_text, duration_minutes) or
            cls._parse_relative_date_only(input_text, duration_minutes) or
            cls._parse_time_only(input_text, duration_minutes) or
            cls._parse_relative_time_expression(input_text, duration_minutes) or
            cls._default_appointment()
        )
        
        logger.info(f"Parse result: {result}")
        return result
    
    @classmethod
    def _parse_explicit_datetime(
        cls,
        text: str,
        duration_minutes: int
    ) -> Optional[ParsedDateTime]:
        """Parse explicit datetime patterns like 'tomorrow at 2 PM'."""
        # Pattern: [date phrase] at [time]
        pattern = r"(today|tomorrow|day after tomorrow|next\s+\w+)\s+(?:at|@)\s+(\d{1,2})\s*(?::|\.)?(\d{2})?\s*(am|pm)?"
        match = re.search(pattern, text)
        
        if match:
            date_phrase = match.group(1)
            hour = int(match.group(2))
            minute = int(match.group(3) or 0)
            period = match.group(4) or ""
            
            # Convert 12-hour to 24-hour format
            if period.lower() == "pm" and hour != 12:
                hour += 12
            elif period.lower() == "am" and hour == 12:
                hour = 0
            
            # Get date
            resolved_date = cls._resolve_date(date_phrase)
            if not resolved_date:
                return None
            
            # Validate and adjust time to clinic hours
            resolved_time = cls._validate_and_adjust_time(
                resolved_date, f"{hour:02d}:{minute:02d}", duration_minutes
            )
            
            if not resolved_time:
                return None
            
            return ParsedDateTime(
                original_input=text,
                resolved_date=resolved_date,
                resolved_time=resolved_time,
                confidence=0.95,
                parsing_notes="Explicit datetime pattern matched",
                is_valid=True
            )
        
        return None
    
    @classmethod
    def _parse_relative_date_with_time(
        cls,
        text: str,
        duration_minutes: int
    ) -> Optional[ParsedDateTime]:
        """Parse patterns like 'in 2 days at 3 PM'."""
        pattern = r"in\s+(\d+)\s+(hour|minute|day|week)s?\s+(?:at|@)\s+(\d{1,2})\s*(?::|\.)?(\d{2})?\s*(am|pm)?"
        match = re.search(pattern, text)
        
        if match:
            quantity = int(match.group(1))
            unit = match.group(2).lower()
            hour = int(match.group(3))
            minute = int(match.group(4) or 0)
            period = match.group(5) or ""
            
            # Convert 12-hour to 24-hour
            if period.lower() == "pm" and hour != 12:
                hour += 12
            elif period.lower() == "am" and hour == 12:
                hour = 0
            
            # Calculate target datetime
            now = datetime.now()
            if unit == "hour":
                target_dt = now + timedelta(hours=quantity)
            elif unit == "minute":
                target_dt = now + timedelta(minutes=quantity)
            elif unit == "day":
                target_dt = now + timedelta(days=quantity)
            elif unit == "week":
                target_dt = now + timedelta(weeks=quantity)
            else:
                return None
            
            # Override time if specified
            target_dt = target_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            resolved_date = target_dt.strftime("%Y-%m-%d")
            resolved_time = cls._validate_and_adjust_time(
                resolved_date, f"{hour:02d}:{minute:02d}", duration_minutes
            )
            
            if not resolved_time:
                return None
            
            return ParsedDateTime(
                original_input=text,
                resolved_date=resolved_date,
                resolved_time=resolved_time,
                confidence=0.90,
                parsing_notes="Relative date with explicit time matched",
                is_valid=True
            )
        
        return None
    
    @classmethod
    def _parse_relative_date_only(
        cls,
        text: str,
        duration_minutes: int
    ) -> Optional[ParsedDateTime]:
        """Parse date-only patterns like 'tomorrow', 'next tuesday'."""
        # Check for specific day of week
        day_match = re.search(r"next\s+(" + "|".join(cls.DAY_OF_WEEK_NAMES.keys()) + r")", text)
        if day_match:
            target_day = day_match.group(1)
            resolved_date = cls._get_next_weekday(target_day)
            if resolved_date:
                resolved_time = cls._get_default_time_for_date(resolved_date, duration_minutes)
                if resolved_time:
                    return ParsedDateTime(
                        original_input=text,
                        resolved_date=resolved_date,
                        resolved_time=resolved_time,
                        confidence=0.85,
                        parsing_notes=f"Next {target_day} matched",
                        is_valid=True
                    )
        
        # Check for relative keywords
        for keyword, days_offset in cls.RELATIVE_KEYWORDS.items():
            if keyword in text and days_offset is not None:
                target_date = (datetime.now() + timedelta(days=days_offset)).date()
                resolved_date = target_date.strftime("%Y-%m-%d")
                resolved_time = cls._get_default_time_for_date(resolved_date, duration_minutes)
                
                if resolved_time:
                    return ParsedDateTime(
                        original_input=text,
                        resolved_date=resolved_date,
                        resolved_time=resolved_time,
                        confidence=0.80,
                        parsing_notes=f"Keyword '{keyword}' matched",
                        is_valid=True
                    )
        
        return None
    
    @classmethod
    def _parse_time_only(
        cls,
        text: str,
        duration_minutes: int
    ) -> Optional[ParsedDateTime]:
        """Parse time-only patterns like 'at 3 PM' (assume today)."""
        pattern = r"(?:at|@)\s+(\d{1,2})\s*(?::|\.)?(\d{2})?\s*(am|pm)"
        match = re.search(pattern, text)
        
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            period = match.group(3)
            
            # Convert 12-hour to 24-hour
            if period.lower() == "pm" and hour != 12:
                hour += 12
            elif period.lower() == "am" and hour == 12:
                hour = 0
            
            # Use today as date
            today = datetime.now().date().strftime("%Y-%m-%d")
            resolved_time = cls._validate_and_adjust_time(
                today, f"{hour:02d}:{minute:02d}", duration_minutes
            )
            
            if not resolved_time:
                return None
            
            return ParsedDateTime(
                original_input=text,
                resolved_date=today,
                resolved_time=resolved_time,
                confidence=0.75,
                parsing_notes="Time-only pattern matched, using today as date",
                is_valid=True
            )
        
        return None
    
    @classmethod
    def _parse_relative_time_expression(
        cls,
        text: str,
        duration_minutes: int
    ) -> Optional[ParsedDateTime]:
        """Parse relative time patterns like 'in 2 hours', 'after some time'."""
        # "in X hours/minutes" pattern
        pattern = r"in\s+(\d+)\s+(hour|minute)s?"
        match = re.search(pattern, text)
        
        if match:
            quantity = int(match.group(1))
            unit = match.group(2).lower()
            
            now = datetime.now()
            if unit == "hour":
                target_dt = now + timedelta(hours=quantity)
            elif unit == "minute":
                target_dt = now + timedelta(minutes=quantity)
            else:
                return None
            
            # Round to nearest 15-minute slot
            minutes = target_dt.minute
            if minutes % 15 != 0:
                target_dt = target_dt.replace(second=0, microsecond=0)
                target_dt += timedelta(minutes=15 * ((minutes // 15) + 1))
            
            resolved_date = target_dt.strftime("%Y-%m-%d")
            resolved_time = cls._validate_and_adjust_time(
                resolved_date,
                target_dt.strftime("%H:%M"),
                duration_minutes
            )
            
            if not resolved_time:
                return None
            
            return ParsedDateTime(
                original_input=text,
                resolved_date=resolved_date,
                resolved_time=resolved_time,
                confidence=0.70,
                parsing_notes="Relative time expression matched",
                is_valid=True
            )
        
        # Vague patterns like "after some time", "soon", "asap"
        if any(phrase in text for phrase in ["after some time", "soon", "asap", "whenever"]):
            now = datetime.now()
            # Default to next available slot in 1 hour
            target_dt = now + timedelta(hours=1)
            
            # Round to nearest 15-minute slot
            minutes = target_dt.minute
            if minutes % 15 != 0:
                target_dt = target_dt.replace(second=0, microsecond=0)
                target_dt += timedelta(minutes=15 * ((minutes // 15) + 1))
            
            resolved_date = target_dt.strftime("%Y-%m-%d")
            resolved_time = cls._validate_and_adjust_time(
                resolved_date,
                target_dt.strftime("%H:%M"),
                duration_minutes
            )
            
            if not resolved_time:
                return None
            
            return ParsedDateTime(
                original_input=text,
                resolved_date=resolved_date,
                resolved_time=resolved_time,
                confidence=0.50,
                parsing_notes="Vague time expression, defaulting to next available slot",
                is_valid=True,
                fallback_used=True
            )
        
        return None
    
    @classmethod
    def _resolve_date(cls, date_phrase: str) -> Optional[str]:
        """Convert date phrase to YYYY-MM-DD format."""
        date_phrase = date_phrase.lower().strip()
        
        if date_phrase == "today":
            return datetime.now().date().strftime("%Y-%m-%d")
        elif date_phrase == "tomorrow":
            return (datetime.now() + timedelta(days=1)).date().strftime("%Y-%m-%d")
        elif date_phrase in ["day after tomorrow", "day after"]:
            return (datetime.now() + timedelta(days=2)).date().strftime("%Y-%m-%d")
        
        # Check for next weekday
        if date_phrase.startswith("next "):
            day_name = date_phrase.split("next ")[-1]
            return cls._get_next_weekday(day_name)
        
        return None
    
    @classmethod
    def _get_next_weekday(cls, day_name: str) -> Optional[str]:
        """Get next occurrence of specified weekday."""
        day_name = day_name.lower().strip()
        
        if day_name not in cls.DAY_OF_WEEK_NAMES:
            return None
        
        target_day_num = cls.DAY_OF_WEEK_NAMES[day_name]
        today = datetime.now().date()
        current_day = today.weekday()
        
        # Calculate days until target day
        days_ahead = target_day_num - current_day
        if days_ahead <= 0:
            days_ahead += 7
        
        target_date = today + timedelta(days=days_ahead)
        return target_date.strftime("%Y-%m-%d")
    
    @classmethod
    def _get_default_time_for_date(
        cls,
        date_str: str,
        duration_minutes: int
    ) -> Optional[str]:
        """Get default appointment time for a given date."""
        # Check if time period keywords in original text
        default_hour = cls.DEFAULT_APPOINTMENT_HOUR
        
        resolved_time = cls._validate_and_adjust_time(
            date_str,
            f"{default_hour:02d}:00",
            duration_minutes
        )
        
        return resolved_time
    
    @classmethod
    def _validate_and_adjust_time(
        cls,
        date_str: str,
        time_str: str,
        duration_minutes: int
    ) -> Optional[str]:
        """
        Validate time and adjust to fit within clinic hours.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            time_str: Time in HH:MM format (24-hour)
            duration_minutes: Appointment duration
        
        Returns:
            Validated/adjusted time in HH:MM format, or None if invalid
        """
        try:
            # Parse requested time
            hour, minute = map(int, time_str.split(":"))
            
            # Build appointment datetime
            appt_dt = datetime.strptime(f"{date_str} {hour:02d}:{minute:02d}", "%Y-%m-%d %H:%M")
            current_dt = datetime.now()
            
            # Rule 1: Cannot be in the past
            if appt_dt < current_dt:
                # Find next valid slot in clinic hours same day
                search_dt = current_dt.replace(second=0, microsecond=0)
                appt_dt = cls._find_next_valid_slot(
                    search_dt.strftime("%Y-%m-%d"),
                    search_dt.strftime("%H:%M"),
                    duration_minutes
                )
                if not appt_dt:
                    return None
                return appt_dt.strftime("%H:%M")
            
            # Rule 2: Must be within clinic hours
            clinic_start = time(cls.CLINIC_START_HOUR, 0)
            clinic_end = time(cls.CLINIC_END_HOUR, cls.CLINIC_END_MIN)
            appt_time = appt_dt.time()
            
            if appt_time < clinic_start:
                # Before opening, use opening time
                appt_dt = appt_dt.replace(hour=cls.CLINIC_START_HOUR, minute=0)
            elif appt_time > clinic_end:
                # After closing, move to next day opening
                appt_dt = (appt_dt + timedelta(days=1)).replace(
                    hour=cls.CLINIC_START_HOUR,
                    minute=0
                )
            
            # Rule 3: Appointment must fit before clinic closes
            end_dt = appt_dt + timedelta(minutes=duration_minutes)
            clinic_end_dt = appt_dt.replace(
                hour=cls.CLINIC_END_HOUR,
                minute=cls.CLINIC_END_MIN
            )
            
            if end_dt > clinic_end_dt:
                # Won't fit, try to find earlier time or next day
                if appt_dt.hour > cls.CLINIC_START_HOUR:
                    # Try moving earlier in same day
                    appt_dt = appt_dt.replace(hour=cls.CLINIC_START_HOUR, minute=0)
                    end_dt = appt_dt + timedelta(minutes=duration_minutes)
                    if end_dt > clinic_end_dt:
                        # Still won't fit, move to next day
                        appt_dt = (appt_dt + timedelta(days=1)).replace(
                            hour=cls.CLINIC_START_HOUR,
                            minute=0
                        )
                else:
                    # Already at opening time, move to next day
                    appt_dt = (appt_dt + timedelta(days=1)).replace(
                        hour=cls.CLINIC_START_HOUR,
                        minute=0
                    )
            
            return appt_dt.strftime("%H:%M")
            
        except (ValueError, AttributeError):
            return None
    
    @classmethod
    def _find_next_valid_slot(
        cls,
        date_str: str,
        time_str: str,
        duration_minutes: int,
        max_days: int = 14
    ) -> Optional[datetime]:
        """Find next valid slot respecting clinic hours."""
        try:
            search_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            current_dt = datetime.now()
            search_dt = max(search_dt, current_dt)
            
            search_end = current_dt + timedelta(days=max_days)
            
            while search_dt <= search_end:
                # Check if within clinic hours
                clinic_start = time(cls.CLINIC_START_HOUR, 0)
                clinic_end = time(cls.CLINIC_END_HOUR, cls.CLINIC_END_MIN)
                slot_time = search_dt.time()
                
                if clinic_start <= slot_time <= clinic_end:
                    # Check if fits before closing
                    end_dt = search_dt + timedelta(minutes=duration_minutes)
                    clinic_end_dt = search_dt.replace(
                        hour=cls.CLINIC_END_HOUR,
                        minute=cls.CLINIC_END_MIN
                    )
                    
                    if end_dt <= clinic_end_dt:
                        return search_dt
                
                # Move to next 15-minute interval
                search_dt += timedelta(minutes=15)
            
            return None
            
        except ValueError:
            return None
    
    @classmethod
    def _default_appointment(cls) -> ParsedDateTime:
        """Return default appointment time."""
        now = datetime.now()
        
        # Find next available slot after current time
        target_dt = now + timedelta(hours=1)
        target_dt = target_dt.replace(minute=0, second=0, microsecond=0)
        
        # Round to next 15-minute interval
        minutes = target_dt.minute
        if minutes % 15 != 0:
            target_dt += timedelta(minutes=15 * ((minutes // 15) + 1))
        
        # Ensure within clinic hours
        if target_dt.hour >= cls.CLINIC_END_HOUR:
            target_dt = (target_dt + timedelta(days=1)).replace(
                hour=cls.CLINIC_START_HOUR,
                minute=0
            )
        
        resolved_date = target_dt.strftime("%Y-%m-%d")
        resolved_time = target_dt.strftime("%H:%M")
        
        return ParsedDateTime(
            original_input="[no input]",
            resolved_date=resolved_date,
            resolved_time=resolved_time,
            confidence=0.0,
            parsing_notes="Using default appointment time (next available slot)",
            is_valid=True,
            fallback_used=True
        )

