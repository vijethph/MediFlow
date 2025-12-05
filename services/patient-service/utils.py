"""Utility functions for the Patient Management Service."""
from typing import Optional
from datetime import datetime, date
import re


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format.
    
    Args:
        phone: Phone number string
        
    Returns:
        True if valid, False otherwise
    """
    if not phone:
        return False
    
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
    
    # Check if it contains only digits and has reasonable length
    return cleaned.isdigit() and 7 <= len(cleaned) <= 15


def validate_date_of_birth(dob: date) -> bool:
    """
    Validate date of birth (must be in the past and reasonable).
    
    Args:
        dob: Date of birth
        
    Returns:
        True if valid, False otherwise
    """
    if not dob:
        return False
    
    today = date.today()
    
    # Check if date is in the past
    if dob >= today:
        return False
    
    # Check if date is reasonable (not more than 150 years ago)
    age = (today - dob).days / 365.25
    if age > 150:
        return False
    
    return True


def format_patient_id(patient_id: str) -> str:
    """
    Format patient ID for display.
    
    Args:
        patient_id: Patient ID string
        
    Returns:
        Formatted patient ID
    """
    if not patient_id:
        return ""
    
    # Ensure it starts with PAT-
    if not patient_id.startswith("PAT-"):
        return f"PAT-{patient_id}"
    
    return patient_id.upper()


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
    
    # Remove potentially dangerous characters
    text = text.strip()
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    return text


def calculate_age(date_of_birth: Optional[date]) -> Optional[int]:
    """
    Calculate age from date of birth.
    
    Args:
        date_of_birth: Date of birth
        
    Returns:
        Age in years or None if date_of_birth is None
    """
    if not date_of_birth:
        return None
    
    today = date.today()
    age = today.year - date_of_birth.year
    
    # Adjust if birthday hasn't occurred this year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    
    return age


def mask_email(email: str) -> str:
    """
    Mask email address for logging (privacy protection).
    
    Args:
        email: Email address
        
    Returns:
        Masked email (e.g., j***@example.com)
    """
    if not email or '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    
    if len(local) <= 1:
        masked_local = '*'
    else:
        masked_local = local[0] + '*' * (len(local) - 1)
    
    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    """
    Mask phone number for logging (privacy protection).
    
    Args:
        phone: Phone number
        
    Returns:
        Masked phone (e.g., +1234***7890)
    """
    if not phone or len(phone) < 4:
        return phone
    
    # Show first 4 and last 4 digits
    return phone[:4] + '*' * (len(phone) - 8) + phone[-4:]


def validate_blood_group(blood_group: Optional[str]) -> bool:
    """
    Validate blood group format.
    
    Args:
        blood_group: Blood group string
        
    Returns:
        True if valid, False otherwise
    """
    if not blood_group:
        return True  # Optional field
    
    valid_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    return blood_group.upper() in valid_groups

