from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import Flask, g, session
from mysql.connector import Error

import app.models as db
from app_types import UserRecord
from config import CONFIG
from app.utils.sms import process_due_reminders

                       
CHAT_SEED = [{"role": "assistant", "content": "Ask me anything about pet care, grooming, or bookings."}]
OWNER_QUICK_PROMPTS = [
    "How often should I groom my dog?",
    "My cat hates baths - any tips?",
    "Best haircut for a Shih Tzu?",
    "What add-ons do you recommend?",
]
STAFF_QUICK_PROMPTS = [
    "How to handle an anxious dog?",
    "Signs of skin infection to watch for?",
    "De-shedding best practices?",
    "When to stop a groom for safety?",
]
SERVICE_DETAILS: dict[str, dict[str, str]] = {
    "Bath & Blow Dry": {"duration": "60 min", "price": "PHP 450", "desc": "Full bath, blow dry, brush-out"},
    "Full Groom": {"duration": "90 min", "price": "PHP 850", "desc": "Bath, haircut, nail trim, ear clean"},
    "Breed Styling": {"duration": "120 min", "price": "PHP 1,100", "desc": "Breed-specific scissor finish"},
    "Nail Trim": {"duration": "30 min", "price": "PHP 180", "desc": "Clip and file, no bath required"},
    "De-shedding": {"duration": "60 min", "price": "PHP 520", "desc": "Loose coat removal treatment"},
    "Sanitary Trim": {"duration": "45 min", "price": "PHP 300", "desc": "Comfort and hygiene-focused trim"},
}
ADD_ONS = ["Teeth cleaning", "Ear cleaning", "Paw balm", "Cologne", "Tick & flea wash", "Blueberry facial"]
SPECIES_OPTIONS = ["Dog", "Cat", "Rabbit", "Bird", "Hamster", "Fish", "Reptile", "Other"]
PUBLIC_SERVICES = [
    {"title": "Bath & Blow Dry", "body": "Full bath + blow dry + brush-out", "value": "PHP 450", "footer": "60 min", "icon": "🛁"},
    {"title": "Full Groom", "body": "Bath, haircut, nail trim, ear clean", "value": "PHP 850", "footer": "90 min", "icon": "✂️"},
    {"title": "Breed Styling", "body": "Breed-specific scissor finish", "value": "PHP 1,100", "footer": "120 min", "icon": "✨"},
    {"title": "Nail Trim", "body": "Clip and file, no bath required", "value": "PHP 180", "footer": "30 min", "icon": "🐾"},
    {"title": "De-shedding", "body": "Loose coat removal treatment", "value": "PHP 520", "footer": "60 min", "icon": "🪮"},
    {"title": "Sanitary Trim", "body": "Comfort and hygiene-focused trim", "value": "PHP 300", "footer": "45 min", "icon": "🧼"},
]

                    
STARTUP_ERROR: str | None = None

def _initialize_application() -> str | None:
    try:
        db.init_db()
        if CONFIG.demo_mode:
            db.seed_demo_data()
        process_due_reminders()
    except Error as exc:
        return str(exc)
    return None

def create_app() -> Flask:
    global STARTUP_ERROR
    
    app = Flask(__name__)
    app.config["SECRET_KEY"] = CONFIG.secret_key
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024                   
    
                                                             
    STARTUP_ERROR = _initialize_application()
    
                         
    from app.main import main_bp
    from app.auth import auth_bp
    from app.owner import owner_bp
    from app.staff import staff_bp
    from app.admin import admin_bp
    from app.chatbot import chatbot_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(owner_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(chatbot_bp)
    
                            
    @app.before_request
    def load_user() -> None:
        from app.utils.auth_helpers import SESSION_USER_KEY
        
        g.user = None
        user_id = session.get(SESSION_USER_KEY)
        if user_id:
            user = db.get_user_by_id(int(user_id))
            if user:
                g.user = user
            else:
                session.pop(SESSION_USER_KEY, None)
    
    @app.context_processor
    def inject_globals() -> dict[str, Any]:
        from app.utils.auth_helpers import current_user
        from app.utils.formatters import format_slot
        
        user = current_user()
        return {
            "app_name": CONFIG.app_name,
            "city": CONFIG.city,
            "current_user": user,
            "dark_mode": bool(session.get("dark_mode", False)),
            "pending_approvals": len(db.list_pending_appointments()) if user and user.get("role") == "admin" else 0,
            "now_year": datetime.now().year,
            "format_slot": format_slot,
        }
    
    return app
