"""
Test database connection for Doctor-Patient app
This app now uses existing pces_users and patient tables
No table initialization needed
"""
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.database import get_db


def test_connection():
    """Test database connection and verify tables exist"""
    print("🔍 Testing database connection...")
    
    try:
        db = get_db()
        conn = db.db.get_connection()
        cursor = conn.cursor()
        
        # Test connection
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✓ Connected to PostgreSQL")
        print(f"  Version: {version[:50]}...")
        
        # Check if pces_users table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'pces_users'
            )
        """)
        pces_users_exists = cursor.fetchone()[0]
        
        # Check if patient table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'patient'
            )
        """)
        patient_exists = cursor.fetchone()[0]
        
        print("\n📊 Table Status:")
        print(f"  pces_users table: {'✓ EXISTS' if pces_users_exists else '❌ NOT FOUND'}")
        print(f"  patient table: {'✓ EXISTS' if patient_exists else '❌ NOT FOUND'}")
        
        if pces_users_exists:
            cursor.execute("SELECT COUNT(*) FROM pces_users")
            count = cursor.fetchone()[0]
            print(f"  pces_users records: {count}")
        
        if patient_exists:
            cursor.execute("SELECT COUNT(*) FROM patient")
            count = cursor.fetchone()[0]
            print(f"  patient records: {count}")
        
        # Test search functionality
        print("\n🔎 Testing search functionality...")
        
        if pces_users_exists:
            test_doctors = db.search_doctors("a")
            print(f"  Doctor search test: Found {len(test_doctors)} results")
            if test_doctors:
                print(f"  Example: {test_doctors[0]['full_name']}")
        
        if patient_exists:
            test_patients = db.search_patients("a")
            print(f"  Patient search test: Found {len(test_patients)} results")
            if test_patients:
                print(f"  Example: {test_patients[0]['full_name']}")
        
        cursor.close()
        
        if pces_users_exists and patient_exists:
            print("\n✅ Database is ready to use!")
            print("   The app will search existing pces_users and patient tables.")
            return True
        else:
            print("\n⚠️  Required tables not found!")
            print("   Please ensure pces_users and patient tables exist.")
            return False
        
    except Exception as e:
        print(f"❌ Connection or test failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("  Doctor-Patient App - Database Connection Test")
    print("=" * 60)
    print()
    print("This app uses existing database tables:")
    print("  • pces_users (for doctors)")
    print("  • patient (for patients)")
    print()
    
    if test_connection():
        print("\n✓ You can now run the application:")
        print("  python backend/main.py")
    else:
        print("\n⚠️  Please check your database configuration")
        print("  Verify .env file settings and table existence")
        sys.exit(1)
