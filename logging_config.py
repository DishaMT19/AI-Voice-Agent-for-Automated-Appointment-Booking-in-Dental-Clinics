# backend/logging_config.py - Structured logging with audit trails
"""
Structured logging system for the DentalVoice AI backend.
Provides hierarchical loggers for different components.
Logs all pipeline stages, errors, and audit events.
"""

import logging
import logging.handlers
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from functools import wraps

# Import config
from config import LOG_LEVEL, LOG_FORMAT, LOG_FILE, ERROR_LOG_FILE, LOGS_DIR

# ============================================================================
# LOGGER FACTORY
# ============================================================================

class StructuredLogger:
    """Structured logging wrapper for consistent format and audit trail."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup file and console handlers with proper formatting."""
        if self.logger.handlers:
            return
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, LOG_LEVEL))
        console_formatter = logging.Formatter(LOG_FORMAT)
        console_handler.setFormatter(console_formatter)
        
        # File handler (main log)
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(LOG_FORMAT)
        file_handler.setFormatter(file_formatter)
        
        # Error handler (errors only)
        error_handler = logging.handlers.RotatingFileHandler(
            ERROR_LOG_FILE,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(LOG_FORMAT)
        error_handler.setFormatter(error_formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        self.logger.setLevel(logging.DEBUG)
    
    def debug(self, msg: str, **kwargs):
        """Log debug message with context."""
        self.logger.debug(f"{msg} | {self._format_context(kwargs)}" if kwargs else msg)
    
    def info(self, msg: str, **kwargs):
        """Log info message with context."""
        self.logger.info(f"{msg} | {self._format_context(kwargs)}" if kwargs else msg)
    
    def warning(self, msg: str, **kwargs):
        """Log warning message with context."""
        self.logger.warning(f"{msg} | {self._format_context(kwargs)}" if kwargs else msg)
    
    def error(self, msg: str, exc_info: bool = False, **kwargs):
        """Log error message with context and optional traceback."""
        self.logger.error(f"{msg} | {self._format_context(kwargs)}" if kwargs else msg, exc_info=exc_info)
    
    def critical(self, msg: str, exc_info: bool = False, **kwargs):
        """Log critical message with context and optional traceback."""
        self.logger.critical(f"{msg} | {self._format_context(kwargs)}" if kwargs else msg, exc_info=exc_info)
    
    @staticmethod
    def _format_context(context: Dict[str, Any]) -> str:
        """Format context dictionary for logging."""
        if not context:
            return ""
        pairs = [f"{k}={v}" for k, v in context.items()]
        return " ".join(pairs)

# ============================================================================
# AUDIT LOGGER
# ============================================================================

class AuditLogger:
    """Audit trail logger for compliance and debugging."""
    
    def __init__(self):
        self.logger = StructuredLogger("audit")
    
    def log_pipeline_stage(self, stage: str, status: str, data: Optional[Dict] = None, error: Optional[str] = None):
        """Log each pipeline stage with status and data."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "stage": stage,
            "status": status,
            "data": data or {},
            "error": error
        }
        self.logger.info(f"Pipeline stage: {stage}", status=status, error=error)
    
    def log_data_persistence(self, operation: str, file_path: str, success: bool, records: int = 0, error: Optional[str] = None):
        """Log data persistence operations."""
        self.logger.info(f"Data persistence: {operation}", 
                        file=file_path, 
                        success=success, 
                        records=records,
                        error=error)
    
    def log_entity_extraction(self, entity_type: str, input_value: str, output_value: str, confidence: float = 1.0, success: bool = True):
        """Log entity extraction with confidence scores."""
        self.logger.info(f"Entity extraction: {entity_type}",
                        input=input_value,
                        output=output_value,
                        confidence=confidence,
                        success=success)
    
    def log_validation(self, validation_type: str, field: str, value: str, result: str, error: Optional[str] = None):
        """Log validation operations."""
        self.logger.info(f"Validation: {validation_type}",
                        field=field,
                        value=value,
                        result=result,
                        error=error)
    
    def log_notification(self, notification_type: str, recipient: str, status: str, error: Optional[str] = None, provider: Optional[str] = None):
        """Log notification sends."""
        self.logger.info(f"Notification: {notification_type}",
                        recipient=recipient,
                        status=status,
                        error=error,
                        provider=provider)
    
    def log_appointment_saved(self, confirmation_id: str, patient_name: str, success: bool, error: Optional[str] = None):
        """Log successful appointment saves."""
        self.logger.info(f"Appointment saved: {confirmation_id}",
                        patient=patient_name,
                        success=success,
                        error=error)

# ============================================================================
# DECORATORS FOR PIPELINE LOGGING
# ============================================================================

def log_pipeline_stage(stage_name: str, log_input: bool = True, log_output: bool = True):
    """Decorator to log pipeline stages with automatic error handling."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = StructuredLogger(func.__module__)
            audit = AuditLogger()
            
            try:
                if log_input:
                    logger.debug(f"Entering {stage_name}", args_count=len(args), kwargs_keys=list(kwargs.keys()))
                
                result = func(*args, **kwargs)
                
                if log_output:
                    logger.debug(f"Exiting {stage_name} successfully")
                
                audit.log_pipeline_stage(stage=stage_name, status="success")
                return result
                
            except Exception as e:
                logger.error(f"Error in {stage_name}", exc_info=True)
                audit.log_pipeline_stage(stage=stage_name, status="failed", error=str(e))
                raise
        
        return wrapper
    return decorator

def log_operation(operation_name: str):
    """Decorator for general operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = StructuredLogger(func.__module__)
            
            try:
                logger.debug(f"Starting operation: {operation_name}")
                result = func(*args, **kwargs)
                logger.debug(f"Completed operation: {operation_name}")
                return result
            except Exception as e:
                logger.error(f"Failed operation: {operation_name}", exc_info=True)
                raise
        
        return wrapper
    return decorator

# ============================================================================
# GLOBAL LOGGER INSTANCES
# ============================================================================

# Main loggers for different components
logger_storage = StructuredLogger("storage")
logger_nlp = StructuredLogger("nlp")
logger_notifications = StructuredLogger("notifications")
logger_validation = StructuredLogger("validation")
logger_api = StructuredLogger("api")
logger_speech = StructuredLogger("speech")
logger_pipeline = StructuredLogger("pipeline")

# Audit logger
audit_logger = AuditLogger()

# Ensure logs directory exists
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Initialize loggers on import
for log_file in [LOG_FILE, ERROR_LOG_FILE]:
    log_file.parent.mkdir(parents=True, exist_ok=True)
