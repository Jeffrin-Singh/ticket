"""
record_success.py - Records successful bookings (Family, Email, Date, Pilgrims) into successful_bookings.xlsx
"""
import os
import sys
import datetime
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

DB_NAME = "padmavathi_travels"
DB_USER = "postgres"
DB_PASSWORD = "Jeffrin@29072004"
DB_HOST = "localhost"
DB_PORT = 5432

SUCCESS_EXCEL_FILE = "successful_bookings.xlsx"

def get_db_connection():
    try:
        return psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
    except Exception:
        return None

def fetch_family_details(group_name):
    """Fetch pilgrim names, Aadhaar numbers, and payment UPI ID for a family group."""
    pilgrims_list = []
    aadhaar_list = []
    upi_id = ""

    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            # 1. Fetch pilgrims
            cur.execute("""
                SELECT p.full_name, p.name, p.aadhar_number, p.id_number
                FROM family_groups fg
                JOIN pilgrims p ON fg.id = p.group_id
                WHERE LOWER(fg.group_name) = LOWER(%s)
                ORDER BY p.id ASC;
            """, (str(group_name).strip(),))
            rows = cur.fetchall()
            for r in rows:
                p_name = r.get("full_name") or r.get("name") or ""
                p_id = r.get("aadhar_number") or r.get("id_number") or ""
                if p_name:
                    pilgrims_list.append(str(p_name).strip())
                if p_id:
                    aadhaar_list.append(str(p_id).strip())

            # 2. Fetch UPI ID if available
            cur.execute("""
                SELECT upi_id FROM payments pay
                JOIN family_groups fg ON pay.group_id = fg.id
                WHERE LOWER(fg.group_name) = LOWER(%s) LIMIT 1;
            """, (str(group_name).strip(),))
            p_row = cur.fetchone()
            if p_row and p_row.get("upi_id"):
                upi_id = str(p_row.get("upi_id")).strip()

            cur.close()
            conn.close()
        except Exception:
            pass

    # Fallback to pilgrims_details.xlsx
    if not pilgrims_list and os.path.exists("pilgrims_details.xlsx"):
        try:
            df_p = pd.read_excel("pilgrims_details.xlsx")
            matched = df_p[df_p["Group"].astype(str).str.lower() == str(group_name).strip().lower()]
            for _, r in matched.iterrows():
                p_name = str(r.get("name", "")).strip()
                p_id = str(r.get("id_number", "")).strip()
                if p_name and p_name.lower() != "nan":
                    pilgrims_list.append(p_name)
                if p_id and p_id.lower() != "nan":
                    aadhaar_list.append(p_id)
        except Exception:
            pass

    return ", ".join(pilgrims_list), ", ".join(aadhaar_list), upi_id

def record_successful_booking(email, group, booking_datetime=None, status="PASSED", notes=""):
    """
    Saves/appends the successful booking record (family, email, date) to successful_bookings.xlsx.
    Avoids duplicate entries for the same group, email, and date.
    """
    now = booking_datetime or datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

    email = str(email).strip()
    group = str(group).strip()
    status = str(status).strip().upper()

    pilgrims_str, aadhaars_str, upi_id = fetch_family_details(group)

    new_row = {
        "Date": date_str,
        "Time": time_str,
        "Family": group,
        "Email": email,
        "Pilgrims": pilgrims_str,
        "Aadhaar_Numbers": aadhaars_str,
        "UPI_ID": upi_id,
        "Status": status,
        "Timestamp": timestamp_str
    }

    cols = ["Date", "Time", "Family", "Email", "Pilgrims", "Aadhaar_Numbers", "UPI_ID", "Status", "Timestamp"]

    df = pd.DataFrame()
    if os.path.exists(SUCCESS_EXCEL_FILE):
        try:
            df = pd.read_excel(SUCCESS_EXCEL_FILE)
        except Exception as e:
            print(f"⚠️ Warning reading {SUCCESS_EXCEL_FILE}: {e}")
            df = pd.DataFrame()

    if not df.empty and "Date" in df.columns and "Family" in df.columns:
        # Check if already recorded today for this group and email
        mask = (
            (df["Date"].astype(str) == date_str) &
            (df["Family"].astype(str).str.lower() == group.lower()) &
            (df["Email"].astype(str).str.lower() == email.lower())
        )
        if mask.any():
            idx = df[mask].index[0]
            for k, v in new_row.items():
                df.at[idx, k] = v
            print(f"🔄 Updated existing record in {SUCCESS_EXCEL_FILE} for {group} ({email}) on {date_str}")
        else:
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            print(f"🎉 Recorded new successful booking in {SUCCESS_EXCEL_FILE}: {group} | {email} | {date_str}")
    else:
        df = pd.DataFrame([new_row], columns=cols)
        print(f"🎉 Created {SUCCESS_EXCEL_FILE} with successful booking: {group} | {email} | {date_str}")

    # Ensure column ordering
    available_cols = [c for c in cols if c in df.columns]
    other_cols = [c for c in df.columns if c not in cols]
    df = df[available_cols + other_cols]

    try:
        df.to_excel(SUCCESS_EXCEL_FILE, index=False)
        print(f"✅ Saved {SUCCESS_EXCEL_FILE} successfully.")
    except PermissionError:
        backup_file = f"successful_bookings_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        print(f"⚠️ {SUCCESS_EXCEL_FILE} is open in Excel! Saving backup to {backup_file}")
        try:
            df.to_excel(backup_file, index=False)
        except Exception as ex:
            print(f"❌ Failed to write backup: {ex}")
    except Exception as e:
        print(f"❌ Error writing to {SUCCESS_EXCEL_FILE}: {e}")

    return df

def sync_success_from_db():
    """Scans database and lock files to record any passed families that aren't yet saved in successful_bookings.xlsx."""
    # 1. Check lock files in ready/
    ready_dir = os.path.join(os.getcwd(), "ready")
    recorded = 0
    if os.path.exists(ready_dir):
        for fname in os.listdir(ready_dir):
            if fname.endswith("_paynow.lock") or fname.endswith("_payment.lock"):
                grp = fname.split("_")[0]
                try:
                    with open(os.path.join(ready_dir, fname), "r") as lf:
                        content = lf.read().strip()
                    winner_email = content.split("_")[0]
                    if winner_email and "@" in winner_email:
                        record_successful_booking(winner_email, grp)
                        recorded += 1
                except Exception:
                    pass

    # 2. Check PostgreSQL database for PASSED families
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT fg.group_name, fg.updated_at, fg.status 
                FROM family_groups fg 
                WHERE fg.status = 'PASSED';
            """)
            passed_groups = cur.fetchall()

            cur.execute("""
                SELECT email, last_used_at FROM logins WHERE status = 'PASSED';
            """)
            passed_logins = cur.fetchall()

            # Pair passed families with passed logins if lock wasn't available
            if passed_groups and passed_logins:
                for idx, grp in enumerate(passed_groups):
                    grp_name = grp["group_name"]
                    login_email = passed_logins[idx % len(passed_logins)]["email"]
                    b_dt = grp.get("updated_at") or datetime.datetime.now()
                    record_successful_booking(login_email, grp_name, booking_datetime=b_dt)
                    recorded += 1

            cur.close()
            conn.close()
        except Exception as e:
            print(f"⚠️ Error querying database: {e}")

    return recorded

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("📋 SUCCESSFUL BOOKINGS HISTORY TRACKER")
    print("=" * 70)
    sync_success_from_db()
    if os.path.exists(SUCCESS_EXCEL_FILE):
        try:
            df = pd.read_excel(SUCCESS_EXCEL_FILE)
            print(f"\n📖 Current records in {SUCCESS_EXCEL_FILE} ({len(df)} total):\n")
            print(df.to_string(index=False))
        except Exception as e:
            print(f"Error reading file: {e}")
    else:
        print(f"\nℹ️ No {SUCCESS_EXCEL_FILE} created yet. It will be automatically generated upon your next successful booking!")
    print("\n" + "=" * 70 + "\n")

