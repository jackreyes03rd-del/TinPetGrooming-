"""
Database Migration: Add owner_notes table
Run this script to add the owner_notes table for staff notes about pet owners.
"""

import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "tin_pet_grooming"
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS owner_notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    owner_id INT NOT NULL,
    staff_id INT NOT NULL,
    note TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (staff_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_owner_id (owner_id),
    INDEX idx_created_at (created_at)
)
"""

def run_migration():
    """Run the migration to add owner_notes table."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        print("🔧 Running migration: Add owner_notes table...")
        cursor.execute(CREATE_TABLE_SQL)
        connection.commit()
        
        # Verify table was created
        cursor.execute("SHOW TABLES LIKE 'owner_notes'")
        if cursor.fetchone():
            print("✅ owner_notes table created successfully!")
            
            # Show table structure
            cursor.execute("DESCRIBE owner_notes")
            columns = cursor.fetchall()
            print("\n📋 Table structure:")
            for col in columns:
                print(f"  - {col[0]} ({col[1]})")
        else:
            print("❌ Failed to create owner_notes table")
        
        cursor.close()
        connection.close()
        
    except Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_migration()
