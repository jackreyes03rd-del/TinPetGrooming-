from __future__ import annotations

from flask import flash, redirect, render_template, request, session, url_for

from app.auth import auth_bp
from app.utils.auth_helpers import login_user, logout_user, role_home
from app.utils.warnings import (
    WarningMessages,
    check_rate_limit,
    clear_rate_limit,
    flash_warning,
    record_failed_attempt,
)
import app.models as db

                      
from app import STARTUP_ERROR

@auth_bp.route("/login", methods=["POST"])
def login():
    if STARTUP_ERROR:
        return render_template("error.html", error_message=STARTUP_ERROR), 500
    
                   
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    
                                        
    if not email or not password:
        flash_warning(WarningMessages.LOGIN_FIELDS_REQUIRED, "warning")
        return redirect(url_for("main.public_page", auth="login"))
    
                                                
    is_allowed, remaining_seconds = check_rate_limit("login")
    if not is_allowed:
        message = WarningMessages.LOGIN_TOO_MANY_ATTEMPTS.format(seconds=remaining_seconds)
        flash_warning(message, "warning")
        return redirect(url_for("main.public_page", auth="login"))
    
                            
    user = db.authenticate_user(email=email, password=password)
    
    if not user:
                               
        _attempts, is_locked = record_failed_attempt("login")
        
        if is_locked:
            message = WarningMessages.LOGIN_TOO_MANY_ATTEMPTS.format(seconds=30)
            flash_warning(message, "warning")
        else:
                                                       
            flash_warning(WarningMessages.LOGIN_INVALID, "warning")
        
        return redirect(url_for("main.public_page", auth="login", email=email))
    
                                             
    clear_rate_limit("login")
    login_user(user)
    session.setdefault("dark_mode", False)
    return redirect(role_home(user.get("role", "owner")))

@auth_bp.route("/register", methods=["POST"])
def register():
    if STARTUP_ERROR:
        return render_template("error.html", error_message=STARTUP_ERROR), 500
    
                   
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    password = request.form.get("password", "")
    
                                        
    if not all([name, email, phone, password]):
        flash_warning(WarningMessages.REGISTER_FIELDS_REQUIRED, "warning")
        return redirect(url_for("main.public_page", auth="register"))
    
                                       
    if len(password) < 8:
        flash_warning(WarningMessages.REGISTER_PASSWORD_TOO_SHORT, "warning")
        return redirect(url_for("main.public_page", auth="register"))
    
                            
    try:
        db.create_user(name=name, email=email, phone=phone, password=password, role="owner")
    except ValueError as exc:
                              
        error_message = str(exc)
        if "email already exists" in error_message.lower():
            login_url = url_for("main.public_page", auth="login")
            message = WarningMessages.REGISTER_EMAIL_EXISTS.format(url=login_url)
            flash_warning(message, "warning")
        else:
            flash_warning(error_message, "warning")
        return redirect(url_for("main.public_page", auth="register"))
    
             
    flash("Account created successfully! You can log in now.", "success")
    return redirect(url_for("main.public_page", auth="login"))

@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("main.public_page"))
