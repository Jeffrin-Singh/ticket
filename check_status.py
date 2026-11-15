"""
check_status.py - Quick status checker for Tirupati booking logins and families.
Usage: python check_status.py
"""
import sys
import os
import pandas as pd

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Sync latest from database if available
try:
    import sync_db_to_excel
    sync_db_to_excel.sync()
except Exception:
    pass

print("\n" + "=" * 70)
print("📊 TIRUPATI BOOKING STATUS REPORT")
print("=" * 70)

# 1. Family Groups Status
if os.path.exists("pilgrims_details.xlsx"):
    try:
        df_p = pd.read_excel("pilgrims_details.xlsx")
        print("\n👨‍👩‍👧‍👦 FAMILY GROUPS:")
        for _, row in df_p.iterrows():
            status = str(row.get("Status", "PENDING")).strip().upper()
            status_icon = "✅ PASSED" if status == "PASSED" else "⏳ PENDING"
            print(f"  • Group: {row.get('Group')} | Pilgrim: {row.get('name')} | Aadhaar: {row.get('id_number')} | Status: {status_icon}")
    except Exception as e:
        print(f"  Error reading pilgrims: {e}")

# 2. Login Accounts Status
if os.path.exists("user_details.xlsx"):
    try:
        df_u = pd.read_excel("user_details.xlsx")
        print("\n🔑 LOGIN ACCOUNTS:")
        passed_logins = []
        active_logins = []
        for idx, row in df_u.iterrows():
            email = row.get("Login_Email")
            status = str(row.get("Status", "ACTIVE")).strip().upper()
            if status == "PASSED":
                passed_logins.append(email)
            else:
                active_logins.append(email)

        if passed_logins:
            print("  🏆 SUCCESSFUL LOGINS (PASSED):")
            for em in passed_logins:
                print(f"     ✅ {em}")
        else:
            print("  ℹ️ No logins currently marked as PASSED.")

        print(f"\n  💤 STANDBY / ACTIVE LOGINS ({len(active_logins)} available):")
        for em in active_logins:
            print(f"     ⚪ {em}")

        print(f"\nSummary: {len(passed_logins)} PASSED | {len(active_logins)} ACTIVE")
    except Exception as e:
        print(f"  Error reading logins: {e}")

# 3. Successful Bookings Log (from successful_bookings.xlsx)
try:
    import record_success
    record_success.sync_success_from_db()
except Exception:
    pass

if os.path.exists("successful_bookings.xlsx"):
    try:
        df_succ = pd.read_excel("successful_bookings.xlsx")
        if not df_succ.empty:
            print("\n📋 SUCCESSFUL BOOKINGS HISTORY (from successful_bookings.xlsx):")
            for _, r in df_succ.iterrows():
                b_date = r.get("Date", "")
                b_time = r.get("Time", "")
                b_fam = r.get("Family", "")
                b_em = r.get("Email", "")
                b_pil = r.get("Pilgrims", "")
                print(f"  🎉 [{b_date} {b_time}] Family: {b_fam} | Login: {b_em} | Pilgrim: {b_pil}")
    except Exception as e:
        print(f"  Error reading successful_bookings.xlsx: {e}")

print("=" * 70 + "\n")

