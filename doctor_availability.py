# doctor_availability.py - Doctor schedule and availability management
"""
Doctor availability and schedule management system.

Manages doctor schedules, availability windows, and validates appointment
requests against doctor availability and existing bookings.

Features:
- Doctor schedule management (working hours, days off)
- Availability checking
- Slot conflict detection
- Smart slot suggestions
- Voice response generation for availability issues
- Strict clinic working hour enforcement (9 AM - 6:30 PM)
- Past booking prevention
"""

import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


class ClinicHoursValidator:
    """
    Centralized clinic operating hours validator.
    
    Enforces strict clinic operating hours: 9:00 AM to 6:30 PM
    - Prevents scheduling outside clinic hours
    - Prevents past bookings
    - Automatically adjusts to next valid slot
    """
    
    CLINIC_START_HOUR = 9  # 9:00 AM (24-hour format)
    CLINIC_START_MIN = 0
    CLINIC_END_HOUR = 18   # 6:30 PM (24-hour format)
    CLINIC_END_MIN = 30
    
    @classmethod
    def get_clinic_hours_str(cls) -> str:
        """Get formatted clinic hours."""
        start = f"{cls.CLINIC_START_HOUR:02d}:{cls.CLINIC_START_MIN:02d}"
        end = f"{cls.CLINIC_END_HOUR:02d}:{cls.CLINIC_END_MIN:02d}"
        
        start_12h = datetime.strptime(start, "%H:%M").strftime("%I:%M %p").lstrip("0")
        end_12h = datetime.strptime(end, "%H:%M").strftime("%I:%M %p").lstrip("0")
        
        return f"{start_12h} to {end_12h}"
    
    @classmethod
    def is_within_clinic_hours(cls, time_str: str) -> bool:
        """
        Check if time is within clinic operating hours.
        
        Args:
            time_str: Time in HH:MM format (24-hour)
        
        Returns:
            True if time is within clinic hours
        """
        try:
            time_obj = datetime.strptime(time_str, "%H:%M").time()
            clinic_start = time(cls.CLINIC_START_HOUR, cls.CLINIC_START_MIN)
            clinic_end = time(cls.CLINIC_END_HOUR, cls.CLINIC_END_MIN)
            
            return clinic_start <= time_obj <= clinic_end
        except ValueError:
            return False
    
    @classmethod
    def is_past_booking(cls, date_str: str, time_str: str) -> bool:
        """
        Check if appointment is in the past.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            time_str: Time in HH:MM format (24-hour)
        
        Returns:
            True if appointment time has already passed
        """
        try:
            appointment_datetime = datetime.strptime(
                f"{date_str} {time_str}", 
                "%Y-%m-%d %H:%M"
            )
            current_datetime = datetime.now()
            
            return appointment_datetime < current_datetime
        except ValueError:
            return False
    
    @classmethod
    def get_next_valid_slot(
        cls,
        start_date_str: str,
        start_time_str: str,
        duration_minutes: int = 30
    ) -> Optional[Dict]:
        """
        Find the next valid clinic slot from requested time.
        
        Searches forward from requested time, respecting:
        - Clinic operating hours (9 AM - 6:30 PM)
        - Current time (no past bookings)
        - 15-minute intervals
        
        Args:
            start_date_str: Start search date (YYYY-MM-DD)
            start_time_str: Start search time (HH:MM)
            duration_minutes: Appointment duration
        
        Returns:
            Dictionary with date and time, or None if no valid slot found
        """
        try:
            # Parse requested datetime
            requested_dt = datetime.strptime(
                f"{start_date_str} {start_time_str}",
                "%Y-%m-%d %H:%M"
            )
            current_dt = datetime.now()
            
            # Start from current time if requested time is in past
            search_dt = max(requested_dt, current_dt)
            
            # Round up to next 15-minute interval
            minutes = search_dt.minute
            if minutes % 15 != 0:
                search_dt = search_dt.replace(minute=0, second=0, microsecond=0)
                search_dt += timedelta(minutes=15 * ((minutes // 15) + 1))
            
            # Search up to 14 days ahead
            search_end = current_dt + timedelta(days=14)
            
            while search_dt <= search_end:
                time_str = search_dt.strftime("%H:%M")
                
                # Check if within clinic hours
                if cls.is_within_clinic_hours(time_str):
                    # Check if appointment can fit before clinic closes
                    end_dt = search_dt + timedelta(minutes=duration_minutes)
                    clinic_end = search_dt.replace(
                        hour=cls.CLINIC_END_HOUR,
                        minute=cls.CLINIC_END_MIN
                    )
                    
                    if end_dt <= clinic_end:
                        return {
                            "date": search_dt.strftime("%Y-%m-%d"),
                            "time": time_str
                        }
                
                # Move to next 15-minute slot
                search_dt += timedelta(minutes=15)
            
            return None
            
        except ValueError:
            return None
    
    @classmethod
    def adjust_to_valid_slot(
        cls,
        date_str: str,
        time_str: str,
        duration_minutes: int = 30
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Validate time and adjust to next valid slot if needed.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            time_str: Time in HH:MM format
            duration_minutes: Appointment duration
        
        Returns:
            Tuple of (is_valid, adjusted_slot, reason_for_adjustment)
        """
        try:
            # Check if past booking
            if cls.is_past_booking(date_str, time_str):
                adjusted = cls.get_next_valid_slot(date_str, time_str, duration_minutes)
                reason = "Requested time is in the past"
                return False, adjusted, reason
            
            # Check if within clinic hours
            if not cls.is_within_clinic_hours(time_str):
                adjusted = cls.get_next_valid_slot(date_str, time_str, duration_minutes)
                clinic_hours = cls.get_clinic_hours_str()
                reason = f"Outside clinic hours ({clinic_hours})"
                return False, adjusted, reason
            
            # Check if appointment fits before clinic closes
            appointment_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            end_dt = appointment_dt + timedelta(minutes=duration_minutes)
            clinic_end = appointment_dt.replace(
                hour=cls.CLINIC_END_HOUR,
                minute=cls.CLINIC_END_MIN
            )
            
            if end_dt > clinic_end:
                adjusted = cls.get_next_valid_slot(date_str, time_str, duration_minutes)
                reason = "Appointment would extend beyond clinic hours"
                return False, adjusted, reason
            
            # All checks passed
            return True, None, None
            
        except ValueError as e:
            adjusted = cls.get_next_valid_slot(date_str, time_str, duration_minutes)
            return False, adjusted, f"Invalid date/time format: {str(e)}"


@dataclass
class DoctorSchedule:
    """Represents a doctor's schedule."""
    doctor_id: str
    doctor_name: str
    specialization: str
    working_days: List[int]  # 0=Monday, 6=Sunday
    start_time: str  # HH:MM format (24-hour)
    end_time: str    # HH:MM format (24-hour)
    lunch_break_start: str  # HH:MM format
    lunch_break_end: str    # HH:MM format
    
    def is_available_on_day(self, day_of_week: int) -> bool:
        """Check if doctor works on the given day (0=Monday, 6=Sunday)."""
        return day_of_week in self.working_days
    
    def get_working_hours_str(self) -> str:
        """Get formatted working hours."""
        return f"{self.start_time} - {self.end_time}"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor_name,
            "specialization": self.specialization,
            "working_days": self.working_days,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "lunch_break_start": self.lunch_break_start,
            "lunch_break_end": self.lunch_break_end,
            "working_hours": self.get_working_hours_str()
        }


@dataclass
class SlotAvailability:
    """Represents slot availability information."""
    is_available: bool
    doctor_id: str
    doctor_name: str
    requested_date: str
    requested_time: str
    unavailability_reason: Optional[str] = None
    suggested_slots: List[Dict] = None
    voice_response: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "is_available": self.is_available,
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor_name,
            "requested_date": self.requested_date,
            "requested_time": self.requested_time,
            "unavailability_reason": self.unavailability_reason,
            "suggested_slots": self.suggested_slots or [],
            "voice_response": self.voice_response
        }


class DoctorAvailabilityManager:
    """Manages doctor schedules and availability."""
    
    # Default doctor schedules
    DEFAULT_DOCTORS = [
        {
            "doctor_id": "doc_001",
            "doctor_name": "Dr. Rajesh Kumar",
            "specialization": "General Dentist",
            "working_days": [0, 1, 2, 3, 4, 5],  # Mon-Sat
            "start_time": "09:00",
            "end_time": "18:00",
            "lunch_break_start": "13:00",
            "lunch_break_end": "14:00"
        },
        {
            "doctor_id": "doc_002",
            "doctor_name": "Dr. Priya Sharma",
            "specialization": "Orthodontist",
            "working_days": [0, 1, 3, 4, 5],  # Mon, Tue, Thu, Fri, Sat (Wed off)
            "start_time": "10:00",
            "end_time": "17:00",
            "lunch_break_start": "12:30",
            "lunch_break_end": "13:30"
        },
        {
            "doctor_id": "doc_003",
            "doctor_name": "Dr. Amit Patel",
            "specialization": "Root Canal Specialist",
            "working_days": [0, 2, 3, 5],  # Mon, Wed, Thu, Sat (Tue, Fri off)
            "start_time": "09:00",
            "end_time": "17:00",
            "lunch_break_start": "13:00",
            "lunch_break_end": "14:00"
        }
    ]
    
    # Voice response templates
    VOICE_TEMPLATES = {
        "en": {
            "doctor_not_available": "I'm sorry, {doctor_name} is not available on {date}. ",
            "slot_booked": "{doctor_name} has another appointment at the requested time. ",
            "lunch_time": "{doctor_name} is on lunch break at that time. ",
            "outside_hours": "{doctor_name} works from {start_time} to {end_time}. ",
            "day_off": "{doctor_name} doesn't work on {day_name}s. ",
            "clinic_outside_hours": "The clinic operates between 9:00 AM and 6:30 PM. ",
            "past_booking": "That time has already passed. ",
            "suggestion": "The next available slot is at {suggested_time} on {suggested_date}. ",
            "confirm_slot": "Would you like to book this slot? Please say yes or no."
        },
        "hi": {
            "doctor_not_available": "मुझे खेद है, {doctor_name} {date} को उपलब्ध नहीं हैं। ",
            "slot_booked": "{doctor_name} के पास अनुरोधित समय पर एक और नियुक्ति है। ",
            "lunch_time": "{doctor_name} उस समय दोपहर के भोजन पर हैं। ",
            "outside_hours": "{doctor_name} {start_time} से {end_time} तक काम करते हैं। ",
            "day_off": "{doctor_name} {day_name} को काम नहीं करते। ",
            "clinic_outside_hours": "क्लिनिक सुबह 9:00 बजे से शाम 6:30 बजे तक खुली है। ",
            "past_booking": "वह समय पहले ही बीत चुका है। ",
            "suggestion": "अगली उपलब्ध खिड़की {suggested_date} को {suggested_time} पर है। ",
            "confirm_slot": "क्या आप इस स्लॉट को बुक करना चाहते हैं? कृपया हां या नहीं कहें।"
        }
    }
    
    def __init__(self, doctors: List[Dict] = None):
        """
        Initialize availability manager.
        
        Args:
            doctors: List of doctor schedule dictionaries
        """
        self.doctors = {}
        
        # Use provided doctors or defaults
        doctor_list = doctors or self.DEFAULT_DOCTORS
        
        for doc_data in doctor_list:
            schedule = DoctorSchedule(
                doctor_id=doc_data["doctor_id"],
                doctor_name=doc_data["doctor_name"],
                specialization=doc_data["specialization"],
                working_days=doc_data["working_days"],
                start_time=doc_data["start_time"],
                end_time=doc_data["end_time"],
                lunch_break_start=doc_data["lunch_break_start"],
                lunch_break_end=doc_data["lunch_break_end"]
            )
            self.doctors[doc_data["doctor_id"]] = schedule
    
    def get_doctor_schedule(self, doctor_id: str) -> Optional[DoctorSchedule]:
        """Get schedule for a specific doctor."""
        return self.doctors.get(doctor_id)
    
    def get_all_doctors(self) -> List[Dict]:
        """Get all doctor information."""
        return [doc.to_dict() for doc in self.doctors.values()]
    
    def is_doctor_available_on_date(self, doctor_id: str, date_str: str) -> Tuple[bool, Optional[str]]:
        """
        Check if doctor is available on a given date.
        
        Args:
            doctor_id: Doctor ID
            date_str: Date in YYYY-MM-DD format
        
        Returns:
            Tuple of (is_available, reason_if_not)
        """
        doctor = self.get_doctor_schedule(doctor_id)
        if not doctor:
            return False, "Doctor not found"
        
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            day_of_week = date_obj.weekday()
            
            if not doctor.is_available_on_day(day_of_week):
                day_name = date_obj.strftime("%A")
                return False, f"{doctor.doctor_name} doesn't work on {day_name}s"
            
            return True, None
        except ValueError:
            return False, "Invalid date format"
    
    def is_time_in_working_hours(self, doctor_id: str, time_str: str) -> bool:
        """
        Check if time is within doctor's working hours.
        
        Args:
            doctor_id: Doctor ID
            time_str: Time in HH:MM format (24-hour)
        
        Returns:
            True if time is within working hours
        """
        doctor = self.get_doctor_schedule(doctor_id)
        if not doctor:
            return False
        
        try:
            # Parse times
            request_time = datetime.strptime(time_str, "%H:%M").time()
            start = datetime.strptime(doctor.start_time, "%H:%M").time()
            end = datetime.strptime(doctor.end_time, "%H:%M").time()
            
            return start <= request_time < end
        except ValueError:
            return False
    
    def is_lunch_time(self, doctor_id: str, time_str: str) -> bool:
        """
        Check if time is during doctor's lunch break.
        
        Args:
            doctor_id: Doctor ID
            time_str: Time in HH:MM format (24-hour)
        
        Returns:
            True if time is during lunch break
        """
        doctor = self.get_doctor_schedule(doctor_id)
        if not doctor:
            return False
        
        try:
            request_time = datetime.strptime(time_str, "%H:%M").time()
            lunch_start = datetime.strptime(doctor.lunch_break_start, "%H:%M").time()
            lunch_end = datetime.strptime(doctor.lunch_break_end, "%H:%M").time()
            
            return lunch_start <= request_time < lunch_end
        except ValueError:
            return False
    
    def get_next_available_slot(
        self,
        doctor_id: str,
        current_date_str: str,
        current_time_str: str,
        duration_minutes: int = 30
    ) -> Optional[Dict]:
        """
        Find the next available time slot for a doctor.
        
        Args:
            doctor_id: Doctor ID
            current_date_str: Starting date in YYYY-MM-DD format
            current_time_str: Starting time in HH:MM format (24-hour)
            duration_minutes: Appointment duration in minutes
        
        Returns:
            Dictionary with available slot info or None
        """
        doctor = self.get_doctor_schedule(doctor_id)
        if not doctor:
            return None
        
        try:
            current_datetime = datetime.strptime(
                f"{current_date_str} {current_time_str}",
                "%Y-%m-%d %H:%M"
            )
            
            # Start from next time slot (15-minute intervals)
            search_datetime = current_datetime + timedelta(minutes=15)
            search_datetime = search_datetime.replace(
                minute=(search_datetime.minute // 15 + 1) * 15
            )
            
            # Search for next 14 days
            for day_offset in range(14):
                search_date = search_datetime.date() + timedelta(days=day_offset)
                
                # Check if doctor works this day
                if not doctor.is_available_on_date(search_date.strftime("%Y-%m-%d"))[0]:
                    continue
                
                # Try each slot in the day
                current_slot = datetime.combine(search_date, datetime.min.time())
                start_hour = int(doctor.start_time.split(':')[0])
                current_slot = current_slot.replace(hour=start_hour)
                
                while True:
                    slot_time = current_slot.time().strftime("%H:%M")
                    
                    # Check if we've passed end of day
                    if not self.is_time_in_working_hours(doctor_id, slot_time):
                        break
                    
                    # Check if not lunch time
                    if not self.is_lunch_time(doctor_id, slot_time):
                        return {
                            "date": search_date.strftime("%Y-%m-%d"),
                            "time": slot_time,
                            "doctor_id": doctor_id,
                            "doctor_name": doctor.doctor_name,
                            "day_name": search_date.strftime("%A")
                        }
                    
                    current_slot += timedelta(minutes=15)
            
            return None
        except ValueError:
            return None


class SlotConflictValidator:
    """Validates appointment slots for conflicts."""
    
    def __init__(self, appointments: List[Dict] = None):
        """
        Initialize validator.
        
        Args:
            appointments: List of existing appointments
        """
        self.appointments = appointments or []
    
    def set_appointments(self, appointments: List[Dict]):
        """Update appointment list."""
        self.appointments = appointments
    
    def has_conflict(
        self,
        doctor_id: str,
        date_str: str,
        time_str: str,
        duration_minutes: int = 30
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Check if appointment time conflicts with existing bookings.
        
        Args:
            doctor_id: Doctor ID
            date_str: Date in YYYY-MM-DD format
            time_str: Time in HH:MM format (24-hour)
            duration_minutes: Appointment duration in minutes
        
        Returns:
            Tuple of (has_conflict, conflicting_appointment)
        """
        try:
            request_start = datetime.strptime(
                f"{date_str} {time_str}",
                "%Y-%m-%d %H:%M"
            )
            request_end = request_start + timedelta(minutes=duration_minutes)
            
            for appt in self.appointments:
                appt_doctor = appt.get("appointment", {}).get("doctor_id", "doc_001")
                
                # Only check conflicts for same doctor
                if appt_doctor != doctor_id:
                    continue
                
                appt_date = appt.get("appointment", {}).get("date")
                appt_time = appt.get("appointment", {}).get("time")
                appt_duration = appt.get("appointment", {}).get("duration_minutes", 30)
                
                if not appt_date or not appt_time:
                    continue
                
                try:
                    appt_start = datetime.strptime(
                        f"{appt_date} {appt_time}",
                        "%Y-%m-%d %H:%M"
                    )
                    appt_end = appt_start + timedelta(minutes=appt_duration)
                    
                    # Check for overlap
                    if request_start < appt_end and request_end > appt_start:
                        return True, {
                            "doctor_id": doctor_id,
                            "date": appt_date,
                            "time": appt_time,
                            "duration_minutes": appt_duration,
                            "patient_name": appt.get("patient", {}).get("name", "Another patient")
                        }
                except ValueError:
                    continue
            
            return False, None
        except ValueError:
            return False, None


class VoiceResponseGenerator:
    """Generates voice responses for availability issues."""
    
    @staticmethod
    def generate_unavailability_response(
        slot_availability: SlotAvailability,
        language: str = "en"
    ) -> str:
        """
        Generate voice response for unavailable slot.
        
        Args:
            slot_availability: SlotAvailability object
            language: Language code
        
        Returns:
            Voice response text
        """
        templates = DoctorAvailabilityManager.VOICE_TEMPLATES.get(language, {})
        response = ""
        
        # Add unavailability reason
        if slot_availability.unavailability_reason:
            reason = slot_availability.unavailability_reason
            
            if "lunch" in reason.lower():
                response += templates.get(
                    "lunch_time",
                    "The doctor is on lunch break at that time. "
                ).format(doctor_name=slot_availability.doctor_name)
            elif "not work" in reason.lower():
                response += templates.get(
                    "day_off",
                    "The doctor doesn't work on that day. "
                ).format(doctor_name=slot_availability.doctor_name, day_name="")
            else:
                response += templates.get(
                    "slot_booked",
                    "The selected time is already booked. "
                ).format(doctor_name=slot_availability.doctor_name)
        
        # Add suggestion
        if slot_availability.suggested_slots:
            suggested = slot_availability.suggested_slots[0]
            response += templates.get(
                "suggestion",
                "The next available slot is at {suggested_time} on {suggested_date}. "
            ).format(
                suggested_time=suggested.get("time", ""),
                suggested_date=suggested.get("date", "")
            )
        
        # Add confirmation prompt
        response += templates.get(
            "confirm_slot",
            "Would you like to book this slot? Please say yes or no."
        )
        
        return response.strip()
    
    @staticmethod
    def generate_availability_response(
        doctor_name: str,
        date: str,
        time: str,
        language: str = "en"
    ) -> str:
        """
        Generate voice response for available slot.
        
        Args:
            doctor_name: Doctor name
            date: Date in YYYY-MM-DD format
            time: Time in HH:MM format
            language: Language code
        
        Returns:
            Voice response text
        """
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_str = date_obj.strftime("%B %d, %Y")
        time_str = datetime.strptime(time, "%H:%M").strftime("%I:%M %p")
        
        templates = {
            "en": f"Perfect! I've booked your appointment with {doctor_name} on {date_str} at {time_str}. Your confirmation ID is {{confirmation_id}}. Thank you for choosing our clinic.",
            "hi": f"बिल्कुल! मैंने {doctor_name} के साथ आपकी नियुक्ति {date_str} को {time_str} पर बुक कर दी है। आपकी पुष्टि ID {{confirmation_id}} है। हमारी क्लिनिक का चयन करने के लिए धन्यवाद।"
        }
        
        return templates.get(language, templates["en"])


class DoctorAvailabilityValidator:
    """Complete validation system combining availability and conflicts."""
    
    def __init__(self, doctors: List[Dict] = None, appointments: List[Dict] = None):
        """
        Initialize validator.
        
        Args:
            doctors: List of doctor schedules
            appointments: List of existing appointments
        """
        self.availability_manager = DoctorAvailabilityManager(doctors)
        self.conflict_validator = SlotConflictValidator(appointments)
    
    def validate_appointment_slot(
        self,
        doctor_id: str,
        date_str: str,
        time_str: str,
        duration_minutes: int = 30,
        language: str = "en",
        convert_time: bool = False
    ) -> SlotAvailability:
        """
        Validate appointment slot comprehensively.
        
        Validation steps (in order):
        1. Clinic hours enforcement (9 AM - 6:30 PM)
        2. Past booking prevention
        3. Doctor existence check
        4. Doctor availability on date
        5. Doctor working hours
        6. Lunch break check
        7. Appointment conflicts
        
        Args:
            doctor_id: Doctor ID
            date_str: Date in YYYY-MM-DD format
            time_str: Time (HH:MM 24-hour if convert_time=False, else 12-hour AM/PM)
            duration_minutes: Appointment duration
            language: Language for voice response
            convert_time: If True, convert from 12-hour to 24-hour format
        
        Returns:
            SlotAvailability object
        """
        # Convert time if needed
        if convert_time:
            try:
                time_obj = datetime.strptime(time_str, "%I:%M %p")
                time_str = time_obj.strftime("%H:%M")
            except ValueError:
                return SlotAvailability(
                    is_available=False,
                    doctor_id=doctor_id,
                    doctor_name="Unknown",
                    requested_date=date_str,
                    requested_time=time_str,
                    unavailability_reason="Invalid time format"
                )
        
        # STEP 1: CLINIC HOURS ENFORCEMENT (Centralized)
        is_valid, adjusted_slot, clinic_reason = ClinicHoursValidator.adjust_to_valid_slot(
            date_str, time_str, duration_minutes
        )
        
        if not is_valid:
            # Get adjusted slot or find next one
            if not adjusted_slot:
                adjusted_slot = ClinicHoursValidator.get_next_valid_slot(
                    date_str, time_str, duration_minutes
                )
            
            doctor = self.availability_manager.get_doctor_schedule(doctor_id)
            doctor_name = doctor.doctor_name if doctor else "Unknown"
            
            # Format voice response for clinic hours issue
            templates = DoctorAvailabilityManager.VOICE_TEMPLATES.get(language, {})
            response = templates.get(
                "clinic_outside_hours",
                "The clinic operates between 9:00 AM and 6:30 PM. "
            )
            
            if adjusted_slot:
                suggested_time = datetime.strptime(
                    adjusted_slot["time"], "%H:%M"
                ).strftime("%I:%M %p").lstrip("0")
                suggested_date = datetime.strptime(
                    adjusted_slot["date"], "%Y-%m-%d"
                ).strftime("%B %d, %Y")
                
                response += templates.get(
                    "suggestion",
                    "The next available slot is at {suggested_time} on {suggested_date}. "
                ).format(
                    suggested_time=suggested_time,
                    suggested_date=suggested_date
                )
            
            response += templates.get(
                "confirm_slot",
                "Would you like to book this slot? Please say yes or no."
            )
            
            return SlotAvailability(
                is_available=False,
                doctor_id=doctor_id,
                doctor_name=doctor_name,
                requested_date=date_str,
                requested_time=time_str,
                unavailability_reason=clinic_reason,
                suggested_slots=[adjusted_slot] if adjusted_slot else [],
                voice_response=response
            )
        
        # Check if doctor exists
        doctor = self.availability_manager.get_doctor_schedule(doctor_id)
        
        if not doctor:
            return SlotAvailability(
                is_available=False,
                doctor_id=doctor_id,
                doctor_name="Unknown",
                requested_date=date_str,
                requested_time=time_str,
                unavailability_reason="Doctor not found"
            )
        
        # STEP 2: Doctor available on date
        is_available, reason = self.availability_manager.is_doctor_available_on_date(
            doctor_id, date_str
        )
        
        if not is_available:
            # Find next available slot
            suggested = self.availability_manager.get_next_available_slot(
                doctor_id, date_str, time_str, duration_minutes
            )
            
            return SlotAvailability(
                is_available=False,
                doctor_id=doctor_id,
                doctor_name=doctor.doctor_name,
                requested_date=date_str,
                requested_time=time_str,
                unavailability_reason=reason,
                suggested_slots=[suggested] if suggested else [],
                voice_response=VoiceResponseGenerator.generate_unavailability_response(
                    SlotAvailability(
                        is_available=False,
                        doctor_id=doctor_id,
                        doctor_name=doctor.doctor_name,
                        requested_date=date_str,
                        requested_time=time_str,
                        unavailability_reason=reason,
                        suggested_slots=[suggested] if suggested else []
                    ),
                    language
                )
            )
        
        # STEP 3: Time within working hours
        if not self.availability_manager.is_time_in_working_hours(doctor_id, time_str):
            suggested = self.availability_manager.get_next_available_slot(
                doctor_id, date_str, time_str, duration_minutes
            )
            
            reason = f"{doctor.doctor_name} works from {doctor.start_time} to {doctor.end_time}"
            
            return SlotAvailability(
                is_available=False,
                doctor_id=doctor_id,
                doctor_name=doctor.doctor_name,
                requested_date=date_str,
                requested_time=time_str,
                unavailability_reason=reason,
                suggested_slots=[suggested] if suggested else [],
                voice_response=VoiceResponseGenerator.generate_unavailability_response(
                    SlotAvailability(
                        is_available=False,
                        doctor_id=doctor_id,
                        doctor_name=doctor.doctor_name,
                        requested_date=date_str,
                        requested_time=time_str,
                        unavailability_reason=reason,
                        suggested_slots=[suggested] if suggested else []
                    ),
                    language
                )
            )
        
        # STEP 4: Not during lunch break
        if self.availability_manager.is_lunch_time(doctor_id, time_str):
            suggested = self.availability_manager.get_next_available_slot(
                doctor_id, date_str, time_str, duration_minutes
            )
            
            reason = f"{doctor.doctor_name} is on lunch break at that time"
            
            return SlotAvailability(
                is_available=False,
                doctor_id=doctor_id,
                doctor_name=doctor.doctor_name,
                requested_date=date_str,
                requested_time=time_str,
                unavailability_reason=reason,
                suggested_slots=[suggested] if suggested else [],
                voice_response=VoiceResponseGenerator.generate_unavailability_response(
                    SlotAvailability(
                        is_available=False,
                        doctor_id=doctor_id,
                        doctor_name=doctor.doctor_name,
                        requested_date=date_str,
                        requested_time=time_str,
                        unavailability_reason=reason,
                        suggested_slots=[suggested] if suggested else []
                    ),
                    language
                )
            )
        
        # STEP 5: No conflicts with existing appointments
        has_conflict, conflicting_appt = self.conflict_validator.has_conflict(
            doctor_id, date_str, time_str, duration_minutes
        )
        
        if has_conflict:
            suggested = self.availability_manager.get_next_available_slot(
                doctor_id, date_str, time_str, duration_minutes
            )
            
            reason = f"Time slot is booked with another patient"
            
            return SlotAvailability(
                is_available=False,
                doctor_id=doctor_id,
                doctor_name=doctor.doctor_name,
                requested_date=date_str,
                requested_time=time_str,
                unavailability_reason=reason,
                suggested_slots=[suggested] if suggested else [],
                voice_response=VoiceResponseGenerator.generate_unavailability_response(
                    SlotAvailability(
                        is_available=False,
                        doctor_id=doctor_id,
                        doctor_name=doctor.doctor_name,
                        requested_date=date_str,
                        requested_time=time_str,
                        unavailability_reason=reason,
                        suggested_slots=[suggested] if suggested else []
                    ),
                    language
                )
            )
        
        # All checks passed
        return SlotAvailability(
            is_available=True,
            doctor_id=doctor_id,
            doctor_name=doctor.doctor_name,
            requested_date=date_str,
            requested_time=time_str,
            unavailability_reason=None,
            suggested_slots=[],
            voice_response=VoiceResponseGenerator.generate_availability_response(
                doctor.doctor_name, date_str, time_str, language
            )
        )
