from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import base64
import pandas as pd
import requests
from flask import flash, jsonify, redirect, render_template, request, session, url_for

from app.admin import admin_bp
from app.utils.auth_helpers import current_user, login_required
from app.utils import charts, formatters
from app_types import UserRecord
import app.models as db
from config import CONFIG
from app.utils.sms import (
    booking_confirmation_message,
    promo_message,
    reminder_message,
    send_sms,
    status_message,
)
from app.chatbot.routes import get_chat_messages

                      
from app import STAFF_QUICK_PROMPTS, SERVICE_DETAILS

def quick_prompts_for_role(role: str) -> list[str]:
    return STAFF_QUICK_PROMPTS if role in {"admin", "groomer", "staff"} else []

@admin_bp.route("/admin")
@login_required("admin")
def admin_portal():
    user = cast(UserRecord, current_user())
    section = request.args.get("section", "dashboard")
    start_date = formatters.parse_date(request.args.get("start_date"), date.today() - timedelta(days=30))
    end_date = formatters.parse_date(request.args.get("end_date"), date.today() + timedelta(days=1))
    status_filter = request.args.get("status", "All")
    search = request.args.get("search", "").strip()
    groomers = db.list_groomers()
    selected_groomer_id = formatters.safe_int(request.args.get("groomer_id"), groomers[0]["id"] if groomers else None)
    slot_date = formatters.parse_date(request.args.get("slot_date"), date.today() + timedelta(days=1))
    metrics = db.get_dashboard_metrics()
    todays = db.list_all_appointments(date.today(), date.today())
    bookings = db.list_all_appointments(start_date, end_date)
    if status_filter != "All":
        bookings = [item for item in bookings if item["status"] == status_filter]
    analytics_data = db.get_analytics_data(start_date, end_date)
    ai_data = db.get_chatbot_keyword_analysis(start_date, end_date)
    peak_hour_rows: list[dict[str, Any]] = [
        {"hour_label": f"{item['hour_bucket']}:00", "total": item["total"]}
        for item in analytics_data["peak_hours"]
    ]
    satisfaction_rows: list[dict[str, Any]] = [
        {"day_label": item["day_label"], "avg": round(float(item["average_rating"]), 2)}
        for item in analytics_data["satisfaction"]
    ]
    slot_preview = db.list_slots_for_day(slot_date, selected_groomer_id) if selected_groomer_id else []
                                                             
    if selected_groomer_id and not slot_preview and slot_date >= date.today():
        db.create_time_slots(selected_groomer_id, slot_date, start_hour=9, end_hour=17, interval_minutes=60)
        slot_preview = db.list_slots_for_day(slot_date, selected_groomer_id)
    owners = db.fetch_all("SELECT id, name, phone FROM users WHERE role = 'owner' ORDER BY name")
    current_sms_config = {
        "username": CONFIG.sms_username,
        "password": CONFIG.sms_password,
    }
    
                           
    owner_list_data = None
    selected_owner_data = None
    owner_notes_data = []
    owner_appointments_data = []
    
    if section == "owners":
        owner_search = request.args.get("owner_search", "").strip()
        has_pets_filter = request.args.get("has_pets_filter", "all")
        page = formatters.safe_int(request.args.get("page"), 1) or 1
        per_page = 25
        offset = (page - 1) * per_page
        
        selected_owner_id = formatters.safe_int(request.args.get("owner_id"), None)
        
        if selected_owner_id:
            selected_owner_data = db.get_owner_with_pets(selected_owner_id)
            owner_notes_data = db.get_owner_notes(selected_owner_id)
            owner_appointments_data = db.get_owner_appointments(selected_owner_id)
        else:
            owner_list_data = db.list_all_owners(
                search_term=owner_search,
                has_pets_filter=has_pets_filter,
                limit=per_page,
                offset=offset
            )
    
    return render_template(
        "admin/admin.html",
        section=section,
        nav_items=[
            ("dashboard", "Dashboard", "📊"),
            ("approvals", "Approvals", "🔔"),
            ("staff", "Staff", "👥"),
            ("bookings", "Bookings", "📅"),
            ("health", "Health Records", "🏥"),
            ("owners", "Pet Owners", "👤"),
            ("slots", "Slot Management", "🕐"),
            ("analytics", "Analytics", "🤖"),
            ("sms", "SMS Campaigns", "📱"),
            ("settings", "Settings", "⚙️"),
        ],
        metrics=metrics,
        todays=todays,
        timeline_chart_html=charts.timeline_chart(todays),
        pending=db.list_pending_appointments(),
        groomers=groomers,
        bookings=bookings,
        status_filter=status_filter,
        start_date=start_date,
        end_date=end_date,
        records=db.search_pet_health_records(search),
        search=search,
        selected_groomer_id=selected_groomer_id,
        slot_date=slot_date,
        slot_preview=slot_preview,
        analytics_data=analytics_data,
        ai_data=ai_data,
        popular_services_chart=charts.bar_chart(analytics_data["popular_services"], "service_name", "total"),
        peak_hours_chart=charts.bar_chart(peak_hour_rows, "hour_label", "total"),
        busiest_days_chart=charts.bar_chart(analytics_data["busiest_days"], "day_name", "total", color_scale="Teal"),
        keyword_chart=charts.bar_chart(ai_data["keyword_counts"], "count", "keyword", color_scale="Teal", orientation="h"),
        topic_chart=charts.bar_chart(ai_data["topic_counts"], "count", "topic", color_scale="Oranges", orientation="h"),
        satisfaction_chart=charts.line_chart(satisfaction_rows, "day_label", "avg"),
        owners=owners,
        service_details=SERVICE_DETAILS,
        current_sms_config=current_sms_config,
        chat_messages=get_chat_messages("admin"),
        quick_prompts=quick_prompts_for_role(user.get("role", "admin")),
        owner_list_data=owner_list_data,
        selected_owner_data=selected_owner_data,
        owner_notes_data=owner_notes_data,
        owner_appointments_data=owner_appointments_data,
    )

@admin_bp.route("/admin/approvals/<int:appointment_id>/<action>", methods=["POST"])
@login_required("admin")
def manage_approval(appointment_id: int, action: str):
    pending_item = next(
        (item for item in db.list_pending_appointments() if item["id"] == appointment_id),
        None
    )
    if not pending_item:
        flash("Pending booking not found.", "error")
        return redirect(url_for("admin.admin_portal", section="approvals"))
    
    if action == "approve":
        db.approve_appointment(appointment_id)
        slot_text = formatters.format_slot(pending_item["slot_start"])
        message = f"Hi {pending_item['owner_name']}, your booking for {pending_item['pet_name']} ({pending_item['service_name']}) on {slot_text} has been confirmed."
        result = send_sms(pending_item.get("owner_phone", ""), message)
        if pending_item.get("owner_phone"):
            db.log_sms(None, pending_item["owner_phone"], "status_update", message, result.mode, related_appointment_id=appointment_id)
        flash("Booking approved.", "success")
    else:
        db.reject_appointment(appointment_id)
        flash("Booking rejected.", "info")
    
    return redirect(url_for("admin.admin_portal", section="approvals"))

@admin_bp.route("/admin/staff/create", methods=["POST"])
@login_required("admin")
def create_staff_member():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    password = request.form.get("password", "")
    bio = request.form.get("bio", "").strip()
    
    if not all([name, email, phone, password]):
        flash("All staff fields are required.", "error")
        return redirect(url_for("admin.admin_portal", section="staff"))
    
    try:
        user_id = db.create_user(name, email, phone, password, role="groomer")
        if bio:
            db.execute("UPDATE groomers SET bio = %s WHERE user_id = %s", (bio, user_id))
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin.admin_portal", section="staff"))
    
    flash("Staff account created.", "success")
    return redirect(url_for("admin.admin_portal", section="staff"))

@admin_bp.route("/admin/staff/<int:groomer_id>/remove", methods=["POST"])
@login_required("admin")
def remove_staff_member(groomer_id: int):
    db.execute(
        "DELETE FROM users WHERE id = (SELECT user_id FROM groomers WHERE id = %s)",
        (groomer_id,)
    )
    flash("Staff member removed.", "info")
    return redirect(url_for("admin.admin_portal", section="staff"))

@admin_bp.route("/admin/bookings/<int:appointment_id>/status", methods=["POST"])
@login_required("admin")
def update_admin_booking_status(appointment_id: int):
    appointment = db.fetch_one(
        """
        SELECT a.*, p.name AS pet_name, u.name AS owner_name, u.phone AS owner_phone
        FROM appointments a
        JOIN pets p ON p.id = a.pet_id
        JOIN users u ON u.id = a.owner_id
        WHERE a.id = %s
        """,
        (appointment_id,),
    )
    if not appointment:
        flash("Appointment not found.", "error")
        return redirect(url_for("admin.admin_portal", section="bookings"))
    
    status = request.form.get("status", appointment["status"])
    appointment_updates = {
        "behavior_alert": formatters.optional_text(request.form.get("behavior_alert")),
        "recommended_shampoo": formatters.optional_text(request.form.get("recommended_shampoo")),
        "handling_level": formatters.optional_text(request.form.get("handling_level")),
        "prep_notes": formatters.optional_text(request.form.get("prep_notes")),
        "nutrition_flag": formatters.optional_text(request.form.get("nutrition_flag")),
    }
    
    db.update_appointment_status(appointment_id, status)
    if any(value is not None for value in appointment_updates.values()):
        db.update_appointment_recommendations(appointment_id, appointment_updates)
    
    message = status_message(
        appointment["owner_name"],
        appointment["pet_name"],
        status,
        formatters.format_slot(appointment["slot_start"])
    )
    result = send_sms(appointment["owner_phone"], message)
    db.log_sms(
        appointment["owner_id"],
        appointment["owner_phone"],
        "status_update",
        message,
        result.mode,
        related_appointment_id=appointment_id
    )
    
    flash("Booking status updated.", "success")
    return redirect(url_for(
        "admin.admin_portal",
        section="bookings",
        start_date=request.form.get("start_date"),
        end_date=request.form.get("end_date"),
        status=request.form.get("status_filter", "All")
    ))

@admin_bp.route("/admin/bookings/<int:appointment_id>/reminder", methods=["POST"])
@login_required("admin")
def send_admin_booking_reminder(appointment_id: int):
    appointment = db.fetch_one(
        """
        SELECT a.*, p.name AS pet_name, u.name AS owner_name, u.phone AS owner_phone
        FROM appointments a
        JOIN pets p ON p.id = a.pet_id
        JOIN users u ON u.id = a.owner_id
        WHERE a.id = %s
        """,
        (appointment_id,),
    )
    if not appointment:
        flash("Appointment not found.", "error")
        return redirect(url_for("admin.admin_portal", section="bookings"))
    
    message = reminder_message(
        appointment["owner_name"],
        appointment["pet_name"],
        formatters.format_slot(appointment["slot_start"])
    )
    result = send_sms(appointment["owner_phone"], message)
    db.log_sms(
        appointment["owner_id"],
        appointment["owner_phone"],
        "reminder",
        message,
        result.mode,
        related_appointment_id=appointment_id
    )
    
    flash("Reminder sent.", "success")
    return redirect(url_for(
        "admin.admin_portal",
        section="bookings",
        start_date=request.form.get("start_date"),
        end_date=request.form.get("end_date"),
        status=request.form.get("status_filter", "All")
    ))

@admin_bp.route("/admin/slots/generate", methods=["POST"])
@login_required("admin")
def generate_slots():
    groomer_id = formatters.safe_int(request.form.get("groomer_id"))
    target_date = formatters.parse_date(request.form.get("slot_date"), date.today())
    start_hour = formatters.safe_int(request.form.get("start_hour"), 9) or 9
    end_hour = formatters.safe_int(request.form.get("end_hour"), 17) or 17
    interval = formatters.safe_int(request.form.get("interval"), 60) or 60
    
    if not groomer_id:
        flash("Select a groomer first.", "error")
        return redirect(url_for("admin.admin_portal", section="slots"))
    
    created = db.create_time_slots(groomer_id, target_date, start_hour, end_hour, interval)
    flash(f"Created {created} slot(s).", "success")
    return redirect(url_for(
        "admin.admin_portal",
        section="slots",
        groomer_id=groomer_id,
        slot_date=target_date.isoformat()
    ))

@admin_bp.route("/admin/sms/send", methods=["POST"])
@login_required("admin")
def send_sms_campaign():
    owner_ids = [formatters.safe_int(value) for value in request.form.getlist("owner_ids")]
    owner_ids = [value for value in owner_ids if value is not None]
    message = request.form.get("message", "").strip()
    
    if not owner_ids or not message:
        flash("Select at least one recipient and enter a message.", "error")
        return redirect(url_for("admin.admin_portal", section="sms"))
    
    targets = db.fetch_all(
        f"SELECT id, name, phone FROM users WHERE id IN ({', '.join(['%s'] * len(owner_ids))})",
        tuple(owner_ids),
    )
    
                                
    success_count = 0
    failed_count = 0
    errors: list[str] = []
    last_mode = "sms"
    
    for owner in targets:
        body = promo_message(owner["name"], message)
        result = send_sms(owner["phone"], body)
        db.log_sms(owner["id"], owner["phone"], "promotion", body, result.mode)
        last_mode = result.mode
        
        print(f"[SMS Campaign] To: {owner['phone']} ({owner['name']}) | Success: {result.success} | Mode: {result.mode} | Detail: {result.detail}")
        
        if result.success:
            success_count += 1
        else:
            failed_count += 1
            errors.append(f"{owner['name']} ({owner['phone']}): {result.detail}")
    
                           
    if failed_count == 0:
        flash(f"✅ Successfully sent {success_count} SMS message(s) via {last_mode.upper()}.", "success")
    elif success_count == 0:
        flash(f"❌ All {failed_count} SMS messages failed. Check console for details.", "error")
        for error_msg in errors[:3]:
            flash(error_msg, "warning")
    else:
        flash(f"⚠️ Sent {success_count} successfully, {failed_count} failed. Check console for details.", "warning")
        for error_msg in errors[:3]:
            flash(error_msg, "warning")
    
    return redirect(url_for("admin.admin_portal", section="sms"))

@admin_bp.route("/admin/sms/test", methods=["POST"])
@login_required("admin")
def send_test_sms_direct():
    phone = request.form.get("test_phone", "").strip()
    message = request.form.get("test_message", "").strip()
    
    if not phone or not message:
        flash("❌ Please enter both phone number and message.", "error")
        return redirect(url_for("admin.admin_portal", section="sms"))
    
                       
    print(f"\n{'='*80}")
    print(f"[TEST SMS] Starting test SMS send to {phone}")
    print(f"[TEST SMS] API URL: {CONFIG.sms_api_url}")
    print(f"[TEST SMS] Message: {message}")
    print(f"{'='*80}\n")
    
    result = send_sms(phone, message)
    
    print(f"\n{'='*80}")
    print(f"[TEST SMS] Result - Success: {result.success} | Mode: {result.mode} | Detail: {result.detail}")
    print(f"{'='*80}\n")
    
                            
    if result.success:
        flash(f"✅ Test SMS sent successfully!", "success")
        flash(f"📤 Provider: {result.mode.upper()}", "success")
        flash(f"📱 To: {phone}", "success")
        flash(f"📝 Detail: {result.detail}", "success")
    else:
        flash(f"❌ Test SMS failed to send.", "error")
        flash(f"📤 Provider: {result.mode.upper()}", "error")
        flash(f"📱 To: {phone}", "error")
        flash(f"🔍 Error: {result.detail}", "error")
        flash("💡 Check the terminal/console for detailed debugging logs.", "warning")
    
    return redirect(url_for("admin.admin_portal", section="sms"))

@admin_bp.route("/admin/settings/hours", methods=["POST"])
@login_required("admin")
def save_working_hours():
    open_hour = request.form.get("open_hour", "09")
    close_hour = request.form.get("close_hour", "17")
    flash(f"Hours saved: {open_hour}:00 to {close_hour}:00.", "success")
    return redirect(url_for("admin.admin_portal", section="settings"))

@admin_bp.route("/admin/settings/reseed", methods=["POST"])
@login_required("admin")
def reseed_demo_data():
    db.seed_demo_data()
    flash("Demo data re-seeded.", "success")
    return redirect(url_for("admin.admin_portal", section="settings"))

@admin_bp.route("/admin/settings/sms", methods=["POST"])
@login_required("admin")
def save_sms_config():
    sms_username = request.form.get("sms_username", "").strip()
    sms_password = request.form.get("sms_password", "").strip()
    
                            
    env_path = Path(__file__).parent.parent.parent / ".env"
    env_lines: list[str] = []
    
    if env_path.exists():
        with open(env_path, "r") as f:
            env_lines = f.readlines()
    
                                     
    updated_lines: list[str] = []
    keys_to_update: dict[str, str] = {
        "SMS_USERNAME": sms_username,
    }
    
                                      
    if sms_password:
        keys_to_update["SMS_PASSWORD"] = sms_password
    
    keys_found: set[str] = set()
    
    for line in env_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            updated_lines.append(line)
            continue
        
        if "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in keys_to_update:
                updated_lines.append(f"{key}={keys_to_update[key]}\n")
                keys_found.add(key)
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)
    
                          
    for key, value in keys_to_update.items():
        if key not in keys_found:
            updated_lines.append(f"{key}={value}\n")
    
                             
    with open(env_path, "w") as f:
        f.writelines(updated_lines)
    
                             
    CONFIG.sms_username = sms_username
    if sms_password:
        CONFIG.sms_password = sms_password
    
    flash("SMS configuration saved successfully. Restart the application for changes to take full effect.", "success")
    return redirect(url_for("admin.admin_portal", section="settings"))

@admin_bp.route("/admin/settings/sms/test", methods=["POST"])
@login_required("admin")
def test_sms_config():
    data = request.get_json()
    username = data.get("sms_username", "").strip()
    password = data.get("sms_password", "").strip()
    
    if not all([username, password]):
        return jsonify({"success": False, "message": "Please fill in both username and password."})
    
    try:
                                                    
        auth_string = f"{username}:{password}"
        auth_bytes = auth_string.encode('ascii')
        base64_auth = base64.b64encode(auth_bytes).decode('ascii')
        
                       
        test_url = f"{CONFIG.sms_api_url}/health"
        headers = {
            "Authorization": f"Basic {base64_auth}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(test_url, headers=headers, timeout=10)
        
                               
        if response.status_code in [200, 201, 404]:
            return jsonify({
                "success": True,
                "message": f"✅ Connection successful! Android SMS Gateway is reachable. Your phone should be connected with the app running."
            })
        elif response.status_code == 401:
            return jsonify({"success": False, "message": "❌ Authentication failed. Check your username and password."})
        else:
            return jsonify({"success": True, "message": f"⚠️ Server reachable (status {response.status_code}). Make sure the Android SMS Gateway app is running on your phone."})
    
    except requests.exceptions.Timeout:
        return jsonify({"success": False, "message": "❌ Connection timeout. Check your URL or make sure the Android SMS Gateway app is running."})
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"❌ Connection error: {str(e)[:100]}"})
    except Exception as e:
        return jsonify({"success": False, "message": f"❌ Unexpected error: {str(e)[:100]}"})

@admin_bp.route("/admin/owners/<int:owner_id>/edit", methods=["POST"])
@login_required("admin")
def admin_edit_owner(owner_id: int):
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    
    if not all([name, email, phone]):
        flash("All fields are required.", "error")
        return redirect(url_for("admin.admin_portal", section="owners"))
    
    try:
        db.update_owner_info(owner_id, name, email, phone)
        flash("Owner information updated.", "success")
    except Exception as exc:
        flash(f"Error updating owner: {str(exc)}", "error")
    
    return redirect(url_for("admin.admin_portal", section="owners", owner_id=owner_id))

@admin_bp.route("/admin/owners/<int:owner_id>/reset-password", methods=["POST"])
@login_required("admin")
def admin_reset_owner_password(owner_id: int):
    import secrets
    temp_password = secrets.token_urlsafe(12)[:12]
    
    try:
        db.reset_owner_password(owner_id, temp_password)
        flash(f"Password reset successful. Temporary password: {temp_password}", "success")
        flash("NOTE: In production, this should be sent via email instead of displayed.", "warning")
    except Exception as exc:
        flash(f"Error resetting password: {str(exc)}", "error")
    
    return redirect(url_for("admin.admin_portal", section="owners", owner_id=owner_id))

@admin_bp.route("/owners/<int:owner_id>/add-note", methods=["POST"])
@login_required("admin", "groomer", "staff")
def add_owner_note(owner_id: int):
    user = cast(UserRecord, current_user())
    note = request.form.get("note", "").strip()
    
    if not note:
        flash("Note cannot be empty.", "error")
    else:
        try:
            db.add_owner_note(owner_id, user["id"], note)
            flash("Note added successfully.", "success")
        except Exception as exc:
            flash(f"Error adding note: {str(exc)}", "error")
    
                                 
    if user.get("role") == "admin":
        return redirect(url_for("admin.admin_portal", section="owners", owner_id=owner_id))
    else:
        return redirect(url_for("staff.staff_portal", section="owners", owner_id=owner_id))
