from __future__ import annotations

from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, cast

from flask import flash, jsonify, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

import app.models as db
from app import ADD_ONS, SERVICE_DETAILS, SPECIES_OPTIONS
from app.utils.auth_helpers import current_user, login_required
from app.utils.formatters import format_slot, parse_date, safe_int, optional_text
from app.utils.sms import send_sms, booking_confirmation_message, status_message
from app.utils.warnings import WarningMessages, flash_warning, validate_file_upload
from app_types import UserRecord
from config import CONFIG

from app.owner import owner_bp

                                                                              
                  
                                                                              

def appointment_owner_record(appointment_id: int, owner_id: int) -> dict[str, Any] | None:
    return db.fetch_one(
        """
        SELECT a.*, p.name AS pet_name, u.name AS owner_name, u.phone AS owner_phone
        FROM appointments a
        JOIN pets p ON p.id = a.pet_id
        JOIN users u ON u.id = a.owner_id
        WHERE a.id = %s AND a.owner_id = %s
        """,
        (appointment_id, owner_id),
    )

def vaccination_link(record_url: str | None) -> str | None:
    if not record_url:
        return None
    return url_for("main.uploaded_file", filename=Path(record_url).name)

def quick_prompts_for_role(role: str) -> list[str]:
    from app import STAFF_QUICK_PROMPTS, OWNER_QUICK_PROMPTS
    return STAFF_QUICK_PROMPTS if role in {"admin", "groomer", "staff"} else OWNER_QUICK_PROMPTS

def get_chat_messages(scope: str) -> list[dict[str, str]]:
    from flask import session
    key = f"chat_{scope}"
    return session.get(key, [])

                                                                              
                         
                                                                              

@owner_bp.route("/")
@login_required("owner")
def owner_portal():
    user = cast(UserRecord, current_user())
    section = request.args.get("section", "dashboard")
    
                  
    pets = db.list_owner_pets(user["id"])
    pet_profiles = {pet["id"]: pet for pet in pets}
    
                          
    appointments = db.list_owner_appointments(user["id"])
    upcoming = [
        item for item in appointments 
        if item["slot_start"] >= datetime.now() and item["status"] in {"confirmed", "pending", "rescheduled"}
    ]
    past = [item for item in appointments if item not in upcoming]
    upcoming.sort(key=lambda item: item["slot_start"])
    
                                      
    upcoming = [dict(item, pet_profile=pet_profiles.get(item["pet_id"])) for item in upcoming]
    past = [dict(item, pet_profile=pet_profiles.get(item["pet_id"])) for item in past]
    
                          
    selected_date = parse_date(request.args.get("date"), date.today() + timedelta(days=1))
    groomers = db.list_groomers()
    selected_groomer_id = safe_int(request.args.get("groomer_id"), groomers[0]["id"] if groomers else None)
    selected_service = request.args.get("service") or next(iter(SERVICE_DETAILS), "")
    selected_pet_id = safe_int(request.args.get("pet_id"))
    
    slot_options = db.list_slots_for_day(selected_date, selected_groomer_id, available_only=False) if selected_groomer_id else []
    
                                                             
    if selected_groomer_id and not slot_options and selected_date >= date.today():
        db.create_time_slots(selected_groomer_id, selected_date, start_hour=9, end_hour=17, interval_minutes=60)
        slot_options = db.list_slots_for_day(selected_date, selected_groomer_id, available_only=False)
    
    available_slots = [slot for slot in slot_options if slot["status"] == "available"]
    next_appointment = upcoming[0] if upcoming else None
    selected_pet = next((pet for pet in pets if pet["id"] == selected_pet_id), None)
    
                                   
    pets_with_links = [dict(pet, vaccination_link=vaccination_link(pet.get("vaccination_records_url"))) for pet in pets]
    pet_profiles_with_links = {pet["id"]: pet for pet in pets_with_links}
    
                                                  
    upcoming = [dict(item, pet_profile=pet_profiles_with_links.get(item["pet_id"])) for item in upcoming]
    past = [dict(item, pet_profile=pet_profiles_with_links.get(item["pet_id"])) for item in past]
    next_appointment = upcoming[0] if upcoming else None
    selected_pet = next((pet for pet in pets_with_links if pet["id"] == selected_pet_id), None)
    
    return render_template(
        "owner.html",
        section=section,
        nav_items=[
            ("dashboard", "Dashboard", "🏠"),
            ("book", "Book Appointment", "📅"),
            ("pets", "My Pets", "🐾"),
            ("history", "Booking History", "📋"),
        ],
        pets=pets_with_links,
        appointments=appointments,
        upcoming=upcoming,
        past=past,
        next_appointment=next_appointment,
        completed_count=len([item for item in appointments if item["status"] == "completed"]),
        groomers=groomers,
        selected_groomer_id=selected_groomer_id,
        selected_date=selected_date,
        selected_service=selected_service,
        slot_options=slot_options,
        available_slots=available_slots,
        service_details=SERVICE_DETAILS,
        add_ons=ADD_ONS,
        species_options=SPECIES_OPTIONS,
        selected_pet=selected_pet,
        allergy_options=db.list_allergy_options(),
        medication_options=db.list_medication_options(),
        breeds_for_pet=db.list_breeds(selected_pet["species"]) if selected_pet else [],
        coat_type_options=["Short", "Medium", "Long", "Curly", "Wavy", "Double coat", "Hairless"],
        temperament_options=["Calm", "Friendly", "Playful", "Shy", "Anxious", "Aggressive", "Stubborn"],
        chat_messages=get_chat_messages("owner"),
        quick_prompts=quick_prompts_for_role("owner"),
    )

                                                                              
                       
                                                                              

@owner_bp.route("/pets/save", methods=["POST"])
@login_required("owner")
def save_owner_pet():
    user = cast(UserRecord, current_user())
    pet_id = safe_int(request.form.get("pet_id"))
    name = request.form.get("name", "").strip()
    species = request.form.get("species", "Dog")
    breed = request.form.get("breed", "").strip()
    age = safe_int(request.form.get("age"), 0) or 0
    weight = float(request.form.get("weight", 0) or 0)
    medical_history = request.form.get("medical_history", "").strip()
                                                                             
    allergy_list = request.form.getlist("allergies")
    allergy_other = request.form.get("allergies_other", "").strip()
    if allergy_other and "Other" in allergy_list:
        allergy_list = [a for a in allergy_list if a != "Other"] + [allergy_other]
    allergies = ", ".join(a for a in allergy_list if a and a != "None") or request.form.get("allergies", "").strip()
    medication_list = request.form.getlist("medications")
    medication_other = request.form.get("medications_other", "").strip()
    if medication_other and "Other" in medication_list:
        medication_list = [m for m in medication_list if m != "Other"] + [medication_other]
    medications = ", ".join(m for m in medication_list if m and m != "None") or request.form.get("medications", "").strip()
    temperament = optional_text(request.form.get("temperament"))
    
                           
    diet_stage = optional_text(request.form.get("diet_stage"))
    body_condition = optional_text(request.form.get("body_condition"))
    food_brand = optional_text(request.form.get("food_brand"))
    feeding_frequency = optional_text(request.form.get("feeding_frequency"))
    appetite_status = optional_text(request.form.get("appetite_status"))
    water_intake_status = optional_text(request.form.get("water_intake_status"))
    nutrition_notes = optional_text(request.form.get("nutrition_notes"))
    emotional_condition = optional_text(request.form.get("emotional_condition"))
    behavior_triggers = optional_text(request.form.get("behavior_triggers"))
    handling_notes = optional_text(request.form.get("handling_notes"))
    grooming_tolerance = optional_text(request.form.get("grooming_tolerance"))
    coat_type = optional_text(request.form.get("coat_type"))
    skin_condition = optional_text(request.form.get("skin_condition"))
    parasite_status = optional_text(request.form.get("parasite_status"))
    recommended_shampoo = optional_text(request.form.get("recommended_shampoo"))
    recommended_add_ons = optional_text(request.form.get("recommended_add_ons"))
    bath_tolerance = optional_text(request.form.get("bath_tolerance"))
    dryer_tolerance = optional_text(request.form.get("dryer_tolerance"))
    brushing_tolerance = optional_text(request.form.get("brushing_tolerance"))
    nail_trim_tolerance = optional_text(request.form.get("nail_trim_tolerance"))
    ear_cleaning_tolerance = optional_text(request.form.get("ear_cleaning_tolerance"))
    handling_readiness = optional_text(request.form.get("handling_readiness"))
    vaccine_expiry = request.form.get("vaccine_expiry", "").strip() or None
    upload: Any = request.files.get("vaccination_file")
                                                                            
    
                
    if not name or not breed:
        flash_warning(WarningMessages.PET_FIELDS_REQUIRED, "warning")
        return redirect(url_for("owner.owner_portal", section="pets", pet_id=pet_id))
    
    if age <= 0:
        flash_warning(WarningMessages.PET_INVALID_AGE, "warning")
        return redirect(url_for("owner.owner_portal", section="pets", pet_id=pet_id))
    
    if weight <= 0:
        flash_warning(WarningMessages.PET_INVALID_WEIGHT, "warning")
        return redirect(url_for("owner.owner_portal", section="pets", pet_id=pet_id))
    
                            
    if upload and upload.filename:
        upload.seek(0, 2)               
        file_size = upload.tell()
        upload.seek(0)                      
        
        validation_error = validate_file_upload(upload.filename, file_size)
        if validation_error:
            flash_warning(validation_error, "warning")
            return redirect(url_for("owner.owner_portal", section="pets", pet_id=pet_id))
    
    try:
        record_url = db.save_uploaded_file(upload) if upload and upload.filename else None
        saved_pet_id = db.upsert_pet(
            owner_id=user["id"],
            pet_id=pet_id,
            name=name,
            species=species,
            breed=breed,
            age=age,
            weight=weight,
            medical_history=medical_history,
            allergies=allergies,
            medications=medications,
            vaccination_records_url=record_url,
            vaccine_expiry=vaccine_expiry,
        )
        db.update_pet_recommendation_profile(
            saved_pet_id,
            {
                "diet_stage": diet_stage,
                "body_condition": body_condition,
                "food_brand": food_brand,
                "feeding_frequency": feeding_frequency,
                "appetite_status": appetite_status,
                "water_intake_status": water_intake_status,
                "nutrition_notes": nutrition_notes,
                "emotional_condition": emotional_condition,
                "behavior_triggers": behavior_triggers,
                "handling_notes": handling_notes,
                "grooming_tolerance": grooming_tolerance,
                "coat_type": coat_type,
                "skin_condition": skin_condition,
                "parasite_status": parasite_status,
                "recommended_shampoo": recommended_shampoo,
                "recommended_add_ons": recommended_add_ons,
                "bath_tolerance": bath_tolerance,
                "dryer_tolerance": dryer_tolerance,
                "brushing_tolerance": brushing_tolerance,
                "nail_trim_tolerance": nail_trim_tolerance,
                "ear_cleaning_tolerance": ear_cleaning_tolerance,
                "handling_readiness": handling_readiness,
                "temperament": temperament,
            },
        )
        
                            
        if body_condition:
            db.log_pet_nutrition(
                saved_pet_id,
                body_condition=body_condition,
                diet_stage=diet_stage,
                food_brand=food_brand,
                feeding_frequency=feeding_frequency,
                nutrition_notes=nutrition_notes,
                recorded_by_user_id=user["id"],
            )
        if emotional_condition:
            db.log_pet_behavior(
                saved_pet_id,
                emotional_condition=emotional_condition,
                recorded_by_user_id=user["id"],
                behavior_notes=handling_notes,
                handling_recommendation=behavior_triggers,
            )
        if coat_type and skin_condition and recommended_shampoo:
            db.log_pet_product_recommendation(
                saved_pet_id,
                coat_type=coat_type,
                skin_condition=skin_condition,
                parasite_status=parasite_status,
                recommended_shampoo=recommended_shampoo,
                recommended_add_ons=recommended_add_ons,
                recorded_by_user_id=user["id"],
            )
        if all([bath_tolerance, dryer_tolerance, brushing_tolerance, nail_trim_tolerance, ear_cleaning_tolerance, handling_readiness]):
            bath_tolerance_value = cast(str, bath_tolerance)
            dryer_tolerance_value = cast(str, dryer_tolerance)
            brushing_tolerance_value = cast(str, brushing_tolerance)
            nail_trim_tolerance_value = cast(str, nail_trim_tolerance)
            ear_cleaning_tolerance_value = cast(str, ear_cleaning_tolerance)
            handling_readiness_value = cast(str, handling_readiness)
            db.log_pet_handling_assessment(
                saved_pet_id,
                bath_tolerance=bath_tolerance_value,
                dryer_tolerance=dryer_tolerance_value,
                brushing_tolerance=brushing_tolerance_value,
                nail_trim_tolerance=nail_trim_tolerance_value,
                ear_cleaning_tolerance=ear_cleaning_tolerance_value,
                handling_readiness=handling_readiness_value,
                handling_notes=handling_notes,
                recorded_by_user_id=user["id"],
            )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("owner.owner_portal", section="pets", pet_id=pet_id))
    
    flash("Pet profile saved.", "success")
    return redirect(url_for("owner.owner_portal", section="pets"))

@owner_bp.route("/api/breeds")
@login_required("owner")
def api_breeds():
    species = request.args.get("species", "").strip()
    if not species:
        return jsonify({"breeds": []})
    breeds = db.list_breeds(species)
    return jsonify({"breeds": breeds})

@owner_bp.route("/api/owner/pets/add", methods=["POST"])
@login_required("owner")
def add_pet_api():
    user = cast(UserRecord, current_user())
    
    try:
                                      
        name = request.form.get("name", "").strip()
        species = request.form.get("species", "Dog").strip()
        breed = request.form.get("breed", "").strip()
        age = safe_int(request.form.get("age"), 0) or 0
        weight = float(request.form.get("weight", 0) or 0)
        
                                                          
        allergy_list = request.form.getlist("allergies")
        allergy_other = request.form.get("allergies_other", "").strip()
        if allergy_other and "Other" in allergy_list:
            allergy_list = [a for a in allergy_list if a != "Other"] + [allergy_other]
        allergies = ", ".join(a for a in allergy_list if a and a != "None") or request.form.get("allergies", "").strip()
        medication_list = request.form.getlist("medications")
        medication_other = request.form.get("medications_other", "").strip()
        if medication_other and "Other" in medication_list:
            medication_list = [m for m in medication_list if m != "Other"] + [medication_other]
        medications = ", ".join(m for m in medication_list if m and m != "None") or request.form.get("medications", "").strip()
        medical_history = request.form.get("medical_history", "").strip()
        
                             
        vaccine_expiry = request.form.get("vaccine_expiry", "").strip() or None
        upload: Any = request.files.get("vaccination_file")
        
                    
        if not name:
            return jsonify({"success": False, "error": "Pet name is required"}), 400
        if not breed:
            return jsonify({"success": False, "error": "Breed is required"}), 400
        if age < 0 or age > 30:
            return jsonify({"success": False, "error": "Age must be between 0 and 30 years"}), 400
        if weight <= 0:
            return jsonify({"success": False, "error": "Weight must be a positive number"}), 400
        
                         
        vaccination_url = None
        if upload and upload.filename:
            filename = upload.filename.lower()
            allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png'}
            file_ext = Path(filename).suffix
            
            if file_ext not in allowed_extensions:
                return jsonify({"success": False, "error": "Vaccine file must be PDF, JPEG, or PNG"}), 400
            
                                       
            upload.seek(0, 2)               
            file_size = upload.tell()
            upload.seek(0)                      
            
            if file_size > 5 * 1024 * 1024:       
                return jsonify({"success": False, "error": "Vaccine file must be under 5MB"}), 400
            
            vaccination_url = db.save_uploaded_file(upload)
        
                  
        pet_id = db.upsert_pet(
            owner_id=user["id"],
            name=name,
            species=species,
            breed=breed,
            age=age,
            weight=weight,
            medical_history=medical_history,
            allergies=allergies,
            medications=medications,
            vaccination_records_url=vaccination_url,
            vaccine_expiry=vaccine_expiry,
            pet_id=None,
        )
        
        import json as _json
        vaccines_raw = request.form.get("vaccines_json", "[]")
        try:
            vaccine_rows = _json.loads(vaccines_raw)
        except Exception:
            vaccine_rows = []
        for row in vaccine_rows:
            vname = (row.get("vaccine_name") or "").strip()
            if not vname:
                continue
            db.add_pet_vaccination(
                pet_id=pet_id,
                vaccine_name=vname,
                date_administered=row.get("date_administered") or None,
                next_due_date=row.get("next_due_date") or None,
                vet_name=(row.get("vet_name") or "").strip() or None,
                notes=(row.get("notes") or "").strip() or None,
                created_by=user["id"],
            )
        
                               
        pet = db.get_pet_by_id(pet_id)
        if not pet:
            return jsonify({"success": False, "error": "Failed to retrieve created pet"}), 500
        
        return jsonify({
            "success": True,
            "message": "Pet added successfully!",
            "pet": {
                "id": pet["id"],
                "name": pet["name"],
                "species": pet["species"],
                "breed": pet["breed"],
                "age": pet["age"],
                "weight": float(pet["weight"]),
            }
        }), 200
        
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@owner_bp.route("/api/owner/pets/<int:pet_id>/delete", methods=["POST"])
@login_required("owner")
def delete_pet_api(pet_id: int):
    user = cast(UserRecord, current_user())
    print(f"[DELETE] Request to delete pet ID {pet_id} by user {user['id']}")
    
    try:
                          
        pet = db.get_pet_by_id(pet_id)
        if not pet:
            print(f"[DELETE] Pet {pet_id} not found")
            return jsonify({"success": False, "error": "Pet not found"}), 404
        
        if pet["owner_id"] != user["id"]:
            print(f"[DELETE] Unauthorized: pet owner={pet['owner_id']}, user={user['id']}")
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        
                                       
        active_appointments = db.fetch_all(
            "SELECT id FROM appointments WHERE pet_id = %s AND status != 'completed' AND status != 'cancelled'",
            (pet_id,)
        )
        
        if active_appointments:
            print(f"[DELETE] Pet {pet_id} has {len(active_appointments)} active appointments")
            return jsonify({
                "success": False, 
                "error": f"Cannot delete {pet['name']}. Pet has active appointments. Please cancel or complete them first."
            }), 400
        
                                                          
        print(f"[DELETE] Deleting pet {pet_id}: {pet['name']}")
        db.execute("DELETE FROM pets WHERE id = %s AND owner_id = %s", (pet_id, user["id"]))
        print(f"[DELETE] Pet {pet_id} deleted successfully")
        
        return jsonify({
            "success": True,
            "message": f"{pet['name']} has been deleted successfully."
        }), 200
        
    except Exception as exc:
        print(f"[DELETE] Error deleting pet {pet_id}: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500

                                                                              
                                   
                                                                              

@owner_bp.route("/api/pet/<int:pet_id>/vaccinations", methods=["GET"])
@login_required()
def get_pet_vaccinations(pet_id: int):
    user = cast(UserRecord, current_user())
    
                                           
    pet = db.get_pet_by_id(pet_id)
    if not pet:
        return jsonify({"success": False, "error": "Pet not found"}), 404
    
    if user["role"] == "owner" and pet["owner_id"] != user["id"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    
    vaccinations = db.list_pet_vaccinations(pet_id)
    
                           
    for vax in vaccinations:
        if vax.get("date_administered"):
            vax["date_administered"] = vax["date_administered"].isoformat() if isinstance(vax["date_administered"], date) else vax["date_administered"]
        if vax.get("next_due_date"):
            vax["next_due_date"] = vax["next_due_date"].isoformat() if isinstance(vax["next_due_date"], date) else vax["next_due_date"]
    
    return jsonify({"success": True, "vaccinations": vaccinations}), 200

@owner_bp.route("/api/pet/<int:pet_id>/vaccinations/add", methods=["POST"])
@login_required()
def add_vaccination(pet_id: int):
    user = cast(UserRecord, current_user())
    
    if user["role"] == "owner":
        return jsonify({"success": False, "error": "Only staff or admin can add vaccination records after registration."}), 403
    
    pet = db.get_pet_by_id(pet_id)
    if not pet:
        return jsonify({"success": False, "error": "Pet not found"}), 404
    
    vaccine_name = request.form.get("vaccine_name", "").strip()
    date_administered = request.form.get("date_administered", "").strip() or None
    next_due_date = request.form.get("next_due_date", "").strip() or None
    vet_name = request.form.get("vet_name", "").strip() or None
    notes = request.form.get("notes", "").strip() or None
    
    if not vaccine_name:
        return jsonify({"success": False, "error": "Vaccine name is required"}), 400
    
    try:
        vax_id = db.add_pet_vaccination(
            pet_id=pet_id,
            vaccine_name=vaccine_name,
            date_administered=date_administered,
            next_due_date=next_due_date,
            vet_name=vet_name,
            notes=notes,
            created_by=user["id"],
        )
        return jsonify({"success": True, "message": "Vaccination added successfully", "id": vax_id}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@owner_bp.route("/api/pet/vaccinations/<int:vax_id>/update", methods=["POST"])
@login_required()
def update_vaccination(vax_id: int):
    user = cast(UserRecord, current_user())
    
    if user["role"] == "owner":
        return jsonify({"success": False, "error": "Only staff or admin can edit vaccination records."}), 403
    
    vaccination = db.get_vaccination_by_id(vax_id)
    if not vaccination:
        return jsonify({"success": False, "error": "Vaccination record not found"}), 404
    
    vaccine_name = request.form.get("vaccine_name", "").strip()
    date_administered = request.form.get("date_administered", "").strip() or None
    next_due_date = request.form.get("next_due_date", "").strip() or None
    vet_name = request.form.get("vet_name", "").strip() or None
    notes = request.form.get("notes", "").strip() or None
    
    if not vaccine_name:
        return jsonify({"success": False, "error": "Vaccine name is required"}), 400
    
    try:
        db.update_pet_vaccination(
            vaccination_id=vax_id,
            vaccine_name=vaccine_name,
            date_administered=date_administered,
            next_due_date=next_due_date,
            vet_name=vet_name,
            notes=notes,
        )
        return jsonify({"success": True, "message": "Vaccination updated successfully"}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@owner_bp.route("/api/pet/vaccinations/<int:vax_id>/delete", methods=["POST"])
@login_required()
def delete_vaccination(vax_id: int):
    user = cast(UserRecord, current_user())
    
    if user["role"] == "owner":
        return jsonify({"success": False, "error": "Only staff or admin can delete vaccination records."}), 403
    
    vaccination = db.get_vaccination_by_id(vax_id)
    if not vaccination:
        return jsonify({"success": False, "error": "Vaccination record not found"}), 404
    
    try:
        db.delete_pet_vaccination(vax_id)
        return jsonify({"success": True, "message": "Vaccination deleted successfully"}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@owner_bp.route("/pet/<int:pet_id>/vaccination-card/download")
@login_required()
def download_vaccination_card(pet_id: int):
    from datetime import datetime as dt
    
    user = cast(UserRecord, current_user())
    
                   
    pet = db.get_pet_by_id(pet_id)
    if not pet:
        flash("Pet not found", "error")
        return redirect(url_for("owner.owner_portal", section="pets"))
    
    if user["role"] == "owner" and pet["owner_id"] != user["id"]:
        flash("Unauthorized", "error")
        return redirect(url_for("owner.owner_portal", section="pets"))
    
                      
    vaccinations = db.list_pet_vaccinations(pet_id)
    
                        
    owner = db.get_user_by_id(pet["owner_id"])
    
                                               
    html_content = render_template(
        "_vaccination_card_pdf.html",
        pet=pet,
        owner=owner,
        vaccinations=vaccinations,
        generated_date=dt.now().strftime("%B %d, %Y"),
        today=dt.now().date(),
        city=CONFIG.city,
    )
    
    try:
                                                 
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
        
        font_config = FontConfiguration()
        pdf_bytes = HTML(string=html_content).write_pdf(
            font_config=font_config,
            stylesheets=[CSS(string="""
                @page { 
                    size: A4; 
                    margin: 1cm; 
                }
                body { 
                    font-family: 'Segoe UI', Arial, sans-serif; 
                }
            """)]
        )
        
                                                
        filename = f"VaccinationCard_{pet['name'].replace(' ', '_')}_{dt.now().strftime('%Y%m%d')}.pdf"
        
                       
        return send_file(
            BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )
        
    except (ImportError, OSError) as exc:
                                                                              
                                                                   
        if isinstance(exc, OSError):
            flash("PDF generation requires GTK3 libraries. Displaying printable version instead. Use Ctrl+P to save as PDF from your browser.", "info")
        else:
            flash("PDF generation library not installed. Displaying printable version instead. Use Ctrl+P to save as PDF from your browser.", "info")
        
                                                            
        print_ready_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Vaccination Card - {pet['name']}</title>
            <style>
                @media print {{
                    @page {{ size: A4; margin: 1cm; }}
                    body {{ font-family: 'Segoe UI', Arial, sans-serif; }}
                    .no-print {{ display: none !important; }}
                }}
                @media screen {{
                    body {{ max-width: 210mm; margin: 20px auto; padding: 20px; background: #f5f5f5; }}
                    .print-notice {{
                        background: #e3f2fd;
                        border-left: 4px solid #2196F3;
                        padding: 15px;
                        margin-bottom: 20px;
                        border-radius: 4px;
                    }}
                    .print-btn {{
                        background: #4CAF50;
                        color: white;
                        border: none;
                        padding: 12px 24px;
                        font-size: 16px;
                        border-radius: 4px;
                        cursor: pointer;
                        margin-top: 10px;
                    }}
                    .print-btn:hover {{ background: #45a049; }}
                }}
            </style>
        </head>
        <body>
            <div class="print-notice no-print">
                <h3>🖨️ Print to PDF</h3>
                <p>Press <strong>Ctrl+P</strong> (or Cmd+P on Mac) and select <strong>"Save as PDF"</strong> to download this vaccination card.</p>
                <button class="print-btn" onclick="window.print()">🖨️ Print Now</button>
            </div>
            {html_content}
            <script>
                // Optional: Auto-trigger print dialog after page loads
                // window.addEventListener('load', () => setTimeout(() => window.print(), 500));
            </script>
        </body>
        </html>
        """
        return print_ready_html, 200, {"Content-Type": "text/html; charset=utf-8"}
    
    except Exception as exc:
        flash(f"Error generating vaccination card: {str(exc)}", "error")
        return redirect(url_for("owner.owner_portal", section="pets"))

                                                                              
                           
                                                                              

@owner_bp.route("/bookings/create", methods=["POST"])
@login_required("owner")
def create_owner_booking():
    user = cast(UserRecord, current_user())
    pet_id = safe_int(request.form.get("pet_id"))
    groomer_id = safe_int(request.form.get("groomer_id"))
    slot_id = safe_int(request.form.get("slot_id"))
    service_name = request.form.get("service_name", "")
    add_ons = ", ".join(request.form.getlist("add_ons"))
    notes = request.form.get("notes", "").strip()
    booking_date = request.form.get("booking_date")
    
                                           
    if pet_id is None or groomer_id is None or slot_id is None or not service_name:
        flash_warning(WarningMessages.BOOKING_FIELDS_REQUIRED, "warning")
        return redirect(url_for("owner.owner_portal", section="book", date=booking_date, groomer_id=groomer_id, service=service_name))
    
    try:
        created = db.create_appointment(
            owner_id=user["id"],
            pet_id=pet_id,
            groomer_id=groomer_id,
            slot_id=slot_id,
            service_name=service_name,
            add_ons=add_ons,
            notes=notes,
        )
        if request.form.get("send_sms"):
            pet = db.get_pet_by_id(pet_id)
            message = booking_confirmation_message(
                owner_name=user["name"],
                pet_name=pet["name"] if pet else "your pet",
                service_name=service_name,
                slot_label=format_slot(created["slot_start"]),
            )
            result = send_sms(user["phone"], message)
            db.log_sms(user["id"], user["phone"], "booking_confirmation", message, result.mode, related_appointment_id=created["appointment_id"])
    except ValueError as exc:
        error_message = str(exc)
                                           
        if "already been booked" in error_message.lower():
            flash_warning(WarningMessages.BOOKING_SLOT_TAKEN, "warning")
        elif "does not belong to this user" in error_message.lower():
            flash_warning(WarningMessages.BOOKING_NO_PET, "warning")
        else:
            flash_warning(error_message, "warning")
        return redirect(url_for("owner.owner_portal", section="book", date=booking_date, groomer_id=groomer_id, service=service_name))
    
    flash("Booking created and sent for approval.", "success")
    return redirect(url_for("owner.owner_portal", section="history"))

@owner_bp.route("/appointments/<int:appointment_id>/cancel", methods=["POST"])
@login_required("owner")
def cancel_owner_booking(appointment_id: int):
    user = cast(UserRecord, current_user())
    appointment = appointment_owner_record(appointment_id, user["id"])
    if not appointment:
        flash("Appointment not found.", "error")
        return redirect(url_for("owner.owner_portal", section="history"))
    
    db.update_appointment_status(appointment_id, "cancelled")
    message = status_message(user["name"], appointment["pet_name"], "cancelled", format_slot(appointment["slot_start"]))
    result = send_sms(user["phone"], message)
    db.log_sms(user["id"], user["phone"], "status_update", message, result.mode, related_appointment_id=appointment_id)
    flash("Appointment cancelled.", "success")
    return redirect(url_for("owner.owner_portal", section="history"))

@owner_bp.route("/appointments/<int:appointment_id>/rate", methods=["POST"])
@login_required("owner")
def rate_owner_booking(appointment_id: int):
    user = cast(UserRecord, current_user())
    appointment = appointment_owner_record(appointment_id, user["id"])
    if not appointment:
        flash("Appointment not found.", "error")
        return redirect(url_for("owner.owner_portal", section="history"))
    
    rating = safe_int(request.form.get("rating"), 5) or 5
    db.rate_appointment(appointment_id, max(1, min(5, rating)))
    flash("Rating saved.", "success")
    return redirect(url_for("owner.owner_portal", section="history"))
