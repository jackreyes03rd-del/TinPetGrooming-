from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from flask import flash, jsonify, session

WarningCategory = Literal["warning", "error", "success", "info"]

                             
MAX_LOGIN_ATTEMPTS = 3
LOCKOUT_DURATION = 30           

def flash_warning(message: str, category: WarningCategory = "warning") -> None:
    flash(message, category)

def json_warning(message: str, success: bool = False, **extra_data) -> tuple:
    response = {
        "success": success,
        "warning": message if not success else None,
        "message": message if success else None,
        **extra_data
    }
    status_code = 200 if success else 400
    return jsonify(response), status_code

def check_rate_limit(identifier: str, max_attempts: int = MAX_LOGIN_ATTEMPTS, 
                     lockout_duration: int = LOCKOUT_DURATION) -> tuple[bool, int | None]:
    now = datetime.utcnow()
    attempts_key = f"{identifier}_attempts"
    lockout_key = f"{identifier}_locked_until"
    
                                   
    locked_until = session.get(lockout_key)
    if locked_until:
        locked_until_dt = datetime.fromisoformat(locked_until)
        if now < locked_until_dt:
            remaining = int((locked_until_dt - now).total_seconds())
            return False, remaining
        else:
                                       
            session.pop(lockout_key, None)
            session.pop(attempts_key, None)
    
    return True, None

def record_failed_attempt(identifier: str, max_attempts: int = MAX_LOGIN_ATTEMPTS,
                         lockout_duration: int = LOCKOUT_DURATION) -> tuple[int, bool]:
    now = datetime.utcnow()
    attempts_key = f"{identifier}_attempts"
    lockout_key = f"{identifier}_locked_until"
    
                             
    attempts = session.get(attempts_key, 0) + 1
    session[attempts_key] = attempts
    
                                 
    if attempts >= max_attempts:
        locked_until = now + timedelta(seconds=lockout_duration)
        session[lockout_key] = locked_until.isoformat()
        return attempts, True
    
    return attempts, False

def clear_rate_limit(identifier: str) -> None:
    attempts_key = f"{identifier}_attempts"
    lockout_key = f"{identifier}_locked_until"
    session.pop(attempts_key, None)
    session.pop(lockout_key, None)

                                                  
class WarningMessages:
    
                    
    LOGIN_INVALID = "Invalid email or password."
    LOGIN_FIELDS_REQUIRED = "Email and password are required."
    LOGIN_TOO_MANY_ATTEMPTS = "Too many failed login attempts. Please wait {seconds} seconds before trying again."
    LOGIN_NO_ACCOUNT = "No account found with this email address. <a href='{url}'>Register here</a>."
    
                           
    REGISTER_EMAIL_EXISTS = "Email is already registered. <a href='{url}'>Log in instead</a>."
    REGISTER_FIELDS_REQUIRED = "All fields are required."
    REGISTER_PASSWORD_TOO_SHORT = "Password must be at least 8 characters."
    
                          
    PET_FIELDS_REQUIRED = "Please fill in all required fields (name, species, age, weight) before saving."
    PET_INVALID_AGE = "Pet age must be a positive number."
    PET_INVALID_WEIGHT = "Pet weight must be a positive number."
    
                      
    BOOKING_SLOT_TAKEN = "Sorry, this time slot was just booked by another customer. Please select a different slot."
    BOOKING_PAST_DATE = "Cannot book appointments in the past."
    BOOKING_NO_PET = "Please add at least one pet to your profile before booking."
    BOOKING_FIELDS_REQUIRED = "Please select a pet, service, groomer, and time slot."
    
                          
    FILE_TOO_LARGE = "File must be under 5MB."
    FILE_INVALID_TYPE = "File must be a PDF, JPG, JPEG, or PNG."
    FILE_UPLOAD_FAILED = "File upload failed. Please try again."
    
                      
    UNAUTHORIZED = "You don't have permission to perform this action."
    SESSION_EXPIRED = "Your session has expired. Please log in again."
    SOMETHING_WENT_WRONG = "Something went wrong. Please try again."

def validate_file_upload(filename: str, file_size: int, 
                        allowed_extensions: set[str] = None,
                        max_size_mb: int = 5) -> str | None:
    if allowed_extensions is None:
        allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png'}
    
                     
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        return f"File must be under {max_size_mb}MB."
    
                          
    if '.' not in filename:
        return "Invalid file type."
    
    extension = filename.rsplit('.', 1)[1].lower()
    if extension not in allowed_extensions:
        allowed_str = ', '.join(allowed_extensions).upper()
        return f"File must be a {allowed_str}."
    
    return None
