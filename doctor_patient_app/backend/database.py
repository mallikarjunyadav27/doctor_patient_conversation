"""
Database models and connection for Doctor-Patient app
Uses existing pces_users and patient tables
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()


class Database:
    """Database connection handler"""
    
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Establish connection to PostgreSQL"""
        try:
            self.connection = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                database=os.getenv("DB_NAME", "pces_base"),
                user=os.getenv("DB_USER", "pcesuser"),
                password=os.getenv("DB_PASSWORD")
            )
            print("✓ Database connected successfully")
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            raise
    
    def get_connection(self):
        """Get database connection"""
        if self.connection is None or self.connection.closed:
            self.connect()
        return self.connection
    
    def close(self):
        """Close database connection"""
        if self.connection and not self.connection.closed:
            self.connection.close()
            print("✓ Database connection closed")


class DoctorPatientDB:
    """Database operations for doctors and patients using existing tables"""
    
    def __init__(self):
        self.db = Database()
    
    def search_doctors(self, query: str) -> List[Dict]:
        """
        Search for doctors by first_name and last_name from pces_users table.
        Returns matching doctors based on partial input.
        """
        try:
            if not query or not query.strip():
                return []
            
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            search_pattern = f"%{query.strip().lower()}%"
            
            cursor.execute("""
                SELECT DISTINCT first_name, last_name 
                FROM pces_users 
                WHERE LOWER(first_name) LIKE %s 
                   OR LOWER(last_name) LIKE %s 
                   OR LOWER(CONCAT(first_name, ' ', last_name)) LIKE %s
                ORDER BY first_name, last_name
                LIMIT 10
            """, (search_pattern, search_pattern, search_pattern))
            
            results = cursor.fetchall()
            cursor.close()
            
            doctors = []
            for row in results:
                if row['first_name'] and row['last_name']:
                    full_name = f"{row['first_name']} {row['last_name']}"
                    doctors.append({
                        "first_name": row['first_name'],
                        "last_name": row['last_name'],
                        "full_name": full_name
                    })
            
            return doctors
            
        except Exception as e:
            print(f"Error searching doctors: {e}")
            return []
    
    def search_patients(self, query: str) -> List[Dict]:
        """
        Search for patients by first_name and last_name from patient table.
        Returns matching patients based on partial input.
        """
        try:
            if not query or not query.strip():
                return []
            
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            search_pattern = f"%{query.strip().lower()}%"
            
            cursor.execute("""
                SELECT DISTINCT patient_id, first_name, last_name 
                FROM patient 
                WHERE LOWER(first_name) LIKE %s 
                   OR LOWER(last_name) LIKE %s 
                   OR LOWER(CONCAT(first_name, ' ', last_name)) LIKE %s
                ORDER BY first_name, last_name
                LIMIT 10
            """, (search_pattern, search_pattern, search_pattern))
            
            results = cursor.fetchall()
            cursor.close()
            
            patients = []
            for row in results:
                if row['first_name'] and row['last_name']:
                    full_name = f"{row['first_name']} {row['last_name']}"
                    patients.append({
                        "patient_id": row['patient_id'],
                        "first_name": row['first_name'],
                        "last_name": row['last_name'],
                        "full_name": full_name
                    })
            
            return patients
            
        except Exception as e:
            print(f"Error searching patients: {e}")
            return []
    
    def save_conversation(self, doctor_name: str, patient_id: int, 
                         patient_name: str, conversation_data: Dict, file_path: str):
        """Save conversation record to database - uses doctor name and patient ID"""
        cursor = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Try to create conversations table if it doesn't exist
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS doctor_patient_conversations (
                        id SERIAL PRIMARY KEY,
                        doctor_name VARCHAR(255),
                        patient_id INTEGER,
                        patient_name VARCHAR(255),
                        conversation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        doctor_language VARCHAR(10),
                        patient_language VARCHAR(10),
                        file_path TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
            except psycopg2.errors.InsufficientPrivilege:
                # User doesn't have CREATE TABLE permission, rollback and check if table exists
                conn.rollback()
                cursor.close()
                cursor = conn.cursor()  # Get new cursor after rollback
                
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'doctor_patient_conversations'
                    )
                """)
                table_exists = cursor.fetchone()[0]
                if not table_exists:
                    print("⚠️ Cannot create table and table doesn't exist. Skipping database save.")
                    cursor.close()
                    return None
            except Exception as other_error:
                # Any other error, rollback and continue
                conn.rollback()
                cursor.close()
                cursor = conn.cursor()  # Get new cursor after rollback
            
            cursor.execute("""
                INSERT INTO doctor_patient_conversations 
                (doctor_name, patient_id, patient_name, conversation_date, 
                 doctor_language, patient_language, file_path)
                VALUES (%s, %s, %s, NOW(), %s, %s, %s)
                RETURNING id
            """, (
                doctor_name,
                patient_id,
                patient_name,
                conversation_data.get('doctor_lang', 'en'),
                conversation_data.get('patient_lang', 'en'),
                file_path
            ))
            
            conversation_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            
            print(f"✓ Conversation saved to database (ID: {conversation_id})")
            return conversation_id
            
        except Exception as e:
            print(f"Error saving conversation: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.rollback()
            except Exception as rollback_error:
                print(f"Error during rollback: {rollback_error}")
            finally:
                try:
                    if cursor:
                        cursor.close()
                except:
                    pass
            return None
    
    def close(self):
        """Close database connection"""
        self.db.close()


# Singleton instance
_db_instance = None

def get_db() -> DoctorPatientDB:
    """Get database instance (singleton)"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DoctorPatientDB()
    return _db_instance
