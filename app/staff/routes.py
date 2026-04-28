from __future__ import annotations

from datetime import date
from typing import Any, cast

from flask import flash, redirect, render_template, request, url_for

from app.staff import staff_bp
from app.utils.auth_helpers import current_user
from app.utils import formatters, login_required
from app_types import UserRecord
import app.models as db
from app.utils.sms import send_sms, status_message
from app.chatbot.routes import get_chat_messages

                      
from app import SERVICE_DETAILS, STAFF_QUICK_PROMPTS

def appointment_staff_record(appointment_id: int, user_id: int) -> dict[str, Any] | None:
    return db.fetch_one(
        """
        SELECT a.*, p.name AS pet_name, p.species, u.name AS owner_name, u.phone AS owner_phone
        FROM appointments a
        JOIN pets p ON p.id = a.pet_id
        JOIN users u ON u.id = a.owner_id
        JOIN groomers g ON g.id = a.groomer_id
        WHERE a.id = %s AND g.user_id = %s
        """,
        (appointment_id, user_id),
    )

def quick_prompts_for_role(role: str) -> list[str]:
    return STAFF_QUICK_PROMPTS if role in {"admin", "groomer", "staff"} else []

@staff_bp.route("/staff")
@login_required("groomer", "staff")
def staff_portal():
    user = cast(UserRecord, current_user())
    section = request.args.get("section", "dashboard")
    search = request.args.get("search", "").strip()
    
    today_schedule = db.list_schedule_for_groomer_user(user["id"], date.today())
    owners = db.fetch_all("SELECT id, name, email, phone FROM users WHERE role = 'owner' ORDER BY name")
    selected_owner_id = formatters.safe_int(request.args.get("owner_id"), owners[0]["id"] if owners else None)
    owner_pets = db.list_owner_pets(selected_owner_id) if selected_owner_id else []
    
    quick_book_date = formatters.parse_date(request.args.get("quick_date"), date.today())
    groomer_profile = user.get("groomer_profile") or {}
    quick_slots = db.list_slots_for_day(
        quick_book_date,
        groomer_profile.get("id"),
        available_only=True
    ) if groomer_profile.get("id") else []
    
    records = db.search_pet_health_records(search)
    
                           
    owner_list_data = None
    selected_owner_data_full = None
    owner_notes_data = []
    owner_appointments_data = []
    
    if section == "owners":
                                          
        owner_search = request.args.get("owner_search", "").strip()
        has_pets_filter = request.args.get("has_pets_filter", "all")
        page = formatters.safe_int(request.args.get("page"), 1) or 1
        per_page = 25
        offset = (page - 1) * per_page
        
                                         
        selected_owner_id_full = formatters.safe_int(request.args.get("owner_id"), None)
        
        if selected_owner_id_full:
                                        
            selected_owner_data_full = db.get_owner_with_pets(selected_owner_id_full)
            owner_notes_data = db.get_owner_notes(selected_owner_id_full)
            owner_appointments_data = db.get_owner_appointments(selected_owner_id_full)
        else:
                                    
            owner_list_data = db.list_all_owners(
                search_term=owner_search,
                has_pets_filter=has_pets_filter,
                limit=per_page,
                offset=offset
            )
    
    return render_template(
        "staff/staff.html",
        section=section,
        nav_items=[
            ("dashboard", "Today's Schedule", "📅"),
            ("health", "Pet Health Records", "🏥"),
            ("owners", "Pet Owners", "👤")
        ],
        today_schedule=today_schedule,
        confirmed_today=len([item for item in today_schedule if item["status"] == "confirmed"]),
        completed_today=len([item for item in today_schedule if item["status"] == "completed"]),
        owners=owners,
        selected_owner_id=selected_owner_id,
        owner_pets=owner_pets,
        quick_book_date=quick_book_date,
        quick_slots=quick_slots,
        service_details=SERVICE_DETAILS,
        records=records,
        search=search,
        chat_messages=get_chat_messages("staff"),
        quick_prompts=quick_prompts_for_role(user.get("role", "groomer")),
                               
        owner_list_data=owner_list_data,
        selected_owner_data=selected_owner_data_full,
        owner_notes_data=owner_notes_data,
        owner_appointments_data=owner_appointments_data,
    )

@staff_bp.route("/staff/appointments/<int:appointment_id>/status", methods=["POST"])
@login_required("groomer", "staff")
def update_staff_status(appointment_id: int):
    user = cast(UserRecord, current_user())
    status = request.form.get("status", "confirmed")
    
    appointment = appointment_staff_record(appointment_id, user["id"])
    if not appointment:
        flash("Appointment not found.", "error")
        return redirect(url_for("staff.staff_portal", section="dashboard"))
    
    db.update_appointment_status(appointment_id, status)
    
                           
    if appointment.get("owner_phone"):
        message = status_message(
            appointment["owner_name"],
            appointment["pet_name"],
            status,
            formatters.format_slot(appointment["slot_start"])
        )
        result = send_sms(appointment["owner_phone"], message)
        db.log_sms(
            None,
            appointment["owner_phone"],
            "status_update",
            message,
            result.mode,
            related_appointment_id=appointment_id
        )
    
    flash(f"Appointment marked as {status}.", "success")
    return redirect(url_for("staff.staff_portal", section="dashboard"))

@staff_bp.route("/staff/appointments/<int:appointment_id>/note", methods=["POST"])
@login_required("groomer", "staff")
def save_staff_note(appointment_id: int):
    user = cast(UserRecord, current_user())
    
    appointment = appointment_staff_record(appointment_id, user["id"])
    if not appointment:
        flash("Appointment not found.", "error")
        return redirect(url_for("staff.staff_portal", section="dashboard"))
    
                   
    note = request.form.get("note", "").strip()
    emotional_condition = formatters.optional_text(request.form.get("emotional_condition"))
    behavior_alert = formatters.optional_text(request.form.get("behavior_alert"))
    recommended_shampoo = formatters.optional_text(request.form.get("recommended_shampoo"))
    handling_level = formatters.optional_text(request.form.get("handling_level"))
    prep_notes = formatters.optional_text(request.form.get("prep_notes"))
    coat_type = formatters.optional_text(request.form.get("coat_type"))
    skin_condition = formatters.optional_text(request.form.get("skin_condition"))
    parasite_status = formatters.optional_text(request.form.get("parasite_status"))
    bath_tolerance = formatters.optional_text(request.form.get("bath_tolerance"))
    dryer_tolerance = formatters.optional_text(request.form.get("dryer_tolerance"))
    brushing_tolerance = formatters.optional_text(request.form.get("brushing_tolerance"))
    nail_trim_tolerance = formatters.optional_text(request.form.get("nail_trim_tolerance"))
    ear_cleaning_tolerance = formatters.optional_text(request.form.get("ear_cleaning_tolerance"))
    handling_readiness = formatters.optional_text(request.form.get("handling_readiness"))
    trigger_noise = formatters.is_checked(request.form.get("trigger_noise"))
    trigger_touch = formatters.is_checked(request.form.get("trigger_touch"))
    trigger_dryer = formatters.is_checked(request.form.get("trigger_dryer"))
    trigger_nail_trim = formatters.is_checked(request.form.get("trigger_nail_trim"))
    trigger_ear_cleaning = formatters.is_checked(request.form.get("trigger_ear_cleaning"))
    
                             
    db.execute("UPDATE appointments SET notes = %s WHERE id = %s", (note, appointment_id))
    
                                        
    appointment_updates = {
        "behavior_alert": behavior_alert,
        "recommended_shampoo": recommended_shampoo,
        "handling_level": handling_level,
        "prep_notes": prep_notes,
    }
    if any(value is not None for value in appointment_updates.values()):
        db.update_appointment_recommendations(appointment_id, appointment_updates)
    
                        
    pet_profile_updates: dict[str, Any] = {}
    if emotional_condition is not None:
        pet_profile_updates["emotional_condition"] = emotional_condition
    if recommended_shampoo is not None:
        pet_profile_updates["recommended_shampoo"] = recommended_shampoo
    if handling_readiness is not None:
        pet_profile_updates["handling_readiness"] = handling_readiness
    if coat_type is not None:
        pet_profile_updates["coat_type"] = coat_type
    if skin_condition is not None:
        pet_profile_updates["skin_condition"] = skin_condition
    if parasite_status is not None:
        pet_profile_updates["parasite_status"] = parasite_status
    if bath_tolerance is not None:
        pet_profile_updates["bath_tolerance"] = bath_tolerance
    if dryer_tolerance is not None:
        pet_profile_updates["dryer_tolerance"] = dryer_tolerance
    if brushing_tolerance is not None:
        pet_profile_updates["brushing_tolerance"] = brushing_tolerance
    if nail_trim_tolerance is not None:
        pet_profile_updates["nail_trim_tolerance"] = nail_trim_tolerance
    if ear_cleaning_tolerance is not None:
        pet_profile_updates["ear_cleaning_tolerance"] = ear_cleaning_tolerance
    
    if pet_profile_updates:
        db.update_pet_recommendation_profile(appointment["pet_id"], pet_profile_updates)
    
                      
    if emotional_condition:
        db.log_pet_behavior(
            appointment["pet_id"],
            emotional_condition=emotional_condition,
            appointment_id=appointment_id,
            recorded_by_user_id=user["id"],
            trigger_noise=trigger_noise,
            trigger_touch=trigger_touch,
            trigger_dryer=trigger_dryer,
            trigger_nail_trim=trigger_nail_trim,
            trigger_ear_cleaning=trigger_ear_cleaning,
            handling_recommendation=handling_level,
            behavior_notes=note or prep_notes,
        )
    
                                
    if coat_type and skin_condition and recommended_shampoo:
        db.log_pet_product_recommendation(
            appointment["pet_id"],
            appointment_id=appointment_id,
            recorded_by_user_id=user["id"],
            coat_type=coat_type,
            skin_condition=skin_condition,
            parasite_status=parasite_status,
            recommended_shampoo=recommended_shampoo,
            recommendation_reason=prep_notes,
        )
    
                             
    if all([
        bath_tolerance,
        dryer_tolerance,
        brushing_tolerance,
        nail_trim_tolerance,
        ear_cleaning_tolerance,
        handling_readiness
    ]):
        bath_tolerance_value = cast(str, bath_tolerance)
        dryer_tolerance_value = cast(str, dryer_tolerance)
        brushing_tolerance_value = cast(str, brushing_tolerance)
        nail_trim_tolerance_value = cast(str, nail_trim_tolerance)
        ear_cleaning_tolerance_value = cast(str, ear_cleaning_tolerance)
        handling_readiness_value = cast(str, handling_readiness)
        
        db.log_pet_handling_assessment(
            appointment["pet_id"],
            appointment_id=appointment_id,
            recorded_by_user_id=user["id"],
            bath_tolerance=bath_tolerance_value,
            dryer_tolerance=dryer_tolerance_value,
            brushing_tolerance=brushing_tolerance_value,
            nail_trim_tolerance=nail_trim_tolerance_value,
            ear_cleaning_tolerance=ear_cleaning_tolerance_value,
            handling_readiness=handling_readiness_value,
            handling_notes=prep_notes,
        )
    
    flash("Note saved.", "success")
    return redirect(url_for("staff.staff_portal", section="dashboard"))

@staff_bp.route("/staff/walkin", methods=["POST"])
@login_required("groomer", "staff")
def create_walkin_booking():
    user = cast(UserRecord, current_user())
    
    owner_id = formatters.safe_int(request.form.get("owner_id"))
    pet_id = formatters.safe_int(request.form.get("pet_id"))
    slot_id = formatters.safe_int(request.form.get("slot_id"))
    service_name = request.form.get("service_name", "")
    notes = request.form.get("notes", "").strip() or "Walk-in booking"
    
    groomer_profile = user.get("groomer_profile") or {}
    groomer_id = groomer_profile.get("id")
    
    if owner_id is None or pet_id is None or slot_id is None or groomer_id is None or not service_name:
        flash("Complete the quick booking form.", "error")
        return redirect(url_for(
            "staff.staff_portal",
            section="dashboard",
            owner_id=owner_id,
            quick_date=request.form.get("quick_date")
        ))
    
    try:
        db.create_appointment(
            owner_id=owner_id,
            pet_id=pet_id,
            groomer_id=groomer_id,
            slot_id=slot_id,
            service_name=service_name,
            add_ons="",
            notes=notes,
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for(
            "staff.staff_portal",
            section="dashboard",
            owner_id=owner_id,
            quick_date=request.form.get("quick_date")
        ))
    
    flash("Walk-in booking created.", "success")
    return redirect(url_for("staff.staff_portal", section="dashboard"))
