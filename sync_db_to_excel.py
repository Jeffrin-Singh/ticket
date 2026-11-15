import sys
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import os

DB_NAME = "padmavathi_travels"
DB_USER = "postgres"
DB_PASSWORD = "Jeffrin@29072004"
DB_HOST = "localhost"
DB_PORT = 5432

def sync():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1. Export logins
    cur.execute('SELECT email AS "Login_Email", password, status AS "Status" FROM logins ORDER BY id ASC;')
    u_rows = cur.fetchall()
    if u_rows:
        u_df = pd.DataFrame(u_rows)
        # Ensure Status column is string type to accept 'PASSED'/'FAILED'
        u_df['Status'] = u_df['Status'].astype(str)
        u_df.to_excel('user_details.xlsx', index=False)
        print(f"✅ Synced {len(u_df)} login(s) to user_details.xlsx")
        print(u_df)

    # 2. Export pilgrims
    cur.execute('''
        SELECT fg.group_name AS "Group", 
               COALESCE(p.name, p.full_name) AS "name", 
               p.age, 
               p.gender, 
               COALESCE(p.id_type, 'Aadhaar Card') AS "id_type", 
               COALESCE(p.id_number, p.aadhar_number) AS "id_number", 
               fg.status AS "Status"
        FROM family_groups fg
        JOIN pilgrims p ON fg.id = p.group_id
        ORDER BY fg.id ASC, p.id ASC;
    ''')
    p_rows = cur.fetchall()
    if p_rows:
        p_df = pd.DataFrame(p_rows)
        p_df['Time'] = ""
        # Ensure Status column is string type to accept 'PASSED'/'FAILED'
        p_df['Status'] = p_df['Status'].astype(str)
        p_df.to_excel('pilgrims_details.xlsx', index=False)
        print(f"✅ Synced {len(p_df)} pilgrim(s) to pilgrims_details.xlsx")
        print(p_df)

    conn.close()

if __name__ == '__main__':
    sync()
