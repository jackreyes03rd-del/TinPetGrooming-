from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from datetime import datetime

import requests

import app.models as db
from config import CONFIG

@dataclass(slots=True)
class SmsResult:
    mode: str
    success: bool
    detail: str

def format_philippine_number(phone: str) -> str:
                                                
    cleaned = re.sub(r'[^0-9+]', '', phone.strip())
    
                              
    if cleaned.startswith('+63'):
        formatted = cleaned
    elif cleaned.startswith('63'):
        formatted = '+' + cleaned
    elif cleaned.startswith('0'):
        formatted = '+63' + cleaned[1:]
    else:
        formatted = '+63' + cleaned
    
                                                                              
    if not re.match(r'^\+639\d{9}$', formatted):
        raise ValueError(f"Invalid Philippine mobile number: {phone}. Expected format: +639XXXXXXXXX")
    
    return formatted

def send_sms(phone: str, message: str) -> SmsResult:
                                
    if not all([CONFIG.sms_username, CONFIG.sms_password]):
        print(f"[SMS] Not configured - would send: {phone} | {message}")
        return SmsResult(mode="not_configured", success=False, detail="SMS not configured. Set username and password in admin settings.")
    
    try:
                                                  
        try:
            formatted_phone = format_philippine_number(phone)
        except ValueError as e:
            return SmsResult(
                mode="sms",
                success=False,
                detail=str(e)
            )
        
                                             
        auth_string = f"{CONFIG.sms_username}:{CONFIG.sms_password}"
        auth_bytes = auth_string.encode('ascii')
        base64_auth = base64.b64encode(auth_bytes).decode('ascii')
        
                         
        url = f"{CONFIG.sms_api_url}/message"
        headers = {
            "Authorization": f"Basic {base64_auth}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "message": message,
            "phoneNumbers": [formatted_phone]
        }
        
                       
        print(f"[SMS] Sending to {formatted_phone} via {url}")
        print(f"[SMS] Payload: {payload}")
        
                      
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
                       
        print(f"[SMS] Response status: {response.status_code}")
        print(f"[SMS] Response body: {response.text[:500]}")
        
                                                    
        if response.status_code in [200, 201, 202]:
            try:
                data = response.json()
                message_id = data.get("id", "unknown")
                state = data.get("state", "unknown")
                
                                                                    
                if state.lower() in ["pending", "queued", "sent", "processed"]:
                    return SmsResult(
                        mode="sms",
                        success=True,
                        detail=f"SMS queued successfully (ID: {message_id}, State: {state})"
                    )
                else:
                    return SmsResult(
                        mode="sms",
                        success=True,
                        detail=f"SMS sent (ID: {message_id}, State: {state})"
                    )
            except Exception:
                return SmsResult(
                    mode="sms",
                    success=True,
                    detail=f"SMS accepted (Status: {response.status_code})"
                )
        elif response.status_code == 401:
            return SmsResult(
                mode="sms",
                success=False,
                detail="Authentication failed - check username and password in admin settings"
            )
        else:
            error_detail = response.text[:100]
            return SmsResult(
                mode="sms",
                success=False,
                detail=f"SMS error: {response.status_code} - {error_detail}"
            )
    
    except requests.exceptions.Timeout:
        return SmsResult(
            mode="sms",
            success=False,
            detail="SMS timeout - request took too long"
        )
    except requests.exceptions.RequestException as e:
        return SmsResult(
            mode="sms",
            success=False,
            detail=f"SMS connection error: {str(e)[:100]}"
        )
    except Exception as e:
        return SmsResult(
            mode="sms",
            success=False,
            detail=f"SMS unexpected error: {str(e)[:100]}"
        )

def booking_confirmation_message(owner_name: str, pet_name: str, service_name: str, slot_label: str) -> str:
    return (
        f"Hi {owner_name}, {pet_name}'s {service_name} booking is confirmed for {slot_label}. "
        f"Thank you for choosing Tin Pet Grooming."
    )

def reminder_message(owner_name: str, pet_name: str, slot_label: str) -> str:
    return f"Reminder for {owner_name}: {pet_name} is scheduled for grooming on {slot_label}."

def status_message(owner_name: str, pet_name: str, status: str, slot_label: str) -> str:
    return f"Hi {owner_name}, {pet_name}'s appointment on {slot_label} has been marked as {status}."

def promo_message(owner_name: str, offer_copy: str) -> str:
    return f"Hi {owner_name}, Tin Pet Grooming promo: {offer_copy}"

def process_due_reminders() -> int:
    sent_count = 0
    for item in db.list_due_reminders():
        message = reminder_message(
            item["owner_name"],
            item["pet_name"],
            datetime.strftime(item["slot_start"], "%b %d, %Y %I:%M %p"),
        )
        result = send_sms(item["owner_phone"], message)
        db.log_sms(
            user_id=item["owner_id"],
            phone=item["owner_phone"],
            message_type="reminder",
            message_body=message,
            provider_mode=result.mode,
            related_appointment_id=item["appointment_id"],
        )
        sent_count += 1
    return sent_count
