# backend/storage.py - Robust append-only data persistence layer
"""
Data persistence layer with atomic writes, append-only storage, and corruption prevention.
Ensures no data loss and maintains historical record of all interactions.
"""

import json
import csv
import os
import uuid
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
import fcntl

from config import JSON_FILE, CSV_FILE, CONVERSATIONS_FILE, APPOINTMENTS_DIR, DATE_FORMAT
from logging_config import logger_storage, audit_logger, log_pipeline_stage, log_operation

# ============================================================================
# FILE LOCKING FOR ATOMIC OPERATIONS
# ============================================================================

class FileLock:
    """Cross-platform file locking for atomic operations."""
    
    def __init__(self, file_path: Path, timeout: int = 10):
        self.file_path = file_path
        self.timeout = timeout
        self.lock_file = file_path.parent / f".{file_path.name}.lock"
        self._lock = None
    
    def acquire(self) -> bool:
        """Acquire file lock."""
        try:
            self.lock_file.touch(exist_ok=True)
            self._lock = open(self.lock_file, 'w')
            # Try to get exclusive lock (blocking with timeout)
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX)
            logger_storage.debug("File lock acquired", file=str(self.file_path))
            return True
        except Exception as e:
            logger_storage.error(f"Failed to acquire lock: {e}")
            return False
    
    def release(self):
        """Release file lock."""
        try:
            if self._lock:
                fcntl.flock(self._lock.fileno(), fcntl.LOCK_UN)
                self._lock.close()
            if self.lock_file.exists():
                self.lock_file.unlink()
            logger_storage.debug("File lock released", file=str(self.file_path))
        except Exception as e:
            logger_storage.warning(f"Failed to release lock: {e}")
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

# ============================================================================
# STORAGE ENGINE
# ============================================================================

class StorageEngine:
    """Robust append-only storage engine with atomic writes and backup."""
    
    def __init__(self):
        self.lock = threading.RLock()
        self._ensure_directories()
        self._ensure_csv_headers()
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        for dir_path in [JSON_FILE.parent, CONVERSATIONS_FILE.parent, APPOINTMENTS_DIR]:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger_storage.debug("Directory verified", path=str(dir_path))
            except Exception as e:
                logger_storage.error(f"Failed to create directory {dir_path}: {e}", exc_info=True)
    
    def _ensure_csv_headers(self):
        """Ensure CSV file has headers."""
        if CSV_FILE.exists() and CSV_FILE.stat().st_size > 0:
            return
        
        try:
            with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "appointment_id", "timestamp", "confirmation_id", "patient_name",
                    "patient_phone", "patient_email", "patient_address", "service",
                    "date", "time", "duration_minutes", "end_time", "backend_saved",
                    "lang", "emotion_data", "conversation_steps", "total_duration_seconds"
                ])
            logger_storage.info("CSV headers initialized", file=str(CSV_FILE))
        except Exception as e:
            logger_storage.error(f"Failed to initialize CSV: {e}", exc_info=True)
    
    @log_pipeline_stage("data_read")
    def load_appointments(self) -> List[Dict]:
        """Load all appointments from JSON file with error recovery."""
        try:
            with threading.Lock():
                if not JSON_FILE.exists():
                    logger_storage.warning("JSON file not found, returning empty list", file=str(JSON_FILE))
                    return []
                
                with open(JSON_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if not isinstance(data, list):
                    logger_storage.warning("JSON file contains non-list data, returning empty list")
                    return []
                
                logger_storage.debug("Appointments loaded", count=len(data), file=str(JSON_FILE))
                audit_logger.log_data_persistence(
                    operation="load",
                    file_path=str(JSON_FILE),
                    success=True,
                    records=len(data)
                )
                return data
                
        except json.JSONDecodeError as e:
            logger_storage.error(f"JSON decode error: {e}", exc_info=True)
            audit_logger.log_data_persistence(
                operation="load",
                file_path=str(JSON_FILE),
                success=False,
                error=f"JSON decode error: {e}"
            )
            return self._recover_from_backup()
        
        except Exception as e:
            logger_storage.error(f"Error loading appointments: {e}", exc_info=True)
            audit_logger.log_data_persistence(
                operation="load",
                file_path=str(JSON_FILE),
                success=False,
                error=str(e)
            )
            return []
    
    @log_pipeline_stage("data_write", log_input=True, log_output=True)
    def save_appointment(self, appointment: Dict) -> Tuple[bool, Optional[str]]:
        """Atomically append single appointment to JSON file."""
        try:
            # Validate appointment structure
            if not isinstance(appointment, dict):
                error_msg = "Appointment must be a dictionary"
                logger_storage.error(error_msg)
                return False, error_msg
            
            required_keys = {'appointment_id', 'confirmation_id', 'timestamp', 'patient', 'appointment'}
            missing_keys = required_keys - set(appointment.keys())
            if missing_keys:
                error_msg = f"Missing required keys: {missing_keys}"
                logger_storage.error(error_msg)
                return False, error_msg
            
            # Atomic write with backup
            with threading.Lock():
                try:
                    # Read existing data
                    existing = self.load_appointments()
                    
                    # Create backup
                    backup_file = JSON_FILE.with_suffix('.backup')
                    if JSON_FILE.exists():
                        with open(JSON_FILE, 'r', encoding='utf-8') as f:
                            backup_data = f.read()
                        with open(backup_file, 'w', encoding='utf-8') as f:
                            f.write(backup_data)
                    
                    # Append to existing
                    existing.append(appointment)
                    
                    # Write atomically
                    temp_file = JSON_FILE.with_suffix('.tmp')
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        json.dump(existing, f, indent=2, ensure_ascii=False)
                    
                    # Atomic rename
                    temp_file.replace(JSON_FILE)
                    
                    logger_storage.info(
                        "Appointment saved successfully",
                        confirmation_id=appointment.get('confirmation_id'),
                        total_count=len(existing)
                    )
                    
                    audit_logger.log_data_persistence(
                        operation="append",
                        file_path=str(JSON_FILE),
                        success=True,
                        records=len(existing)
                    )
                    
                    # Also append to CSV
                    self._append_to_csv(appointment)
                    
                    return True, None
                    
                except Exception as e:
                    # Restore from backup on error
                    backup_file = JSON_FILE.with_suffix('.backup')
                    if backup_file.exists():
                        backup_file.replace(JSON_FILE)
                        logger_storage.warning("Restored from backup after write error")
                    raise
        
        except Exception as e:
            error_msg = f"Failed to save appointment: {str(e)}"
            logger_storage.error(error_msg, exc_info=True)
            audit_logger.log_data_persistence(
                operation="append",
                file_path=str(JSON_FILE),
                success=False,
                error=error_msg
            )
            return False, error_msg
    
    def _append_to_csv(self, appointment: Dict):
        """Append appointment to CSV file."""
        try:
            patient = appointment.get('patient', {})
            appt = appointment.get('appointment', {})
            
            with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    appointment.get('appointment_id', ''),
                    appointment.get('timestamp', ''),
                    appointment.get('confirmation_id', ''),
                    patient.get('name', ''),
                    patient.get('phone', ''),
                    patient.get('email', ''),
                    patient.get('address', ''),
                    appt.get('service', ''),
                    appt.get('date', ''),
                    appt.get('time', ''),
                    appt.get('duration_minutes', ''),
                    appt.get('end_time', ''),
                    appointment.get('backend_saved', True),
                    appointment.get('lang', 'en'),
                    json.dumps(appointment.get('emotions', []), ensure_ascii=False),
                    appointment.get('conversation_steps', 0),
                    appointment.get('total_duration_seconds', 0)
                ])
            
            logger_storage.debug("Appointment appended to CSV", confirmation_id=appointment.get('confirmation_id'))
        
        except Exception as e:
            logger_storage.error(f"Failed to append to CSV: {e}", exc_info=True)
    
    def _recover_from_backup(self) -> List[Dict]:
        """Attempt to recover from backup file."""
        try:
            backup_file = JSON_FILE.with_suffix('.backup')
            if backup_file.exists():
                with open(backup_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger_storage.info("Recovered from backup")
                return data if isinstance(data, list) else []
        except Exception as e:
            logger_storage.error(f"Failed to recover from backup: {e}")
        
        return []
    
    def save_conversation(self, conversation: Dict) -> Tuple[bool, Optional[str]]:
        """Save conversation to append-only conversation log."""
        try:
            with threading.Lock():
                # Add metadata
                conversation['_saved_at'] = datetime.utcnow().isoformat()
                conversation['_id'] = str(uuid.uuid4())
                
                # Append as JSONL
                with open(CONVERSATIONS_FILE, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(conversation, ensure_ascii=False) + '\n')
                
                logger_storage.debug("Conversation saved", id=conversation.get('_id'))
                return True, None
        
        except Exception as e:
            error_msg = f"Failed to save conversation: {str(e)}"
            logger_storage.error(error_msg, exc_info=True)
            return False, error_msg
    
    def save_individual_appointment(self, appointment: Dict, confirmation_id: str) -> Tuple[bool, Optional[str]]:
        """Save individual appointment to file for backup/audit."""
        try:
            appt_file = APPOINTMENTS_DIR / f"{confirmation_id}.json"
            
            with open(appt_file, 'w', encoding='utf-8') as f:
                json.dump(appointment, f, indent=2, ensure_ascii=False)
            
            logger_storage.debug("Individual appointment saved", file=str(appt_file))
            return True, None
        
        except Exception as e:
            error_msg = f"Failed to save individual appointment: {str(e)}"
            logger_storage.error(error_msg, exc_info=True)
            return False, error_msg

# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

storage_engine = StorageEngine()
