# appointment_scheduler.py - Dynamic appointment duration handling
"""
Appointment scheduling module with dynamic duration calculation, time management,
and conflict detection based on selected dental services.

Provides utilities for:
- Calculating appointment end times based on service duration
- Validating time slot availability
- Detecting and reporting scheduling conflicts
- Formatting time information for display
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class TimeSlot:
    """Represents an appointment time slot."""
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    service_name: str
    patient_name: str
    appointment_id: str = None
    
    def overlaps_with(self, other: 'TimeSlot') -> bool:
        """Check if this time slot overlaps with another."""
        return self.start_time < other.end_time and self.end_time > other.start_time
    
    def get_duration_str(self) -> str:
        """Get formatted duration string."""
        if self.duration_minutes < 60:
            return f"{self.duration_minutes} minutes"
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        if minutes == 0:
            return f"{hours} hour" if hours == 1 else f"{hours} hours"
        return f"{hours}h {minutes}m"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_minutes": self.duration_minutes,
            "duration_str": self.get_duration_str(),
            "service_name": self.service_name,
            "patient_name": self.patient_name,
            "appointment_id": self.appointment_id
        }


@dataclass
class ScheduleConflict:
    """Represents a scheduling conflict between appointments."""
    has_conflict: bool
    conflicting_appointment: Optional[Dict] = None
    conflict_reason: str = ""
    suggested_next_slots: List[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "has_conflict": self.has_conflict,
            "conflicting_appointment": self.conflicting_appointment,
            "conflict_reason": self.conflict_reason,
            "suggested_next_slots": self.suggested_next_slots or []
        }


class AppointmentDurationCalculator:
    """Calculates appointment durations and end times based on services."""
    
    # Service duration mapping (in minutes)
    SERVICE_DURATIONS = {
        "cleaning": 30,
        "checkup": 20,
        "filling": 45,
        "root_canal": 90,
        "extraction": 30,
        "braces_consult": 30,
        "whitening": 60,
        "implant_consult": 30,
        "emergency": 30,
        "consultation": 15
    }
    
    @classmethod
    def get_service_duration(cls, service_id: str, service_name: str = None) -> int:
        """
        Get duration for a service by ID or name.
        
        Args:
            service_id: Service ID (e.g., 'cleaning', 'root_canal')
            service_name: Optional service name (e.g., 'Teeth Cleaning')
        
        Returns:
            Duration in minutes, defaults to 30 if not found
        """
        # Try service ID first
        if service_id and service_id in cls.SERVICE_DURATIONS:
            return cls.SERVICE_DURATIONS[service_id]
        
        # Try service name (convert to ID format)
        if service_name:
            service_id_from_name = cls._convert_name_to_id(service_name)
            if service_id_from_name in cls.SERVICE_DURATIONS:
                return cls.SERVICE_DURATIONS[service_id_from_name]
        
        logger.warning(f"Service duration not found for {service_id}, defaulting to 30 minutes")
        return 30
    
    @classmethod
    def _convert_name_to_id(cls, service_name: str) -> str:
        """Convert service name to service ID format."""
        if not service_name:
            return ""
        
        name_to_id = {
            "teeth cleaning": "cleaning",
            "dental checkup": "checkup",
            "tooth filling": "filling",
            "root canal treatment": "root_canal",
            "tooth extraction": "extraction",
            "braces consultation": "braces_consult",
            "teeth whitening": "whitening",
            "implant consultation": "implant_consult",
            "emergency care": "emergency",
            "general consultation": "consultation"
        }
        
        service_lower = service_name.lower().strip()
        return name_to_id.get(service_lower, service_lower.replace(" ", "_"))
    
    @classmethod
    def calculate_end_time(cls, start_time: datetime, 
                          duration_minutes: int) -> datetime:
        """
        Calculate appointment end time.
        
        Args:
            start_time: Appointment start datetime
            duration_minutes: Service duration in minutes
        
        Returns:
            Appointment end datetime
        """
        if not isinstance(start_time, datetime):
            raise ValueError("start_time must be a datetime object")
        
        if duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        
        return start_time + timedelta(minutes=duration_minutes)
    
    @classmethod
    def calculate_end_time_from_strings(cls, date_str: str, time_str: str, 
                                       duration_minutes: int,
                                       date_format: str = "%Y-%m-%d",
                                       time_format: str = "%I:%M %p") -> str:
        """
        Calculate end time from string inputs.
        
        Args:
            date_str: Date string (e.g., "2025-12-30")
            time_str: Time string (e.g., "02:30 PM")
            duration_minutes: Service duration in minutes
            date_format: Date format string
            time_format: Time format string
        
        Returns:
            End time string in same format as input time_str
        """
        try:
            start_datetime = datetime.strptime(
                f"{date_str} {time_str}",
                f"{date_format} {time_format}"
            )
            end_datetime = cls.calculate_end_time(start_datetime, duration_minutes)
            return end_datetime.strftime(time_format)
        except Exception as e:
            logger.error(f"Error calculating end time: {e}")
            raise
    
    @classmethod
    def get_duration_description(cls, duration_minutes: int, language: str = "en") -> str:
        """
        Get human-readable duration description in specified language.
        
        Args:
            duration_minutes: Duration in minutes
            language: Language code (en, hi, kn, te, ta, ml, mr)
        
        Returns:
            Formatted duration string
        """
        descriptions = {
            "en": {15: "15 minutes", 20: "20 minutes", 30: "30 minutes", 
                   45: "45 minutes", 60: "1 hour", 90: "1.5 hours"},
            "hi": {15: "15 मिनट", 20: "20 मिनट", 30: "30 मिनट", 
                   45: "45 मिनट", 60: "1 घंटा", 90: "1.5 घंटे"},
            "kn": {15: "15 ನಿಮಿಷ", 20: "20 ನಿಮಿಷ", 30: "30 ನಿಮಿಷ", 
                   45: "45 ನಿಮಿಷ", 60: "1 ಗಂಟೆ", 90: "1.5 ಗಂಟೆ"},
            "te": {15: "15 నిమిషాలు", 20: "20 నిమిషాలు", 30: "30 నిమిషాలు", 
                   45: "45 నిమిషాలు", 60: "1 గంట", 90: "1.5 గంటలు"},
            "ta": {15: "15 நிமிடங்கள்", 20: "20 நிமிடங்கள்", 30: "30 நிமிடங்கள்", 
                   45: "45 நிமிடங்கள்", 60: "1 மணிநேரம்", 90: "1.5 மணிநேரம்"},
            "ml": {15: "15 മിനിറ്റ്", 20: "20 മിനിറ്റ്", 30: "30 മിനിറ്റ്", 
                   45: "45 മിനിറ്റ്", 60: "1 മണിക്കൂർ", 90: "1.5 മണിക്കൂർ"},
            "mr": {15: "15 मिनिटे", 20: "20 मिनिटे", 30: "30 मिनिटे", 
                   45: "45 मिनिटे", 60: "1 तास", 90: "1.5 तास"}
        }
        
        lang_desc = descriptions.get(language, descriptions["en"])
        
        # Try exact match first
        if duration_minutes in lang_desc:
            return lang_desc[duration_minutes]
        
        # Create custom description
        if duration_minutes < 60:
            if language == "en":
                return f"{duration_minutes} minutes"
            elif language == "hi":
                return f"{duration_minutes} मिनट"
            elif language == "kn":
                return f"{duration_minutes} ನಿಮಿಷ"
            elif language == "te":
                return f"{duration_minutes} నిమిషాలు"
            elif language == "ta":
                return f"{duration_minutes} நிமிடங்கள்"
            elif language == "ml":
                return f"{duration_minutes} മിനിറ്റ്"
            elif language == "mr":
                return f"{duration_minutes} मिनिटे"
        
        hours = duration_minutes // 60
        minutes = duration_minutes % 60
        
        if minutes == 0:
            if language == "en":
                return f"{hours} hour" if hours == 1 else f"{hours} hours"
            elif language == "hi":
                return f"{hours} घंटा" if hours == 1 else f"{hours} घंटे"
        
        if language == "en":
            return f"{hours}h {minutes}m"
        return f"{duration_minutes} minutes"


class AppointmentConflictDetector:
    """Detects and manages scheduling conflicts."""
    
    @classmethod
    def detect_conflicts(cls, appointments: List[Dict], 
                        new_date: str, new_time: str, 
                        duration_minutes: int,
                        date_format: str = "%Y-%m-%d",
                        time_format: str = "%I:%M %p") -> ScheduleConflict:
        """
        Detect conflicts for a new appointment.
        
        Args:
            appointments: List of existing appointments
            new_date: New appointment date string
            new_time: New appointment time string
            duration_minutes: New appointment duration in minutes
            date_format: Date format string
            time_format: Time format string
        
        Returns:
            ScheduleConflict object with conflict details
        """
        try:
            new_start = datetime.strptime(
                f"{new_date} {new_time}",
                f"{date_format} {time_format}"
            )
            new_end = new_start + timedelta(minutes=duration_minutes)
            new_slot = TimeSlot(
                start_time=new_start,
                end_time=new_end,
                duration_minutes=duration_minutes,
                service_name="New Appointment",
                patient_name="New Patient"
            )
            
            for appt in appointments:
                if not cls._is_valid_appointment(appt):
                    continue
                
                try:
                    appt_date = appt.get('appointment', {}).get('date')
                    appt_time = appt.get('appointment', {}).get('time')
                    appt_duration = appt.get('appointment', {}).get('duration_minutes', 30)
                    
                    existing_start = datetime.strptime(
                        f"{appt_date} {appt_time}",
                        f"{date_format} {time_format}"
                    )
                    existing_end = existing_start + timedelta(minutes=appt_duration)
                    existing_slot = TimeSlot(
                        start_time=existing_start,
                        end_time=existing_end,
                        duration_minutes=appt_duration,
                        service_name=appt.get('appointment', {}).get('service', 'Unknown'),
                        patient_name=appt.get('patient', {}).get('name', 'Unknown'),
                        appointment_id=appt.get('appointment_id')
                    )
                    
                    if new_slot.overlaps_with(existing_slot):
                        return ScheduleConflict(
                            has_conflict=True,
                            conflicting_appointment=existing_slot.to_dict(),
                            conflict_reason=f"Time slot overlaps with existing appointment for {existing_slot.patient_name}",
                            suggested_next_slots=cls._get_suggested_slots(
                                appointments, new_date, existing_slot.end_time, 
                                duration_minutes, date_format, time_format
                            )
                        )
                except ValueError:
                    # Invalid date/time format, skip this appointment
                    continue
        except ValueError as e:
            logger.error(f"Invalid date/time format for conflict detection: {e}")
            return ScheduleConflict(
                has_conflict=False,
                conflict_reason="Invalid date/time format"
            )
        
        return ScheduleConflict(has_conflict=False)
    
    @classmethod
    def _is_valid_appointment(cls, appt: Dict) -> bool:
        """Check if appointment has required fields."""
        return (appt.get('appointment', {}).get('date') and 
                appt.get('appointment', {}).get('time'))
    
    @classmethod
    def _get_suggested_slots(cls, appointments: List[Dict], date_str: str,
                            start_after: datetime, duration_minutes: int,
                            date_format: str, time_format: str,
                            num_suggestions: int = 3) -> List[str]:
        """
        Get suggested alternative time slots after a conflict.
        
        Args:
            appointments: List of existing appointments
            date_str: Date string
            start_after: Find slots after this datetime
            duration_minutes: Required duration
            date_format: Date format string
            time_format: Time format string
            num_suggestions: Number of suggestions to return
        
        Returns:
            List of suggested time slot strings
        """
        suggestions = []
        current_time = start_after
        max_time = current_time.replace(hour=18, minute=0)  # End of clinic day at 6 PM
        
        while current_time < max_time and len(suggestions) < num_suggestions:
            end_time = current_time + timedelta(minutes=duration_minutes)
            
            # Check if this slot is available
            is_available = True
            for appt in appointments:
                if not cls._is_valid_appointment(appt):
                    continue
                
                try:
                    appt_date = appt.get('appointment', {}).get('date')
                    appt_time = appt.get('appointment', {}).get('time')
                    appt_duration = appt.get('appointment', {}).get('duration_minutes', 30)
                    
                    existing_start = datetime.strptime(
                        f"{appt_date} {appt_time}",
                        f"{date_format} {time_format}"
                    )
                    existing_end = existing_start + timedelta(minutes=appt_duration)
                    
                    if current_time < existing_end and end_time > existing_start:
                        is_available = False
                        break
                except ValueError:
                    continue
            
            if is_available:
                suggestions.append(current_time.strftime(time_format))
            
            # Move to next 15-minute slot
            current_time += timedelta(minutes=15)
        
        return suggestions


class AppointmentScheduler:
    """Main scheduler class that coordinates duration and conflict management."""
    
    @staticmethod
    def prepare_appointment_data(appointment_dict: Dict, service_id: str = None) -> Dict:
        """
        Prepare appointment data with calculated duration and end time.
        
        Args:
            appointment_dict: Appointment data dictionary
            service_id: Service ID (optional, tries to extract from dict)
        
        Returns:
            Updated appointment dictionary with duration calculations
        """
        if service_id is None:
            service_id = appointment_dict.get('service_id') or \
                        appointment_dict.get('service', '').lower().replace(" ", "_")
        
        duration_minutes = AppointmentDurationCalculator.get_service_duration(service_id)
        appointment_dict['duration_minutes'] = duration_minutes
        appointment_dict['duration_str'] = \
            AppointmentDurationCalculator.get_duration_description(duration_minutes)
        
        # Calculate end time if date and time are available
        date_str = appointment_dict.get('date')
        time_str = appointment_dict.get('time')
        
        if date_str and time_str:
            try:
                end_time_str = AppointmentDurationCalculator.calculate_end_time_from_strings(
                    date_str, time_str, duration_minutes
                )
                appointment_dict['end_time'] = end_time_str
            except Exception as e:
                logger.warning(f"Could not calculate end time: {e}")
        
        return appointment_dict
    
    @staticmethod
    def validate_schedule(appointments: List[Dict], new_appointment: Dict,
                         service_id: str = None) -> Dict:
        """
        Validate a new appointment against existing schedule.
        
        Args:
            appointments: List of existing appointments
            new_appointment: New appointment to validate
            service_id: Service ID for duration calculation
        
        Returns:
            Dictionary with validation results
        """
        # Get duration
        if service_id is None:
            service_id = new_appointment.get('service_id')
        
        duration_minutes = AppointmentDurationCalculator.get_service_duration(service_id)
        
        # Check for conflicts
        conflict = AppointmentConflictDetector.detect_conflicts(
            appointments,
            new_appointment.get('date'),
            new_appointment.get('time'),
            duration_minutes
        )
        
        return {
            "duration_minutes": duration_minutes,
            "conflict": conflict.to_dict(),
            "is_valid": not conflict.has_conflict,
            "message": conflict.conflict_reason if conflict.has_conflict else "Time slot is available"
        }
    
    @staticmethod
    def get_available_slots(appointments: List[Dict], date_str: str,
                           duration_minutes: int,
                           clinic_hours: Tuple[int, int] = (9, 18),
                           slot_interval_minutes: int = 15) -> List[Dict]:
        """
        Get available appointment slots for a given date and duration.
        
        Args:
            appointments: List of existing appointments
            date_str: Date string (e.g., "2025-12-30")
            duration_minutes: Required appointment duration
            clinic_hours: Tuple of (start_hour, end_hour) in 24-hour format
            slot_interval_minutes: Interval between slots (default 15 minutes)
        
        Returns:
            List of available time slots with start and end times
        """
        available_slots = []
        clinic_start = clinic_hours[0]
        clinic_end = clinic_hours[1]
        
        current_hour = clinic_start
        current_minute = 0
        
        while current_hour < clinic_end:
            time_str = datetime(2025, 1, 1, current_hour, current_minute).strftime("%I:%M %p")
            
            # Check if this slot is available
            conflict = AppointmentConflictDetector.detect_conflicts(
                appointments, date_str, time_str, duration_minutes
            )
            
            if not conflict.has_conflict:
                end_time = datetime(2025, 1, 1, current_hour, current_minute) + \
                          timedelta(minutes=duration_minutes)
                end_time_str = end_time.strftime("%I:%M %p")
                
                available_slots.append({
                    "start_time": time_str,
                    "end_time": end_time_str,
                    "duration_minutes": duration_minutes,
                    "available": True
                })
            
            # Move to next slot
            current_minute += slot_interval_minutes
            if current_minute >= 60:
                current_hour += 1
                current_minute = 0
        
        return available_slots
