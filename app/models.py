from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import mysql.connector
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash

from app_types import UserRecord
from config import CONFIG, UPLOAD_DIR

DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(120) NOT NULL,
        email VARCHAR(180) NOT NULL UNIQUE,
        phone VARCHAR(40) NOT NULL,
        role VARCHAR(20) NOT NULL DEFAULT 'owner',
        hashed_password VARCHAR(255) NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS groomers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        bio TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pets (
        id INT AUTO_INCREMENT PRIMARY KEY,
        owner_id INT NOT NULL,
        name VARCHAR(120) NOT NULL,
        species VARCHAR(80) NOT NULL,
        breed VARCHAR(120) NOT NULL,
        age INT NOT NULL,
        weight DECIMAL(7,2) NOT NULL,
        vaccination_records_url TEXT,
        vaccine_expiry DATE,
        medical_history TEXT,
        allergies TEXT,
        medications TEXT,
        diet_stage VARCHAR(30),
        body_condition VARCHAR(30),
        food_brand VARCHAR(120),
        feeding_frequency VARCHAR(60),
        appetite_status VARCHAR(40),
        water_intake_status VARCHAR(40),
        nutrition_notes TEXT,
        emotional_condition VARCHAR(30),
        behavior_triggers TEXT,
        handling_notes TEXT,
        grooming_tolerance VARCHAR(30),
        coat_type VARCHAR(40),
        skin_condition VARCHAR(40),
        parasite_status VARCHAR(30),
        recommended_shampoo VARCHAR(120),
        recommended_add_ons TEXT,
        bath_tolerance VARCHAR(20),
        dryer_tolerance VARCHAR(20),
        brushing_tolerance VARCHAR(20),
        nail_trim_tolerance VARCHAR(20),
        ear_cleaning_tolerance VARCHAR(20),
        handling_readiness VARCHAR(20),
        temperament VARCHAR(40),
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS breeds (
        id INT AUTO_INCREMENT PRIMARY KEY,
        species VARCHAR(20) NOT NULL,
        breed_name VARCHAR(80) NOT NULL,
        UNIQUE KEY uq_species_breed (species, breed_name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS allergy_options (
        id INT AUTO_INCREMENT PRIMARY KEY,
        allergy_name VARCHAR(50) NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS medication_options (
        id INT AUTO_INCREMENT PRIMARY KEY,
        medication_name VARCHAR(50) NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS product_categories (
        id INT AUTO_INCREMENT PRIMARY KEY,
        category_name VARCHAR(50) NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS shampoo_types (
        id INT AUTO_INCREMENT PRIMARY KEY,
        type_name VARCHAR(80) NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS nutrition_flags (
        id INT AUTO_INCREMENT PRIMARY KEY,
        flag_name VARCHAR(80) NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS behavioral_alerts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        alert_name VARCHAR(80) NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pet_vaccinations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pet_id INT NOT NULL,
        vaccine_name VARCHAR(100) NOT NULL,
        date_administered DATE,
        next_due_date DATE,
        vet_name VARCHAR(100),
        notes TEXT,
        created_by INT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE,
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS time_slots (
        id INT AUTO_INCREMENT PRIMARY KEY,
        groomer_id INT NOT NULL,
        slot_start DATETIME NOT NULL,
        slot_end DATETIME NOT NULL,
        status VARCHAR(30) NOT NULL DEFAULT 'available',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY unique_slot (groomer_id, slot_start, slot_end),
        FOREIGN KEY (groomer_id) REFERENCES groomers(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS appointments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pet_id INT NOT NULL,
        owner_id INT NOT NULL,
        groomer_id INT NOT NULL,
        slot_id INT NOT NULL,
        service_name VARCHAR(120) NOT NULL,
        add_ons TEXT,
        notes TEXT,
        slot_start DATETIME NOT NULL,
        slot_end DATETIME NOT NULL,
        status VARCHAR(30) NOT NULL DEFAULT 'confirmed',
        rating INT,
        behavior_alert VARCHAR(120),
        recommended_shampoo VARCHAR(120),
        handling_level VARCHAR(20),
        prep_notes TEXT,
        nutrition_flag VARCHAR(80),
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE,
        FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (groomer_id) REFERENCES groomers(id) ON DELETE CASCADE,
        FOREIGN KEY (slot_id) REFERENCES time_slots(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        question TEXT NOT NULL,
        answer LONGTEXT NOT NULL,
        topic VARCHAR(120) NOT NULL,
        timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sms_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        phone VARCHAR(40) NOT NULL,
        message_type VARCHAR(60) NOT NULL,
        message_body TEXT NOT NULL,
        related_appointment_id INT,
        provider_mode VARCHAR(30) NOT NULL,
        delivery_status VARCHAR(30) NOT NULL DEFAULT 'sent',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
        FOREIGN KEY (related_appointment_id) REFERENCES appointments(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics_cache (
        id INT AUTO_INCREMENT PRIMARY KEY,
        cache_key VARCHAR(120) NOT NULL UNIQUE,
        payload_json LONGTEXT NOT NULL,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pet_nutrition_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pet_id INT NOT NULL,
        recorded_by_user_id INT,
        body_condition VARCHAR(30) NOT NULL,
        diet_stage VARCHAR(30),
        food_brand VARCHAR(120),
        feeding_frequency VARCHAR(60),
        coat_support_goal VARCHAR(80),
        recommended_food_type VARCHAR(120),
        nutrition_notes TEXT,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE,
        FOREIGN KEY (recorded_by_user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pet_behavior_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pet_id INT NOT NULL,
        appointment_id INT,
        recorded_by_user_id INT,
        emotional_condition VARCHAR(30) NOT NULL,
        trigger_noise BOOLEAN NOT NULL DEFAULT 0,
        trigger_touch BOOLEAN NOT NULL DEFAULT 0,
        trigger_dryer BOOLEAN NOT NULL DEFAULT 0,
        trigger_nail_trim BOOLEAN NOT NULL DEFAULT 0,
        trigger_ear_cleaning BOOLEAN NOT NULL DEFAULT 0,
        aggression_risk VARCHAR(20),
        handling_recommendation TEXT,
        behavior_notes TEXT,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE,
        FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE SET NULL,
        FOREIGN KEY (recorded_by_user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pet_product_recommendations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pet_id INT NOT NULL,
        appointment_id INT,
        recorded_by_user_id INT,
        coat_type VARCHAR(40) NOT NULL,
        skin_condition VARCHAR(40) NOT NULL,
        parasite_status VARCHAR(30),
        recommended_shampoo VARCHAR(120) NOT NULL,
        recommended_conditioner VARCHAR(120),
        recommended_add_ons TEXT,
        avoid_ingredients TEXT,
        recommendation_reason TEXT,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE,
        FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE SET NULL,
        FOREIGN KEY (recorded_by_user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pet_handling_assessments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pet_id INT NOT NULL,
        appointment_id INT,
        recorded_by_user_id INT,
        bath_tolerance VARCHAR(20) NOT NULL,
        dryer_tolerance VARCHAR(20) NOT NULL,
        brushing_tolerance VARCHAR(20) NOT NULL,
        nail_trim_tolerance VARCHAR(20) NOT NULL,
        ear_cleaning_tolerance VARCHAR(20) NOT NULL,
        handling_readiness VARCHAR(20) NOT NULL,
        recommended_session_length_minutes INT,
        special_handling_required BOOLEAN NOT NULL DEFAULT 0,
        handling_notes TEXT,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE,
        FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE SET NULL,
        FOREIGN KEY (recorded_by_user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS owner_notes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        owner_id INT NOT NULL,
        staff_id INT NOT NULL,
        note TEXT NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (staff_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """,
]

def _connection_kwargs(include_database: bool = True) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "host": CONFIG.db_host,
        "port": CONFIG.db_port,
        "user": CONFIG.db_user,
        "password": CONFIG.db_password,
        "autocommit": False,
    }
    if include_database:
        kwargs["database"] = CONFIG.db_name
    return kwargs

@contextmanager
def get_connection(include_database: bool = True):
    connection = mysql.connector.connect(**_connection_kwargs(include_database=include_database))
    try:
        yield connection
    finally:
        connection.close()

def _list_columns(connection, table_name: str) -> set[str]:
    cursor = connection.cursor()
    cursor.execute(f"SHOW COLUMNS FROM {table_name}")
    return {row[0] for row in cursor.fetchall()}

def _create_app_tables(connection) -> None:
    cursor = connection.cursor(dictionary=True)
    for statement in DDL_STATEMENTS:
        cursor.execute(statement)
    connection.commit()

def _migrate_legacy_schema(connection) -> None:
    cursor = connection.cursor()

    user_columns = _list_columns(connection, "users")
    if "name" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN name VARCHAR(120) NULL")
    if "hashed_password" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN hashed_password VARCHAR(255) NULL")
    refreshed_user_columns = _list_columns(connection, "users")
    if "full_name" in refreshed_user_columns:
        cursor.execute("UPDATE users SET name = COALESCE(name, full_name)")
    if "password_hash" in refreshed_user_columns:
        cursor.execute("UPDATE users SET hashed_password = COALESCE(hashed_password, password_hash)")

    pet_columns = _list_columns(connection, "pets")
    if "name" not in pet_columns:
        cursor.execute("ALTER TABLE pets ADD COLUMN name VARCHAR(120) NULL")
    if "age" not in pet_columns:
        cursor.execute("ALTER TABLE pets ADD COLUMN age INT NULL")
    if "weight" not in pet_columns:
        cursor.execute("ALTER TABLE pets ADD COLUMN weight DECIMAL(7,2) NULL")
    if "vaccination_records_url" not in pet_columns:
        cursor.execute("ALTER TABLE pets ADD COLUMN vaccination_records_url TEXT NULL")
    if "allergies" not in pet_columns:
        cursor.execute("ALTER TABLE pets ADD COLUMN allergies TEXT NULL")
    if "medications" not in pet_columns:
        cursor.execute("ALTER TABLE pets ADD COLUMN medications TEXT NULL")
    if "vaccine_expiry" not in pet_columns:
        cursor.execute("ALTER TABLE pets ADD COLUMN vaccine_expiry DATE NULL")
    pet_recommendation_columns = {
        "diet_stage": "VARCHAR(30) NULL",
        "body_condition": "VARCHAR(30) NULL",
        "food_brand": "VARCHAR(120) NULL",
        "feeding_frequency": "VARCHAR(60) NULL",
        "appetite_status": "VARCHAR(40) NULL",
        "water_intake_status": "VARCHAR(40) NULL",
        "nutrition_notes": "TEXT NULL",
        "emotional_condition": "VARCHAR(30) NULL",
        "behavior_triggers": "TEXT NULL",
        "handling_notes": "TEXT NULL",
        "grooming_tolerance": "VARCHAR(30) NULL",
        "coat_type": "VARCHAR(40) NULL",
        "skin_condition": "VARCHAR(40) NULL",
        "parasite_status": "VARCHAR(30) NULL",
        "recommended_shampoo": "VARCHAR(120) NULL",
        "recommended_add_ons": "TEXT NULL",
        "bath_tolerance": "VARCHAR(20) NULL",
        "dryer_tolerance": "VARCHAR(20) NULL",
        "brushing_tolerance": "VARCHAR(20) NULL",
        "nail_trim_tolerance": "VARCHAR(20) NULL",
        "ear_cleaning_tolerance": "VARCHAR(20) NULL",
        "handling_readiness": "VARCHAR(20) NULL",
        "temperament": "VARCHAR(40) NULL",
    }
    for column_name, column_type in pet_recommendation_columns.items():
        if column_name not in pet_columns:
            cursor.execute(f"ALTER TABLE pets ADD COLUMN {column_name} {column_type}")
    refreshed_pet_columns = _list_columns(connection, "pets")
    if "pet_name" in refreshed_pet_columns:
        cursor.execute("UPDATE pets SET name = COALESCE(name, pet_name)")
    if "age_years" in refreshed_pet_columns:
        cursor.execute("UPDATE pets SET age = COALESCE(age, age_years)")
    if "weight_kg" in refreshed_pet_columns:
        cursor.execute("UPDATE pets SET weight = COALESCE(weight, weight_kg)")

    appointment_columns = _list_columns(connection, "appointments")
    if "slot_id" not in appointment_columns:
        cursor.execute("ALTER TABLE appointments ADD COLUMN slot_id INT NULL")
    if "service_name" not in appointment_columns:
        cursor.execute("ALTER TABLE appointments ADD COLUMN service_name VARCHAR(120) NULL")
    if "add_ons" not in appointment_columns:
        cursor.execute("ALTER TABLE appointments ADD COLUMN add_ons TEXT NULL")
    if "slot_start" not in appointment_columns:
        cursor.execute("ALTER TABLE appointments ADD COLUMN slot_start DATETIME NULL")
    if "slot_end" not in appointment_columns:
        cursor.execute("ALTER TABLE appointments ADD COLUMN slot_end DATETIME NULL")
    if "rating" not in appointment_columns:
        cursor.execute("ALTER TABLE appointments ADD COLUMN rating INT NULL")
    appointment_recommendation_columns = {
        "behavior_alert": "VARCHAR(120) NULL",
        "recommended_shampoo": "VARCHAR(120) NULL",
        "handling_level": "VARCHAR(20) NULL",
        "prep_notes": "TEXT NULL",
        "nutrition_flag": "VARCHAR(80) NULL",
    }
    for column_name, column_type in appointment_recommendation_columns.items():
        if column_name not in appointment_columns:
            cursor.execute(f"ALTER TABLE appointments ADD COLUMN {column_name} {column_type}")
    refreshed_appointment_columns = _list_columns(connection, "appointments")
    if {"appointment_date", "start_time"}.issubset(refreshed_appointment_columns):
        cursor.execute(
            """
            UPDATE appointments
            SET slot_start = COALESCE(slot_start, TIMESTAMP(appointment_date, start_time))
            """
        )
    if {"appointment_date", "end_time"}.issubset(refreshed_appointment_columns):
        cursor.execute(
            """
            UPDATE appointments
            SET slot_end = COALESCE(slot_end, TIMESTAMP(appointment_date, end_time))
            """
        )
    if "service_id" in refreshed_appointment_columns:
        cursor.execute(
            """
            ALTER TABLE appointments
            MODIFY COLUMN service_id INT NULL
            """
        )
        cursor.execute(
            """
            UPDATE appointments
            SET service_name = COALESCE(service_name, CONCAT('Service #', service_id))
            """
        )
    cursor.execute(
        """
        ALTER TABLE appointments
        MODIFY COLUMN status VARCHAR(30) NOT NULL DEFAULT 'confirmed'
        """
    )
    vax_columns = _list_columns(connection, "pet_vaccinations")
    if "created_by" not in vax_columns:
        cursor.execute("ALTER TABLE pet_vaccinations ADD COLUMN created_by INT NULL")
        cursor.execute("ALTER TABLE pet_vaccinations ADD CONSTRAINT fk_vax_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL")
    if "updated_at" not in vax_columns:
        cursor.execute("ALTER TABLE pet_vaccinations ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
    connection.commit()

def _seed_dropdown_data(connection) -> None:
    cursor = connection.cursor()

            
    dog_breeds = [
        "Aspin (Mixed)", "Labrador Retriever", "Golden Retriever", "German Shepherd",
        "Bulldog", "Poodle", "Beagle", "Rottweiler", "Yorkshire Terrier", "Boxer",
        "Dachshund", "Siberian Husky", "Great Dane", "Doberman", "Shih Tzu",
        "French Bulldog", "Chihuahua", "Pomeranian", "Border Collie", "Maltese",
        "Cocker Spaniel", "Jack Russell Terrier", "Dalmatian", "Japanese Spitz",
        "Chow Chow", "Bichon Frise", "Samoyed", "Akita", "Shar-Pei", "Corgi",
    ]
    cat_breeds = [
        "Puspin (Mixed)", "Persian", "Maine Coon", "Siamese", "British Shorthair",
        "Ragdoll", "Sphynx", "Abyssinian", "Bengal", "American Shorthair",
        "Scottish Fold", "Birman", "Russian Blue", "Exotic Shorthair",
        "Norwegian Forest Cat", "Tonkinese", "Turkish Angora",
    ]
    cursor.execute("SELECT COUNT(*) FROM breeds")
    if cursor.fetchone()[0] == 0:
        for breed in dog_breeds:
            cursor.execute(
                "INSERT IGNORE INTO breeds (species, breed_name) VALUES ('Dog', %s)", (breed,)
            )
        for breed in cat_breeds:
            cursor.execute(
                "INSERT IGNORE INTO breeds (species, breed_name) VALUES ('Cat', %s)", (breed,)
            )

                     
    allergy_list = [
        "None", "Chicken", "Beef", "Pork", "Fish", "Grain", "Soy", "Dairy",
        "Pollen", "Dust", "Shampoo fragrance", "Insect bites", "Other",
    ]
    cursor.execute("SELECT COUNT(*) FROM allergy_options")
    if cursor.fetchone()[0] == 0:
        for item in allergy_list:
            cursor.execute("INSERT IGNORE INTO allergy_options (allergy_name) VALUES (%s)", (item,))

                        
    medication_list = [
        "None", "Antihistamines", "Pain relievers", "Antibiotics", "Anti-parasitic",
        "Flea/tick prevention", "Heart medication", "Insulin", "Steroids",
        "Probiotics", "Other",
    ]
    cursor.execute("SELECT COUNT(*) FROM medication_options")
    if cursor.fetchone()[0] == 0:
        for item in medication_list:
            cursor.execute("INSERT IGNORE INTO medication_options (medication_name) VALUES (%s)", (item,))

                        
    product_category_list = [
        "Shampoo", "Conditioner", "Brush/Comb", "Nail clipper",
        "Ear cleaner", "Toothbrush/toothpaste", "Supplement", "Treat",
    ]
    cursor.execute("SELECT COUNT(*) FROM product_categories")
    if cursor.fetchone()[0] == 0:
        for item in product_category_list:
            cursor.execute("INSERT IGNORE INTO product_categories (category_name) VALUES (%s)", (item,))

                   
    shampoo_type_list = [
        "Hypoallergenic", "Medicated (antifungal)", "Oatmeal soothing",
        "Flea & tick", "Deodorizing", "Puppy/kitten gentle",
        "Whitening", "Color enhancing",
    ]
    cursor.execute("SELECT COUNT(*) FROM shampoo_types")
    if cursor.fetchone()[0] == 0:
        for item in shampoo_type_list:
            cursor.execute("INSERT IGNORE INTO shampoo_types (type_name) VALUES (%s)", (item,))

                     
    nutrition_flag_list = [
        "Grain-free", "High protein", "Organic", "Gluten-free",
        "No artificial preservatives", "Joint support (glucosamine)",
        "Skin & coat (omega-3)", "Digestive health (probiotics)",
    ]
    cursor.execute("SELECT COUNT(*) FROM nutrition_flags")
    if cursor.fetchone()[0] == 0:
        for item in nutrition_flag_list:
            cursor.execute("INSERT IGNORE INTO nutrition_flags (flag_name) VALUES (%s)", (item,))

                       
    behavioral_alert_list = [
        "Aggressive during grooming", "Fear of water", "Sensitive ears",
        "Bites when touched paws", "Anxious in crowds", "Requires muzzle",
        "Not child-friendly",
    ]
    cursor.execute("SELECT COUNT(*) FROM behavioral_alerts")
    if cursor.fetchone()[0] == 0:
        for item in behavioral_alert_list:
            cursor.execute("INSERT IGNORE INTO behavioral_alerts (alert_name) VALUES (%s)", (item,))

    connection.commit()

def init_db() -> None:
    with get_connection(include_database=False) as connection:
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {CONFIG.db_name}")
        connection.commit()

    with get_connection() as connection:
        _create_app_tables(connection)
        _migrate_legacy_schema(connection)
        _seed_dropdown_data(connection)

def _row(cursor) -> dict[str, Any] | None:
    result = cursor.fetchone()
    return dict(result) if result else None

def fetch_all(query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or tuple())
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def fetch_one(query: str, params: tuple[Any, ...] | None = None) -> dict[str, Any] | None:
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or tuple())
        row = cursor.fetchone()
        return dict(row) if row else None

def execute(query: str, params: tuple[Any, ...] | None = None) -> int:
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, params or tuple())
        connection.commit()
        return cursor.lastrowid

def create_user(name: str, email: str, phone: str, password: str, role: str = "owner") -> int:
    existing = fetch_one("SELECT id FROM users WHERE email = %s", (email,))
    if existing:
        raise ValueError("An account with this email already exists.")
    hashed_password = generate_password_hash(password)
    user_id = execute(
        "INSERT INTO users (name, email, phone, role, hashed_password) VALUES (%s, %s, %s, %s, %s)",
        (name, email, phone, role, hashed_password),
    )
    if role in {"admin", "groomer"}:
        execute("INSERT INTO groomers (user_id, bio) VALUES (%s, %s)", (user_id, "Tin Pet grooming specialist"))
    return user_id

def authenticate_user(email: str, password: str) -> UserRecord | None:
    user = fetch_one("SELECT * FROM users WHERE email = %s", (email,))
    if not user:
        return None
    if not check_password_hash(user["hashed_password"], password):
        return None
    groomer = fetch_one("SELECT id, bio FROM groomers WHERE user_id = %s", (user["id"],))
    user["groomer_profile"] = groomer
    return cast(UserRecord, user)

def get_user_by_id(user_id: int) -> UserRecord | None:
    user = fetch_one("SELECT id, name, email, phone, role, created_at FROM users WHERE id = %s", (user_id,))
    if not user:
        return None
    groomer = fetch_one("SELECT id, bio FROM groomers WHERE user_id = %s", (user_id,))
    user["groomer_profile"] = groomer
    return cast(UserRecord, user)

def list_breeds(species: str) -> list[str]:
    rows = fetch_all(
        "SELECT breed_name FROM breeds WHERE species = %s ORDER BY breed_name",
        (species.strip().title(),),
    )
    return [r["breed_name"] for r in rows]

def list_allergy_options() -> list[str]:
    rows = fetch_all("SELECT allergy_name FROM allergy_options ORDER BY id")
    return [r["allergy_name"] for r in rows]

def list_medication_options() -> list[str]:
    rows = fetch_all("SELECT medication_name FROM medication_options ORDER BY id")
    return [r["medication_name"] for r in rows]

def list_shampoo_types() -> list[str]:
    rows = fetch_all("SELECT type_name FROM shampoo_types ORDER BY id")
    return [r["type_name"] for r in rows]

def list_nutrition_flags() -> list[str]:
    rows = fetch_all("SELECT flag_name FROM nutrition_flags ORDER BY id")
    return [r["flag_name"] for r in rows]

def list_behavioral_alerts() -> list[str]:
    rows = fetch_all("SELECT alert_name FROM behavioral_alerts ORDER BY id")
    return [r["alert_name"] for r in rows]

def list_product_categories() -> list[str]:
    rows = fetch_all("SELECT category_name FROM product_categories ORDER BY id")
    return [r["category_name"] for r in rows]

def list_groomers() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT g.id, u.name, u.email, u.phone, g.bio
        FROM groomers g
        JOIN users u ON u.id = g.user_id
        ORDER BY u.name
        """
    )

def search_owners(search_term: str) -> list[dict[str, Any]]:
    like = f"%{search_term}%"
    return fetch_all(
        "SELECT id, name, email, phone FROM users WHERE role = 'owner' AND (name LIKE %s OR email LIKE %s OR phone LIKE %s) ORDER BY name LIMIT 20",
        (like, like, like),
    )

def list_pending_appointments() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT a.*, u.name AS owner_name, u.phone AS owner_phone,
               p.name AS pet_name, p.species, p.breed,
               g_user.name AS groomer_name
        FROM appointments a
        JOIN users u ON u.id = a.owner_id
        JOIN pets p ON p.id = a.pet_id
        JOIN groomers g ON g.id = a.groomer_id
        JOIN users g_user ON g_user.id = g.user_id
        WHERE a.status = 'pending'
        ORDER BY a.slot_start
        """
    )

def approve_appointment(appointment_id: int) -> None:
    execute("UPDATE appointments SET status = 'confirmed' WHERE id = %s AND status = 'pending'", (appointment_id,))

def reject_appointment(appointment_id: int) -> None:
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT slot_id FROM appointments WHERE id = %s", (appointment_id,))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE time_slots SET status = 'available' WHERE id = %s", (row["slot_id"],))
        cursor.execute("UPDATE appointments SET status = 'cancelled' WHERE id = %s", (appointment_id,))
        conn.commit()

def get_chatbot_keyword_analysis(start_date: "date", end_date: "date") -> dict[str, Any]:
    from datetime import time as _time
    from datetime import datetime as _dt
    start_dt = _dt.combine(start_date, _time.min)
    end_dt = _dt.combine(end_date, _time.max)

    logs = fetch_all(
        "SELECT question, topic, timestamp FROM chat_logs WHERE timestamp BETWEEN %s AND %s ORDER BY timestamp DESC",
        (start_dt, end_dt),
    )

    HEALTH_KEYWORDS = [
        "flea", "tick", "allergy", "allergic", "skin", "itch", "rash", "wound", "infection",
        "vaccination", "vaccine", "rabies", "deworming", "ear", "eye", "dental", "teeth",
        "nail", "mat", "matted", "shed", "shedding", "anxiety", "senior", "diet", "weight",
    ]
    TOPIC_LABELS = {
        "grooming_schedule": "Grooming Schedule", "breed_tips_shih_tzu": "Shih Tzu Tips",
        "breed_tips_poodle": "Poodle Tips", "breed_tips_husky": "Husky Tips",
        "breed_tips_persian": "Persian Tips", "cat_hates_bath": "Cat Bathing",
        "anxious_dog": "Anxious Dogs", "skin_health": "Skin Health",
        "flea_tick": "Flea & Tick", "ear_cleaning": "Ear Cleaning",
        "nail_trim": "Nail Trim", "matted_fur": "Matted Fur",
        "puppy_first_groom": "Puppy Grooming", "vaccination": "Vaccination",
        "faq_walkins": "Walk-ins FAQ", "faq_cancel": "Cancellation FAQ",
        "faq_pricing": "Pricing FAQ", "faq_sms": "SMS FAQ",
        "dental_care": "Dental Care", "shedding": "Shedding",
        "senior_pet": "Senior Pets", "post_groom_care": "Post-Groom Care",
    }

    keyword_counts: dict[str, int] = {}
    for log in logs:
        q = (log.get("question") or "").lower()
        for kw in HEALTH_KEYWORDS:
            if kw in q:
                keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

    topic_counts: dict[str, int] = {}
    for log in logs:
        t = log.get("topic") or "unknown"
        label = TOPIC_LABELS.get(t, t.replace("_", " ").title())
        topic_counts[label] = topic_counts.get(label, 0) + 1

    sorted_kw = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)

    recent_questions = [
        {"question": l["question"], "topic": TOPIC_LABELS.get(l["topic"] or "", l.get("topic", "") or ""), "timestamp": str(l["timestamp"])}
        for l in logs[:15]
    ]

    return {
        "keyword_counts": [{"keyword": k, "count": v} for k, v in sorted_kw],
        "topic_counts": [{"topic": t, "count": v} for t, v in sorted_topics],
        "recent_questions": recent_questions,
        "total_questions": len(logs),
    }

def save_uploaded_file(uploaded_file: Any) -> str | None:
    if uploaded_file is None:
        return None
    file_name_attr = getattr(uploaded_file, "filename", None) or getattr(uploaded_file, "name", "upload.bin")
    suffix = Path(file_name_attr).suffix or ".bin"
    file_name = f"{uuid.uuid4().hex}{suffix}"
    file_path = UPLOAD_DIR / file_name
    if hasattr(uploaded_file, "save"):
        uploaded_file.save(file_path)
    elif hasattr(uploaded_file, "getbuffer"):
        file_path.write_bytes(uploaded_file.getbuffer())
    else:
        file_path.write_bytes(uploaded_file.read())
    return str(file_path.relative_to(Path(__file__).resolve().parent)).replace("\\", "/")

PET_RECOMMENDATION_PROFILE_COLUMNS = {
    "diet_stage",
    "body_condition",
    "food_brand",
    "feeding_frequency",
    "appetite_status",
    "water_intake_status",
    "nutrition_notes",
    "emotional_condition",
    "behavior_triggers",
    "handling_notes",
    "grooming_tolerance",
    "coat_type",
    "skin_condition",
    "parasite_status",
    "recommended_shampoo",
    "recommended_add_ons",
    "bath_tolerance",
    "dryer_tolerance",
    "brushing_tolerance",
    "nail_trim_tolerance",
    "ear_cleaning_tolerance",
    "handling_readiness",
    "temperament",
}

APPOINTMENT_RECOMMENDATION_COLUMNS = {
    "behavior_alert",
    "recommended_shampoo",
    "handling_level",
    "prep_notes",
    "nutrition_flag",
}

def _ensure_pet_exists(pet_id: int) -> None:
    if not fetch_one("SELECT id FROM pets WHERE id = %s", (pet_id,)):
        raise ValueError("Pet not found.")

def _ensure_appointment_exists(appointment_id: int) -> None:
    if not fetch_one("SELECT id FROM appointments WHERE id = %s", (appointment_id,)):
        raise ValueError("Appointment not found.")

def _update_columns(table_name: str, record_id: int, id_column: str, values: dict[str, Any], allowed_columns: set[str]) -> None:
    filtered = {column: value for column, value in values.items() if column in allowed_columns}
    if not filtered:
        raise ValueError("No valid fields were provided.")
    assignments = ", ".join(f"{column} = %s" for column in filtered)
    params = tuple(filtered.values()) + (record_id,)
    execute(f"UPDATE {table_name} SET {assignments} WHERE {id_column} = %s", params)

def upsert_pet(
    owner_id: int,
    name: str,
    species: str,
    breed: str,
    age: int,
    weight: float,
    medical_history: str,
    allergies: str,
    medications: str,
    vaccination_records_url: str | None,
    vaccine_expiry: str | None = None,
    pet_id: int | None = None,
) -> int:
    if pet_id is None:
        return execute(
            """
            INSERT INTO pets (
                owner_id, name, species, breed, age, weight,
                vaccination_records_url, vaccine_expiry, medical_history, allergies, medications
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                owner_id,
                name,
                species,
                breed,
                age,
                Decimal(str(weight)),
                vaccination_records_url,
                vaccine_expiry,
                medical_history,
                allergies,
                medications,
            ),
        )

    current = fetch_one("SELECT vaccination_records_url, vaccine_expiry FROM pets WHERE id = %s AND owner_id = %s", (pet_id, owner_id))
    if not current:
        raise ValueError("Pet not found.")
    final_record_url = vaccination_records_url or current["vaccination_records_url"]
    final_vaccine_expiry = vaccine_expiry or current["vaccine_expiry"]
    execute(
        """
        UPDATE pets
        SET name = %s,
            species = %s,
            breed = %s,
            age = %s,
            weight = %s,
            vaccination_records_url = %s,
            vaccine_expiry = %s,
            medical_history = %s,
            allergies = %s,
            medications = %s
        WHERE id = %s AND owner_id = %s
        """,
        (
            name,
            species,
            breed,
            age,
            Decimal(str(weight)),
            final_record_url,
            final_vaccine_expiry,
            medical_history,
            allergies,
            medications,
            pet_id,
            owner_id,
        ),
    )
    return pet_id

def list_owner_pets(owner_id: int) -> list[dict[str, Any]]:
    records = fetch_all("SELECT * FROM pets WHERE owner_id = %s ORDER BY created_at DESC", (owner_id,))
    return _attach_pet_recommendation_snapshots(records)

def get_pet_by_id(pet_id: int) -> dict[str, Any] | None:
    return fetch_one("SELECT * FROM pets WHERE id = %s", (pet_id,))

                                                                              
                  
                                                                              

def add_pet_vaccination(
    pet_id: int,
    vaccine_name: str,
    date_administered: str | None = None,
    next_due_date: str | None = None,
    vet_name: str | None = None,
    notes: str | None = None,
    created_by: int | None = None,
) -> int:
    _ensure_pet_exists(pet_id)
    return execute(
        """
        INSERT INTO pet_vaccinations (
            pet_id, vaccine_name, date_administered, next_due_date, vet_name, notes, created_by
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (pet_id, vaccine_name, date_administered, next_due_date, vet_name, notes, created_by),
    )

def list_pet_vaccinations(pet_id: int) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT pv.*, u.name AS created_by_name
        FROM pet_vaccinations pv
        LEFT JOIN users u ON u.id = pv.created_by
        WHERE pv.pet_id = %s
        ORDER BY pv.date_administered DESC, pv.created_at DESC
        """,
        (pet_id,),
    )

def get_vaccination_by_id(vaccination_id: int) -> dict[str, Any] | None:
    return fetch_one("SELECT * FROM pet_vaccinations WHERE id = %s", (vaccination_id,))

def update_pet_vaccination(
    vaccination_id: int,
    vaccine_name: str,
    date_administered: str | None = None,
    next_due_date: str | None = None,
    vet_name: str | None = None,
    notes: str | None = None,
) -> None:
    execute(
        """
        UPDATE pet_vaccinations
        SET vaccine_name = %s,
            date_administered = %s,
            next_due_date = %s,
            vet_name = %s,
            notes = %s
        WHERE id = %s
        """,
        (vaccine_name, date_administered, next_due_date, vet_name, notes, vaccination_id),
    )

def delete_pet_vaccination(vaccination_id: int) -> None:
    execute("DELETE FROM pet_vaccinations WHERE id = %s", (vaccination_id,))

                                                                              
                                                
                                                                              

def list_all_owners(search_term: str = "", has_pets_filter: str = "all", limit: int = 50, offset: int = 0) -> dict[str, Any]:
    conditions = ["u.role = 'owner'"]
    params: list[Any] = []
    
    if search_term:
        conditions.append("(u.name LIKE %s OR u.email LIKE %s OR u.phone LIKE %s)")
        search_pattern = f"%{search_term}%"
        params.extend([search_pattern, search_pattern, search_pattern])
    
    where_clause = " AND ".join(conditions)
    
                     
    count_query = f"SELECT COUNT(*) as total FROM users u WHERE {where_clause}"
    total_result = fetch_one(count_query, tuple(params) if params else None)
    total = total_result["total"] if total_result else 0
    
                                
    query = f"""
        SELECT 
            u.id,
            u.name,
            u.email,
            u.phone,
            u.created_at,
            COUNT(p.id) as pet_count
        FROM users u
        LEFT JOIN pets p ON u.id = p.owner_id
        WHERE {where_clause}
        GROUP BY u.id, u.name, u.email, u.phone, u.created_at
    """
    
    if has_pets_filter == "with_pets":
        query += " HAVING pet_count > 0"
    elif has_pets_filter == "no_pets":
        query += " HAVING pet_count = 0"
    
    query += " ORDER BY u.created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    owners = fetch_all(query, tuple(params))
    
    return {
        "owners": owners,
        "total": total,
        "limit": limit,
        "offset": offset,
    }

def get_owner_with_pets(owner_id: int) -> dict[str, Any] | None:
    owner = fetch_one(
        """
        SELECT id, name, email, phone, created_at
        FROM users
        WHERE id = %s AND role = 'owner'
        """,
        (owner_id,)
    )
    
    if not owner:
        return None
    
                                 
    pets = fetch_all(
        """
        SELECT *
        FROM pets
        WHERE owner_id = %s
        ORDER BY created_at DESC
        """,
        (owner_id,)
    )
    
                                          
    for pet in pets:
        vaccinations = fetch_all(
            """
            SELECT pv.*, u.name AS created_by_name
            FROM pet_vaccinations pv
            LEFT JOIN users u ON u.id = pv.created_by
            WHERE pv.pet_id = %s
            ORDER BY pv.date_administered DESC
            """,
            (pet["id"],)
        )
        pet["vaccinations"] = vaccinations
    
    owner["pets"] = pets
    
    return owner

def get_owner_notes(owner_id: int) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT 
            ont.id,
            ont.owner_id,
            ont.staff_id,
            ont.note,
            ont.created_at,
            u.name as staff_name
        FROM owner_notes ont
        JOIN users u ON ont.staff_id = u.id
        WHERE ont.owner_id = %s
        ORDER BY ont.created_at DESC
        """,
        (owner_id,)
    )

def add_owner_note(owner_id: int, staff_id: int, note: str) -> int:
    return execute(
        """
        INSERT INTO owner_notes (owner_id, staff_id, note)
        VALUES (%s, %s, %s)
        """,
        (owner_id, staff_id, note)
    )

def update_owner_info(owner_id: int, name: str, email: str, phone: str) -> None:
    execute(
        """
        UPDATE users
        SET name = %s, email = %s, phone = %s
        WHERE id = %s AND role = 'owner'
        """,
        (name, email, phone, owner_id)
    )

def reset_owner_password(owner_id: int, new_password: str) -> None:
    hashed = generate_password_hash(new_password)
    execute(
        """
        UPDATE users
        SET hashed_password = %s
        WHERE id = %s AND role = 'owner'
        """,
        (hashed, owner_id)
    )

def get_owner_appointments(owner_id: int) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT 
            a.*,
            p.name as pet_name,
            u.name as groomer_name,
            g.id as groomer_id
        FROM appointments a
        JOIN pets p ON a.pet_id = p.id
        JOIN groomers g ON a.groomer_id = g.id
        JOIN users u ON g.user_id = u.id
        WHERE a.owner_id = %s
        ORDER BY a.slot_start DESC
        """,
        (owner_id,)
    )

                                                                              

def update_pet_recommendation_profile(pet_id: int, profile_data: dict[str, Any]) -> None:
    _ensure_pet_exists(pet_id)
    _update_columns("pets", pet_id, "id", profile_data, PET_RECOMMENDATION_PROFILE_COLUMNS)

def log_pet_nutrition(
    pet_id: int,
    body_condition: str,
    diet_stage: str | None = None,
    food_brand: str | None = None,
    feeding_frequency: str | None = None,
    coat_support_goal: str | None = None,
    recommended_food_type: str | None = None,
    nutrition_notes: str | None = None,
    recorded_by_user_id: int | None = None,
) -> int:
    _ensure_pet_exists(pet_id)
    return execute(
        """
        INSERT INTO pet_nutrition_logs (
            pet_id, recorded_by_user_id, body_condition, diet_stage,
            food_brand, feeding_frequency, coat_support_goal,
            recommended_food_type, nutrition_notes
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            pet_id,
            recorded_by_user_id,
            body_condition,
            diet_stage,
            food_brand,
            feeding_frequency,
            coat_support_goal,
            recommended_food_type,
            nutrition_notes,
        ),
    )

def list_pet_nutrition_logs(pet_id: int) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT pnl.*, u.name AS recorded_by_name
        FROM pet_nutrition_logs pnl
        LEFT JOIN users u ON u.id = pnl.recorded_by_user_id
        WHERE pnl.pet_id = %s
        ORDER BY pnl.created_at DESC
        """,
        (pet_id,),
    )

def log_pet_behavior(
    pet_id: int,
    emotional_condition: str,
    appointment_id: int | None = None,
    recorded_by_user_id: int | None = None,
    trigger_noise: bool = False,
    trigger_touch: bool = False,
    trigger_dryer: bool = False,
    trigger_nail_trim: bool = False,
    trigger_ear_cleaning: bool = False,
    aggression_risk: str | None = None,
    handling_recommendation: str | None = None,
    behavior_notes: str | None = None,
) -> int:
    _ensure_pet_exists(pet_id)
    if appointment_id is not None:
        _ensure_appointment_exists(appointment_id)
    return execute(
        """
        INSERT INTO pet_behavior_logs (
            pet_id, appointment_id, recorded_by_user_id, emotional_condition,
            trigger_noise, trigger_touch, trigger_dryer, trigger_nail_trim, trigger_ear_cleaning,
            aggression_risk, handling_recommendation, behavior_notes
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            pet_id,
            appointment_id,
            recorded_by_user_id,
            emotional_condition,
            trigger_noise,
            trigger_touch,
            trigger_dryer,
            trigger_nail_trim,
            trigger_ear_cleaning,
            aggression_risk,
            handling_recommendation,
            behavior_notes,
        ),
    )

def list_pet_behavior_logs(pet_id: int) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT pbl.*, u.name AS recorded_by_name
        FROM pet_behavior_logs pbl
        LEFT JOIN users u ON u.id = pbl.recorded_by_user_id
        WHERE pbl.pet_id = %s
        ORDER BY pbl.created_at DESC
        """,
        (pet_id,),
    )

def log_pet_product_recommendation(
    pet_id: int,
    coat_type: str,
    skin_condition: str,
    recommended_shampoo: str,
    appointment_id: int | None = None,
    recorded_by_user_id: int | None = None,
    parasite_status: str | None = None,
    recommended_conditioner: str | None = None,
    recommended_add_ons: str | None = None,
    avoid_ingredients: str | None = None,
    recommendation_reason: str | None = None,
) -> int:
    _ensure_pet_exists(pet_id)
    if appointment_id is not None:
        _ensure_appointment_exists(appointment_id)
    return execute(
        """
        INSERT INTO pet_product_recommendations (
            pet_id, appointment_id, recorded_by_user_id, coat_type, skin_condition,
            parasite_status, recommended_shampoo, recommended_conditioner,
            recommended_add_ons, avoid_ingredients, recommendation_reason
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            pet_id,
            appointment_id,
            recorded_by_user_id,
            coat_type,
            skin_condition,
            parasite_status,
            recommended_shampoo,
            recommended_conditioner,
            recommended_add_ons,
            avoid_ingredients,
            recommendation_reason,
        ),
    )

def list_pet_product_recommendations(pet_id: int) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT ppr.*, u.name AS recorded_by_name
        FROM pet_product_recommendations ppr
        LEFT JOIN users u ON u.id = ppr.recorded_by_user_id
        WHERE ppr.pet_id = %s
        ORDER BY ppr.created_at DESC
        """,
        (pet_id,),
    )

def log_pet_handling_assessment(
    pet_id: int,
    bath_tolerance: str,
    dryer_tolerance: str,
    brushing_tolerance: str,
    nail_trim_tolerance: str,
    ear_cleaning_tolerance: str,
    handling_readiness: str,
    appointment_id: int | None = None,
    recorded_by_user_id: int | None = None,
    recommended_session_length_minutes: int | None = None,
    special_handling_required: bool = False,
    handling_notes: str | None = None,
) -> int:
    _ensure_pet_exists(pet_id)
    if appointment_id is not None:
        _ensure_appointment_exists(appointment_id)
    return execute(
        """
        INSERT INTO pet_handling_assessments (
            pet_id, appointment_id, recorded_by_user_id,
            bath_tolerance, dryer_tolerance, brushing_tolerance,
            nail_trim_tolerance, ear_cleaning_tolerance, handling_readiness,
            recommended_session_length_minutes, special_handling_required, handling_notes
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            pet_id,
            appointment_id,
            recorded_by_user_id,
            bath_tolerance,
            dryer_tolerance,
            brushing_tolerance,
            nail_trim_tolerance,
            ear_cleaning_tolerance,
            handling_readiness,
            recommended_session_length_minutes,
            special_handling_required,
            handling_notes,
        ),
    )

def list_pet_handling_assessments(pet_id: int) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT pha.*, u.name AS recorded_by_name
        FROM pet_handling_assessments pha
        LEFT JOIN users u ON u.id = pha.recorded_by_user_id
        WHERE pha.pet_id = %s
        ORDER BY pha.created_at DESC
        """,
        (pet_id,),
    )

def update_appointment_recommendations(appointment_id: int, recommendation_data: dict[str, Any]) -> None:
    _ensure_appointment_exists(appointment_id)
    _update_columns("appointments", appointment_id, "id", recommendation_data, APPOINTMENT_RECOMMENDATION_COLUMNS)

def search_pet_health_records(search_term: str = "") -> list[dict[str, Any]]:
    like_term = f"%{search_term}%"
    records = fetch_all(
        """
        SELECT p.*, u.name AS owner_name, u.phone AS owner_phone
        FROM pets p
        JOIN users u ON u.id = p.owner_id
        WHERE %s = ''
           OR p.name LIKE %s
           OR p.breed LIKE %s
           OR p.species LIKE %s
           OR u.name LIKE %s
        ORDER BY p.name
        """,
        (search_term, like_term, like_term, like_term, like_term),
    )
    return _attach_pet_recommendation_snapshots(records)

def _attach_pet_recommendation_snapshots(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for record in records:
        pet_id = int(record["id"])
        nutrition_logs = list_pet_nutrition_logs(pet_id)
        behavior_logs = list_pet_behavior_logs(pet_id)
        product_recommendations = list_pet_product_recommendations(pet_id)
        handling_assessments = list_pet_handling_assessments(pet_id)
        record["latest_nutrition_log"] = nutrition_logs[0] if nutrition_logs else None
        record["latest_behavior_log"] = behavior_logs[0] if behavior_logs else None
        record["latest_product_recommendation"] = product_recommendations[0] if product_recommendations else None
        record["latest_handling_assessment"] = handling_assessments[0] if handling_assessments else None
    return records

def create_time_slots(groomer_id: int, selected_date: date, start_hour: int, end_hour: int, interval_minutes: int) -> int:
    start_dt = datetime.combine(selected_date, time(hour=start_hour, minute=0))
    end_dt = datetime.combine(selected_date, time(hour=end_hour, minute=0))
    created = 0
    with get_connection() as connection:
        cursor = connection.cursor()
        current = start_dt
        while current < end_dt:
            slot_end = current + timedelta(minutes=interval_minutes)
            cursor.execute(
                """
                INSERT IGNORE INTO time_slots (groomer_id, slot_start, slot_end, status)
                VALUES (%s, %s, %s, 'available')
                """,
                (groomer_id, current, slot_end),
            )
            created += cursor.rowcount
            current = slot_end
        connection.commit()
    return created

def list_slots_for_day(selected_date: date, groomer_id: int | None = None, available_only: bool = False) -> list[dict[str, Any]]:
    start_dt = datetime.combine(selected_date, time.min)
    end_dt = datetime.combine(selected_date, time.max)
    conditions = ["ts.slot_start BETWEEN %s AND %s"]
    params: list[Any] = [start_dt, end_dt]
    if groomer_id is not None:
        conditions.append("ts.groomer_id = %s")
        params.append(groomer_id)
    if available_only:
        conditions.append("ts.status = 'available'")
    return fetch_all(
        f"""
        SELECT ts.*, u.name AS groomer_name
        FROM time_slots ts
        JOIN groomers g ON g.id = ts.groomer_id
        JOIN users u ON u.id = g.user_id
        WHERE {' AND '.join(conditions)}
        ORDER BY ts.slot_start
        """,
        tuple(params),
    )

def create_appointment(
    owner_id: int,
    pet_id: int,
    groomer_id: int,
    slot_id: int,
    service_name: str,
    add_ons: str,
    notes: str,
) -> dict[str, Any]:
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            connection.start_transaction()
            cursor.execute(
                "SELECT * FROM pets WHERE id = %s AND owner_id = %s FOR UPDATE",
                (pet_id, owner_id),
            )
            pet = cursor.fetchone()
            if not pet:
                raise ValueError("The selected pet does not belong to this user.")

            cursor.execute("SELECT * FROM time_slots WHERE id = %s FOR UPDATE", (slot_id,))
            slot = cursor.fetchone()
            if not slot:
                raise ValueError("The selected time slot no longer exists.")
            if slot["status"] != "available":
                raise ValueError("The selected time slot has already been booked.")
            if int(slot["groomer_id"]) != groomer_id:
                raise ValueError("The slot does not belong to the chosen groomer.")

            cursor.execute(
                """
                INSERT INTO appointments (
                    pet_id, owner_id, groomer_id, slot_id,
                    service_name, add_ons, notes,
                    slot_start, slot_end, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')""",
                (
                    pet_id,
                    owner_id,
                    groomer_id,
                    slot_id,
                    service_name,
                    add_ons,
                    notes,
                    slot["slot_start"],
                    slot["slot_end"],
                ),
            )
            appointment_id = cursor.lastrowid
            cursor.execute("UPDATE time_slots SET status = 'booked' WHERE id = %s", (slot_id,))
            connection.commit()
            return {
                "appointment_id": appointment_id,
                "slot_start": slot["slot_start"],
                "slot_end": slot["slot_end"],
            }
        except Exception:
            connection.rollback()
            raise

def list_owner_appointments(owner_id: int) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT a.*, p.name AS pet_name, p.species, p.breed, u.name AS groomer_name
        FROM appointments a
        JOIN pets p ON p.id = a.pet_id
        JOIN groomers g ON g.id = a.groomer_id
        JOIN users u ON u.id = g.user_id
        WHERE a.owner_id = %s
        ORDER BY a.slot_start DESC
        """,
        (owner_id,),
    )

def list_all_appointments(start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
    conditions = ["1=1"]
    params: list[Any] = []
    if start_date:
        conditions.append("a.slot_start >= %s")
        params.append(datetime.combine(start_date, time.min))
    if end_date:
        conditions.append("a.slot_start <= %s")
        params.append(datetime.combine(end_date, time.max))
    return fetch_all(
        f"""
        SELECT a.*, p.name AS pet_name, u_owner.name AS owner_name, u_owner.phone AS owner_phone, u_groomer.name AS groomer_name
        FROM appointments a
        JOIN pets p ON p.id = a.pet_id
        JOIN users u_owner ON u_owner.id = a.owner_id
        JOIN groomers g ON g.id = a.groomer_id
        JOIN users u_groomer ON u_groomer.id = g.user_id
        WHERE {' AND '.join(conditions)}
        ORDER BY a.slot_start DESC
        """,
        tuple(params),
    )

def list_schedule_for_groomer_user(user_id: int, selected_date: date | None = None) -> list[dict[str, Any]]:
    groomer = fetch_one("SELECT id FROM groomers WHERE user_id = %s", (user_id,))
    if not groomer:
        return []
    if selected_date is None:
        selected_date = date.today()
    start_dt = datetime.combine(selected_date, time.min)
    end_dt = datetime.combine(selected_date, time.max)
    return fetch_all(
        """
        SELECT a.*, p.name AS pet_name, p.species, p.breed, u_owner.name AS owner_name, u_owner.phone AS owner_phone
        FROM appointments a
        JOIN pets p ON p.id = a.pet_id
        JOIN users u_owner ON u_owner.id = a.owner_id
        WHERE a.groomer_id = %s AND a.slot_start BETWEEN %s AND %s
        ORDER BY a.slot_start
        """,
        (groomer["id"], start_dt, end_dt),
    )

def update_appointment_status(appointment_id: int, status: str) -> None:
    appointment = fetch_one("SELECT slot_id FROM appointments WHERE id = %s", (appointment_id,))
    if not appointment:
        raise ValueError("Appointment not found.")
    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            connection.start_transaction()
            cursor.execute("UPDATE appointments SET status = %s WHERE id = %s", (status, appointment_id))
            if status in {"cancelled", "rescheduled"}:
                cursor.execute("UPDATE time_slots SET status = 'available' WHERE id = %s", (appointment["slot_id"],))
            connection.commit()
        except Exception:
            connection.rollback()
            raise

def rate_appointment(appointment_id: int, rating: int) -> None:
    execute("UPDATE appointments SET rating = %s WHERE id = %s", (rating, appointment_id))

def create_or_update_cache(cache_key: str, payload: dict[str, Any]) -> None:
    execute(
        """
        INSERT INTO analytics_cache (cache_key, payload_json)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE payload_json = VALUES(payload_json)
        """,
        (cache_key, json.dumps(payload, default=str)),
    )

def log_chat(user_id: int | None, question: str, answer: str, topic: str) -> None:
    execute(
        "INSERT INTO chat_logs (user_id, question, answer, topic) VALUES (%s, %s, %s, %s)",
        (user_id, question, answer, topic),
    )

def log_sms(
    user_id: int | None,
    phone: str,
    message_type: str,
    message_body: str,
    provider_mode: str,
    delivery_status: str = "sent",
    related_appointment_id: int | None = None,
) -> None:
    execute(
        """
        INSERT INTO sms_logs (
            user_id, phone, message_type, message_body,
            related_appointment_id, provider_mode, delivery_status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            phone,
            message_type,
            message_body,
            related_appointment_id,
            provider_mode,
            delivery_status,
        ),
    )

def list_due_reminders() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT a.id AS appointment_id,
               a.owner_id,
               a.slot_start,
               p.name AS pet_name,
               u.name AS owner_name,
               u.phone AS owner_phone
        FROM appointments a
        JOIN pets p ON p.id = a.pet_id
        JOIN users u ON u.id = a.owner_id
        LEFT JOIN sms_logs s ON s.related_appointment_id = a.id AND s.message_type = 'reminder'
        WHERE a.status = 'confirmed'
          AND a.slot_start BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 24 HOUR)
          AND s.id IS NULL
        ORDER BY a.slot_start ASC
        """
    )

def get_chat_logs(limit: int = 200) -> list[dict[str, Any]]:
    return fetch_all("SELECT * FROM chat_logs ORDER BY timestamp DESC LIMIT %s", (limit,))

def get_dashboard_metrics() -> dict[str, Any]:
    metrics = {
        "appointments_today": fetch_one(
            "SELECT COUNT(*) AS total FROM appointments WHERE DATE(slot_start) = CURDATE()"
        )["total"],
        "active_clients": fetch_one("SELECT COUNT(*) AS total FROM users WHERE role = 'owner'")["total"],
        "registered_pets": fetch_one("SELECT COUNT(*) AS total FROM pets")["total"],
        "pending_slots": fetch_one("SELECT COUNT(*) AS total FROM time_slots WHERE status = 'available'")["total"],
    }
    create_or_update_cache("dashboard_metrics", metrics)
    return metrics

def get_analytics_data(start_date: date, end_date: date) -> dict[str, list[dict[str, Any]]]:
    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date, time.max)
    top_topics = fetch_all(
        """
        SELECT topic, COUNT(*) AS total
        FROM chat_logs
        WHERE timestamp BETWEEN %s AND %s
        GROUP BY topic
        ORDER BY total DESC
        LIMIT 10
        """,
        (start_dt, end_dt),
    )
    popular_services = fetch_all(
        """
        SELECT service_name, COUNT(*) AS total
        FROM appointments
        WHERE slot_start BETWEEN %s AND %s
        GROUP BY service_name
        ORDER BY total DESC
        """,
        (start_dt, end_dt),
    )
    peak_hours = fetch_all(
        """
        SELECT HOUR(slot_start) AS hour_bucket, COUNT(*) AS total
        FROM appointments
        WHERE slot_start BETWEEN %s AND %s
        GROUP BY HOUR(slot_start)
        ORDER BY hour_bucket
        """,
        (start_dt, end_dt),
    )
    busiest_days = fetch_all(
        """
        SELECT DAYNAME(slot_start) AS day_name, COUNT(*) AS total
        FROM appointments
        WHERE slot_start BETWEEN %s AND %s
        GROUP BY DAYNAME(slot_start)
        ORDER BY FIELD(DAYNAME(slot_start), 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
        """,
        (start_dt, end_dt),
    )
    satisfaction = fetch_all(
        """
        SELECT DATE_FORMAT(slot_start, '%Y-%m-%d') AS day_label, AVG(rating) AS average_rating
        FROM appointments
        WHERE slot_start BETWEEN %s AND %s AND rating IS NOT NULL
        GROUP BY DATE_FORMAT(slot_start, '%Y-%m-%d')
        ORDER BY day_label
        """,
        (start_dt, end_dt),
    )
    payload = {
        "top_topics": top_topics,
        "popular_services": popular_services,
        "peak_hours": peak_hours,
        "busiest_days": busiest_days,
        "satisfaction": satisfaction,
    }
    create_or_update_cache("analytics_data", payload)
    return payload

def seed_demo_data() -> None:
    admin = fetch_one("SELECT id FROM users WHERE email = %s", ("admin@tinpet.local",))
    if admin:
        admin_id = admin["id"]
    else:
        admin_id = create_user("Tin Pet Admin", "admin@tinpet.local", "+639123456700", "admin123", role="admin")

    groomer_user = fetch_one("SELECT id FROM users WHERE email = %s", ("groomer@tinpet.local",))
    if groomer_user:
        groomer_user_id = groomer_user["id"]
        if not fetch_one("SELECT id FROM groomers WHERE user_id = %s", (groomer_user_id,)):
            execute("INSERT INTO groomers (user_id, bio) VALUES (%s, %s)", (groomer_user_id, "Tin Pet grooming specialist"))
    else:
        groomer_user_id = create_user("Mika Santos", "groomer@tinpet.local", "+639123456701", "groomer123", role="groomer")

    owner = fetch_one("SELECT id FROM users WHERE email = %s", ("owner@tinpet.local",))
    if owner:
        owner_id = owner["id"]
    else:
        owner_id = create_user("Ella Mendoza", "owner@tinpet.local", "+639123456702", "owner123", role="owner")

    second_owner = fetch_one("SELECT id FROM users WHERE email = %s", ("owner2@tinpet.local",))
    if second_owner:
        second_owner_id = second_owner["id"]
    else:
        second_owner_id = create_user("Paolo Cruz", "owner2@tinpet.local", "+639123456703", "owner123", role="owner")

    third_owner = fetch_one("SELECT id FROM users WHERE email = %s", ("owner3@tinpet.local",))
    if third_owner:
        third_owner_id = third_owner["id"]
    else:
        third_owner_id = create_user("Maria Garcia", "owner3@tinpet.local", "+639123456704", "owner123", role="owner")

    fourth_owner = fetch_one("SELECT id FROM users WHERE email = %s", ("owner4@tinpet.local",))
    if fourth_owner:
        fourth_owner_id = fourth_owner["id"]
    else:
        fourth_owner_id = create_user("Jose Reyes", "owner4@tinpet.local", "+639123456705", "owner123", role="owner")

    staff2 = fetch_one("SELECT id FROM users WHERE email = %s", ("staff2@tinpet.local",))
    if staff2:
        staff2_user_id = staff2["id"]
        if not fetch_one("SELECT id FROM groomers WHERE user_id = %s", (staff2_user_id,)):
            execute("INSERT INTO groomers (user_id, bio) VALUES (%s, %s)", (staff2_user_id, "Specialist in cats and small breeds"))
    else:
        staff2_user_id = create_user("Ana Lim", "staff2@tinpet.local", "+639123456706", "staff123", role="groomer")

    groomer_profile = fetch_one("SELECT id FROM groomers WHERE user_id = %s", (groomer_user_id,))
    if not groomer_profile:
        raise Error("Failed to create groomer profile.")

    existing_pet_1 = fetch_one("SELECT id FROM pets WHERE owner_id = %s AND name = %s", (owner_id, "Mochi"))
    if existing_pet_1:
        pet_1 = existing_pet_1["id"]
    else:
        pet_1 = upsert_pet(
            owner_id=owner_id,
            name="Mochi",
            species="Dog",
            breed="Shih Tzu",
            age=4,
            weight=6.2,
            medical_history="Sensitive skin and seasonal itching.",
            allergies="Chicken",
            medications="Omega supplements",
            vaccination_records_url=None,
        )

    existing_pet_2 = fetch_one("SELECT id FROM pets WHERE owner_id = %s AND name = %s", (second_owner_id, "Luna"))
    if existing_pet_2:
        pet_2 = existing_pet_2["id"]
    else:
        pet_2 = upsert_pet(
            owner_id=second_owner_id,
            name="Luna",
            species="Cat",
            breed="Persian",
            age=3,
            weight=4.5,
            medical_history="Mild eye discharge during dry months.",
            allergies="None recorded",
            medications="Eye drops as needed",
            vaccination_records_url=None,
        )

    target_dates = [date.today(), date.today() + timedelta(days=1), date.today() + timedelta(days=2)]
    for target_date in target_dates:
        create_time_slots(groomer_profile["id"], target_date, 9, 17, 60)

    available_today = list_slots_for_day(date.today(), groomer_id=groomer_profile["id"], available_only=True)
    available_tomorrow = list_slots_for_day(date.today() + timedelta(days=1), groomer_id=groomer_profile["id"], available_only=True)
    has_demo_appointment_1 = fetch_one(
        "SELECT id FROM appointments WHERE owner_id = %s AND pet_id = %s AND service_name = %s",
        (owner_id, pet_1, "Full Groom"),
    )
    has_demo_appointment_2 = fetch_one(
        "SELECT id FROM appointments WHERE owner_id = %s AND pet_id = %s AND service_name = %s",
        (second_owner_id, pet_2, "Bath and Blow Dry"),
    )
    if available_today and not has_demo_appointment_1:
        create_appointment(owner_id, pet_1, groomer_profile["id"], available_today[0]["id"], "Full Groom", "Nail trim, Ear cleaning", "Prefers hypoallergenic shampoo")
    if available_tomorrow and not has_demo_appointment_2:
        create_appointment(second_owner_id, pet_2, groomer_profile["id"], available_tomorrow[0]["id"], "Bath and Blow Dry", "De-shedding", "Keep session gentle")

    if not fetch_one("SELECT id FROM chat_logs WHERE user_id = %s AND topic = %s LIMIT 1", (owner_id, "grooming_schedule")):
        log_chat(owner_id, "How often should I bathe my Shih Tzu?", "A Shih Tzu usually does well with a bath every 3 to 4 weeks, unless your groomer suggests a shorter schedule.", "grooming_schedule")
    if not fetch_one("SELECT id FROM chat_logs WHERE user_id = %s AND topic = %s LIMIT 1", (owner_id, "faq_walkins")):
        log_chat(owner_id, "Do you accept walk-ins?", "Bookings are prioritized. Walk-ins depend on same-day slot availability.", "faq_walkins")
    if not fetch_one("SELECT id FROM chat_logs WHERE user_id = %s AND topic = %s LIMIT 1", (admin_id, "breed_tips")):
        log_chat(admin_id, "Best haircut for a Persian cat?", "A sanitary trim plus regular coat brushing helps Persian cats stay comfortable, but confirm with your groomer before clipping large areas.", "breed_tips")
