import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import os

# Credentials
DB_NAME = "padmavathi_travels"
DB_USER = "postgres"
DB_PASSWORD = "Jeffrin@29072004"
DB_HOST = "localhost"
DB_PORT = "5432"

def test_db():
    print("Connecting to PostgreSQL...")
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.autocommit = True
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        print("Connected successfully!")
        
        # 1. Run the schema if tables don't exist
        print("\nSetting up schema...")
        schema_path = os.path.join(os.path.dirname(__file__), "postgres_schema.sql")
        if not os.path.exists(schema_path):
            schema_path = "postgres_schema.sql"
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
                cursor.execute("SELECT to_regclass('public.family_groups');")
                if cursor.fetchone()['to_regclass'] is None:
                    print("Tables not found. Creating from postgres_schema.sql...")
                    cursor.execute(schema_sql)
                    print("Tables created.")
                else:
                    print("Tables already exist.")
        
        # 2. Insert Test Data
        print("\nWriting test data to 'family_groups'...")
        cursor.execute("""
            INSERT INTO family_groups (group_name, status, payment_method) 
            VALUES ('TEST_FAMILY_1', 'PENDING', 'UPI')
            ON CONFLICT (group_name) DO UPDATE SET status = 'PENDING';
        """)
        
        cursor.execute("""
            INSERT INTO logins (email, password, status) 
            VALUES ('test@example.com', 'password123', 'ACTIVE')
            ON CONFLICT (email) DO NOTHING;
        """)
        print("Test data written successfully.")
        
        # 3. Read Data
        print("\nReading data from 'family_groups'...")
        cursor.execute("SELECT * FROM family_groups;")
        rows = cursor.fetchall()
        for row in rows:
            print(f" -> Found Group: {row['group_name']} | Status: {row['status']} | Payment: {row['payment_method']}")
            
        print("\nReading data from 'logins'...")
        cursor.execute("SELECT * FROM logins;")
        login_rows = cursor.fetchall()
        for row in login_rows:
            print(f" -> Found Login: {row['email']} | Status: {row['status']}")

        cursor.close()
        conn.close()
        print("\nTest completed successfully!")

    except Exception as e:
        print(f"Error during test: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_db()
