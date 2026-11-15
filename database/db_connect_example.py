import psycopg2
import pandas as pd
from sqlalchemy import create_engine

# =========================================================
# Configuration - Update these with your pgAdmin 4 details
# =========================================================
DB_NAME = "padmavathi_travels"
DB_USER = "postgres"           # Default user is usually 'postgres'
DB_PASSWORD = "Jeffrin@29072004"  # The password you set in pgAdmin
DB_HOST = "localhost"          # Running on your own computer
DB_PORT = "5432"               # Default PostgreSQL port

# =========================================================
# Method 1: Using Pandas (Easiest way to replace read_excel)
# =========================================================
def read_from_db_with_pandas():
    print("--- Method 1: Pandas ---")
    # SQLAlchemy engine is required by Pandas for PostgreSQL
    engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
    
    try:
        # Instead of pd.read_excel('pilgrims_details.xlsx')
        query = "SELECT * FROM family_groups WHERE status != 'PASSED';"
        pilgrims_df = pd.read_sql(query, engine)
        
        print("Successfully loaded data from PostgreSQL!")
        print(pilgrims_df.head())
    except Exception as e:
        print(f"Error connecting: {e}")

# =========================================================
# Method 2: Direct Connection (Best for updating data)
# =========================================================
def update_db_status(group_name, new_status):
    print("\n--- Method 2: Direct Update ---")
    try:
        # Connect directly to the database
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        # Update a family's status to 'PASSED'
        update_query = "UPDATE family_groups SET status = %s WHERE group_name = %s"
        cursor.execute(update_query, (new_status, group_name))
        
        conn.commit()  # VERY IMPORTANT: Saves the changes!
        print(f"Successfully updated {group_name} to {new_status}")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error updating: {e}")

if __name__ == "__main__":
    # You need to install these first:
    # pip install psycopg2-binary pandas sqlalchemy
    
    # read_from_db_with_pandas()
    # update_db_status('Family_A', 'PASSED')
    pass

