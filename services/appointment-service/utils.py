"""Utility functions for the Appointment Management Service."""
from typing import Optional
from datetime import datetime, date, time
import re


def validate_time_format(time_str: str) -> bool:
    """
    Validate time format (HH:MM).
    
    Args:
        time_str: Time string
        
    Returns:
        True if valid, False otherwise
    """
    if not time_str:
        return False
    
    pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
    return bool(re.match(pattern, time_str))


def validate_appointment_date(appointment_date: datetime) -> bool:
    """
    Validate appointment date (must be in the future).
    
    Args:
        appointment_date: Appointment date and time
        
    Returns:
        True if valid, False otherwise
    """
    if not appointment_date:
        return False
    
    return appointment_date > datetime.utcnow()


def calculate_end_time(start_time: datetime, duration_minutes: int) -> datetime:
    """
    Calculate end time from start time and duration.
    
    Args:
        start_time: Appointment start time
        duration_minutes: Duration in minutes
        
    Returns:
        End time
    """
    from datetime import timedelta
    return start_time + timedelta(minutes=duration_minutes)


def format_appointment_id(appointment_id: str) -> str:
    """
    Format appointment ID for display.
    
    Args:
        appointment_id: Appointment ID string
        
    Returns:
        Formatted appointment ID
    """
    if not appointment_id:
        return ""
    
    if not appointment_id.startswith("APT-"):
        return f"APT-{appointment_id}"
    
    return appointment_id.upper()


def is_working_hours(appointment_time: time, start_time: str = "09:00", end_time: str = "17:00") -> bool:
    """
    Check if appointment time is within working hours.
    
    Args:
        appointment_time: Appointment time
        start_time: Working hours start (HH:MM)
        end_time: Working hours end (HH:MM)
        
    Returns:
        True if within working hours, False otherwise
    """
    start = datetime.strptime(start_time, "%H:%M").time()
    end = datetime.strptime(end_time, "%H:%M").time()
    
    return start <= appointment_time <= end


def get_appointment_duration_display(duration_minutes: int) -> str:
    """
    Get human-readable duration display.
    
    Args:
        duration_minutes: Duration in minutes
        
    Returns:
        Formatted duration string
    """
    if duration_minutes < 60:
        return f"{duration_minutes} minutes"
    else:
        hours = duration_minutes // 60
        minutes = duration_minutes % 60
        if minutes == 0:
            return f"{hours} hour{'s' if hours > 1 else ''}"
        else:
            return f"{hours} hour{'s' if hours > 1 else ''} {minutes} minute{'s' if minutes > 1 else ''}"


def sanitize_input(text: Optional[str]) -> Optional[str]:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        text: Input text
        
    Returns:
        Sanitized text
    """
    if not text:
        return text
    
    text = text.strip()
    text = text.replace('\x00', '')
    return text

