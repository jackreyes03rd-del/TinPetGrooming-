"""
Database Migration: Add pet_vaccinations table
Run this script to add the vaccination table to an existing database.
"""

import mysql.connector
from mysql.connector import Error

# Database configuration
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': '',  # Update if you have a password
    'database': 'tin_pet_grooming'
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS pet_vaccinations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pet_id INT NOT NULL,
    vaccine_name VARCHAR(100) NOT NULL,
    date_administered DATE,
    next_due_date DATE,
    vet_name VARCHAR(100),
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE,
    INDEX idx_pet_id (pet_id),
    INDEX idx_next_due_date (next_due_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

def run_migration():
    """Run the migration to add pet_vaccinations table."""
    connection = None
    try:
        # Connect to database
        print("Connecting to database...")
        connection = mysql.connector.connect(**DB_CONFIG)
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Check if table already exists
            cursor.execute("SHOW TABLES LIKE 'pet_vaccinations'")
            result = cursor.fetchone()
            
            if result:
                print("✓ Table 'pet_vaccinations' already exists. No migration needed.")
                return
            
            # Create the table
            print("Creating 'pet_vaccinations' table...")
            cursor.execute(CREATE_TABLE_SQL)
            connection.commit()
            
            print("✓ Migration successful! Table 'pet_vaccinations' created.")
            
            # Verify table was created
            cursor.execute("SHOW TABLES LIKE 'pet_vaccinations'")
            result = cursor.fetchone()
            
            if result:
                print("✓ Verification: Table exists in database.")
                
                # Show table structure
                cursor.execute("DESCRIBE pet_vaccinations")
                columns = cursor.fetchall()
                print("\nTable structure:")
                print("-" * 60)
                for col in columns:
                    print(f"  {col[0]:20} {col[1]:20} {col[2]:10}")
                print("-" * 60)
            else:
                print("✗ Warning: Table creation reported success but table not found.")
            
            cursor.close()
    
    except Error as e:
        print(f"✗ Error during migration: {e}")
        if connection:
            connection.rollback()
    
    finally:
        if connection and connection.is_connected():
            connection.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    print("=" * 60)
    print("Pet Vaccinations Table Migration")
    print("=" * 60)
    print()
    
    run_migration()
    
    print()
    print("=" * 60)
    print("Migration complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Install WeasyPrint: pip install -r requirements.txt")
    print("2. Restart Flask: python app.py")
    print("3. Login and test vaccination management")
    print()
