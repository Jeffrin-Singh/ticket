"""
launcher.py - reads Excel, assigns users to families, launches up to MAX_WORKERS sequentially.
Each worker uses its own PowerShell console, isolated undetected_chromedriver cache, and Chrome profile.
"""

import sys
import os

# Fix Windows cp1252 UnicodeEncodeError for emojis/unicode output
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import pandas as pd
import subprocess
import itertools
import time
import shutil
import psutil
import ctypes

# -------------------- CONFIGURATION --------------------
MAX_WORKERS = 100         # Maximum number of concurrent browsers to launch
CLEAN_CACHE_AT_START = True   # Delete old cache folders before starting
LAUNCH_DELAY = 0.2         # seconds between worker spawns (near-instant parallel launch)

# -------------------- BROWSER ASSIGNMENT --------------------
# Standardized to stable bundled Chromium to prevent Chrome auto-update driver mismatches.
# Any worker index listed here overrides the default (chromium).
BROWSER_ASSIGNMENTS = {
    # Optional per-worker overrides: e.g. 0: "chrome"
}
# -----------------------------------------------------------

def is_admin():
    """Check if running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() == 1
    except Exception:
        return False

def relaunch_elevated(mode):
    """Relaunch launcher.py with admin privileges in the specified mode.
    
    Args:
        mode: "cleanup" to run only cleanup, "normal" to run full launcher
    """
    script = os.path.abspath(__file__)
    py_exe = sys.executable
    cmd = f'"{py_exe}" "{script}" --mode {mode}'
    
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", f"/c {cmd}", None, 1)
        return True
    except Exception as e:
        print(f"❌ Failed to elevate: {e}")
        return False

def terminate_stale_browser_processes(timeout_seconds=30):
    """Terminate any stale chrome.exe or chromedriver.exe processes before launch."""
    stale_names = ["chrome.exe", "chromedriver.exe"]
    print(f"🧹 Killing stale Chrome/Driver processes before launch...")

    for proc_name in stale_names:
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", proc_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception as exc:
            print(f"⚠️ Failed to stop {proc_name}: {exc}")

    deadline = time.monotonic() + timeout_seconds
    remaining = True
    while time.monotonic() < deadline:
        alive = []
        for proc in psutil.process_iter(attrs=['name']):
            try:
                name = (proc.info.get('name') or '').lower()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if name in {"chrome.exe", "chromedriver.exe"}:
                alive.append(name)
        if not alive:
            remaining = False
            break
        time.sleep(0.5)

    if remaining:
        print("⚠️ Some Chrome/Driver processes are still alive after timeout; continuing anyway.")
        return False

    print("✅ All stale Chrome/Driver processes terminated before launch.")
    return True

def clean_cache_dirs():
    """Remove only stale startup artifacts; do not delete project folders or useful data."""
    project_root = os.getcwd()
    target_dirs = ["undetected_cache", "sessions", "ready", "otp_requests"]
    cleaned_any = False
    safety_issues = []

    print(f"🧹 Starting safe startup cleanup in: {project_root}")
    if is_admin():
        print("🛡️ Administrator privileges detected. Running elevated-safe cleanup path.")
    else:
        print("ℹ️ Not running elevated; continuing with standard cleanup.")

    for folder in target_dirs:
        path = os.path.join(project_root, folder)
        if not os.path.exists(path):
            continue

        try:
            for entry in os.listdir(path):
                full_path = os.path.join(path, entry)
                lower_name = entry.lower()
                try:
                    if os.path.isfile(full_path) and (
                        lower_name.endswith((".tmp", ".lock", ".pid", ".log", ".ready", ".json", ".png"))
                    ):
                        os.remove(full_path)
                        cleaned_any = True
                        print(f"   Removed stale startup artifact: {full_path}")
                    elif os.path.isdir(full_path) and folder in {"undetected_cache", "sessions"}:
                        # Do not wipe driver binaries; only remove stale temp/cache artifacts inside them.
                        for subentry in os.listdir(full_path):
                            sub_path = os.path.join(full_path, subentry)
                            sub_lower = subentry.lower()
                            if os.path.isfile(sub_path) and (
                                sub_lower.endswith((".tmp", ".lock", ".pid", ".log"))
                            ):
                                os.remove(sub_path)
                                cleaned_any = True
                                print(f"   Removed stale browser artifact: {sub_path}")
                except Exception as exc:
                    safety_issues.append(f"{full_path}: {exc}")
        except Exception as exc:
            safety_issues.append(f"{path}: {exc}")

    project_root_files = [
        "debug_ocr",
        "New Text Document.txt",
    ]
    for item_name in project_root_files:
        item_path = os.path.join(project_root, item_name)
        if not os.path.exists(item_path):
            continue
        try:
            if os.path.isfile(item_path) and item_name.lower().endswith((".tmp", ".lock", ".pid", ".log")):
                os.remove(item_path)
                cleaned_any = True
                print(f"   Removed stale root temp file: {item_path}")
        except Exception as exc:
            safety_issues.append(f"{item_path}: {exc}")

    if safety_issues:
        print("⚠️ Startup cleanup had non-fatal issues:")
        for issue in safety_issues[:5]:
            print(f"   - {issue}")

    if cleaned_any:
        print("✅ Safe startup cleanup completed.")
    else:
        print("ℹ️ No stale startup artifacts were removed.")

    return True

def wait_for_worker_ready(group, idx, timeout=60):
    ready_file = os.path.join(os.getcwd(), "ready", f"{group}_{idx}.ready")
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(ready_file):
            return True
        time.sleep(0.5)
    return False

def main():
    startup_start = time.perf_counter()
    # ============================================================
    # PHASE 0: Elevation Check and Cleanup Orchestration
    # ============================================================
    
    # Parse --mode flag if present
    mode = "normal"  # default mode: full launcher flow
    if len(sys.argv) > 1 and sys.argv[1] == "--mode" and len(sys.argv) > 2:
        mode = sys.argv[2]
    
    print(f"🚀 Launcher mode: {mode}")
    elevated = is_admin()
    print(f"🛡️  Process elevated: {elevated}")
    
    # ============================================================
    # PHASE 1: Cleanup Phase (Elevated)
    # ============================================================
    
    if mode == "cleanup":
        # Elevated cleanup-only mode: run cleanup and exit
        print("\n" + "="*60)
        print("ELEVATED CLEANUP PHASE")
        print("="*60)
        cleanup_start = time.perf_counter()
        try:
            print("✓ Elevated cleanup running...")
            clean_cache_dirs()
            print("✓ Terminating stale browser processes...")
            terminate_stale_browser_processes()
            cleanup_time = time.perf_counter() - cleanup_start
            print(f"✅ Elevated cleanup completed in {cleanup_time:.2f}s")
        except Exception as exc:
            print(f"⚠️ Elevated cleanup failed: {exc}")
        print("🔄 Exiting elevated process...")
        sys.exit(0)
    
    # Normal mode: ensure all stale browser processes and locks are cleaned immediately
    if mode == "normal":
        print("\n" + "="*60)
        print("PRE-LAUNCH CLEANUP")
        print("="*60)
        try:
            cleanup_start = time.perf_counter()
            terminate_stale_browser_processes(timeout_seconds=5)
            clean_cache_dirs()
            print(f"⏱️  Startup cleanup finished in {time.perf_counter() - cleanup_start:.2f}s")
        except Exception as exc:
            print(f"⚠️ Startup cleanup warning: {exc}")

    # ============================================================
    # PHASE 2: Normal Launcher Flow (Non-elevated)
    # ============================================================
    
    print("\n" + "="*60)
    print("LAUNCHER STARTUP PHASE (Normal Privileges)")
    print("="*60)

    # Check target booking time vs current IST
    try:
        import datetime
        timing_file = os.path.join(os.getcwd(), "timing_config.json")
        if os.path.exists(timing_file):
            import json
            with open(timing_file, "r") as tf:
                tdata = json.load(tf)
            thour = int(tdata.get("TARGET_BOOKING_HOUR", 9))
            tmin = int(tdata.get("TARGET_BOOKING_MINUTE", 3))
            tsec = int(tdata.get("TARGET_BOOKING_SECOND", 0))
            now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5.5)
            target_dt = now_ist.replace(hour=thour, minute=tmin, second=tsec, microsecond=0)
            diff = (target_dt - now_ist).total_seconds()
            if diff < -30:
                print(f"⚠️  CRITICAL TIMING WARNING: Current IST time is {now_ist.strftime('%H:%M:%S')}.")
                print(f"   Target slot release was {thour:02d}:{tmin:02d}:{tsec:02d} IST ({int(abs(diff))}s ago).")
                print(f"   Daily Srivani quota usually exhausts in 20-30s! Launching now to attempt booking anyway...\n")
            elif diff > 0:
                print(f"⏰ Target booking time: {thour:02d}:{tmin:02d}:{tsec:02d} IST (in {int(diff//60)}m {int(diff%60)}s). Standing by...\n")
    except Exception:
        pass

    # Sync from PostgreSQL database if available
    try:
        import sync_db_to_excel
        sync_db_to_excel.sync()
    except Exception as e:
        print(f"ℹ️ (Using existing Excel files: {e})")

    try:
        user_df = pd.read_excel('user_details.xlsx')
        user_df = user_df.dropna(subset=['Login_Email'])
        user_df = user_df[user_df['Login_Email'].str.strip() != '']
        if 'Status' in user_df.columns:
            user_df = user_df[user_df['Status'].fillna('').astype(str).str.strip().str.upper() != 'PASSED']
        user_df = user_df.dropna(subset=['password'])
        logins = list(zip(user_df['Login_Email'], user_df['password']))
        if not logins:
            print("❌ No valid active logins found in user_details.xlsx")
            sys.exit(1)
        print(f"✅ Found {len(logins)} active login(s): {[email for email, _ in logins]}")
    except Exception as e:
        print(f"❌ Error reading user_details.xlsx: {e}")
        sys.exit(1)

    try:
        pilgrims_df = pd.read_excel('pilgrims_details.xlsx', dtype={'Group': str})
        pilgrims_df['Group'] = pilgrims_df['Group'].astype(str).str.strip()
        if 'Status' in pilgrims_df.columns:
            pilgrims_df = pilgrims_df[pilgrims_df['Status'].fillna('').astype(str).str.strip().str.upper() != 'PASSED']
        groups_raw = pilgrims_df['Group'].unique()
        unique_groups = [g for g in groups_raw if g and g != 'nan' and g != '']
        if not unique_groups:
            print("❌ No active groups found after cleaning.")
            sys.exit(1)
        
        # Check timing_config.json for BROWSERS_PER_FAMILY setting (default 1)
        timing_file = os.path.join(os.getcwd(), "timing_config.json")
        browsers_per_family = 1
        show_browser_cfg = True
        max_workers_cfg = MAX_WORKERS
        launch_delay_cfg = LAUNCH_DELAY
        if os.path.exists(timing_file):
            try:
                import json
                with open(timing_file, "r") as tf:
                    tdata = json.load(tf)
                    browsers_per_family = max(1, int(tdata.get("BROWSERS_PER_FAMILY", 1)))
                    show_browser_cfg = bool(tdata.get("SHOW_BROWSER", True))
                    if "MAX_WORKERS" in tdata:
                        max_workers_cfg = max(1, int(tdata["MAX_WORKERS"]))
                    if "LAUNCH_DELAY" in tdata:
                        launch_delay_cfg = float(tdata["LAUNCH_DELAY"])
            except Exception:
                pass

        # Expand groups based on requested browsers_per_family (interleaved round-robin)
        raw_groups = []
        for _ in range(browsers_per_family):
            for g in unique_groups:
                raw_groups.append(g)

        # CRITICAL SAFETY: TTD only allows ONE active session per login account.
        # Reusing the same login email across concurrent workers immediately revokes the previous session,
        # redirecting the browser back to #/userLogin and failing payment.
        # Therefore, we NEVER launch more concurrent workers than available unique logins!
        effective_max = max(max_workers_cfg, len(raw_groups))
        total_workers = min(len(raw_groups), len(logins), effective_max)
        groups = raw_groups[:total_workers]
        assigned_logins = logins[:total_workers]

        if len(raw_groups) > len(logins):
            print(f"⚠️ Notice: Requested {len(raw_groups)} worker(s), but only {len(logins)} unique login(s) available in user_details.xlsx.")
            print(f"   Each browser worker MUST have a separate login to prevent TTD session kick-outs.")
            print(f"   Safely running {total_workers} worker(s) (1 worker per unique login).")
        else:
            print(f"✅ Launching {total_workers} worker(s) with dedicated 1:1 login accounts.")
    except Exception as e:
        print(f"❌ Error reading pilgrims_details.xlsx: {e}")
        sys.exit(1)

    print("\n🔗 Mapping:")
    for group, (email, pwd) in zip(groups, assigned_logins):
        print(f"   {group} -> {email}")

    # ============================================================
    # Deep clean startup folders before launching workers
    # ============================================================
    print("\n🧹 Deep cleaning startup folders: /ready, /sessions")
    for folder_name in ["ready", "sessions"]:
        folder_path = os.path.join(os.getcwd(), folder_name)
        if os.path.exists(folder_path):
            for entry in os.listdir(folder_path):
                entry_path = os.path.join(folder_path, entry)
                try:
                    if os.path.isfile(entry_path) or os.path.islink(entry_path):
                        os.unlink(entry_path)
                    elif os.path.isdir(entry_path):
                        shutil.rmtree(entry_path)
                except Exception as exc:
                    print(f"⚠️ Could not remove {entry_path}: {exc}")
            print(f"   ✅ Deleted contents of {folder_path}")
        else:
            os.makedirs(folder_path, exist_ok=True)
            print(f"   📁 Created missing folder: {folder_path}")
    print("✅ Deep clean completed.\n")
    # ============================================================

    os.makedirs("ready", exist_ok=True)
    os.makedirs("undetected_cache", exist_ok=True)

    # Pre-warm master Chrome driver & replicate isolated binaries to each worker
    try:
        import undetected_chromedriver as uc
        patcher = uc.Patcher()
        master_exe = os.path.join(patcher.data_path, "undetected_chromedriver.exe")
        if not os.path.exists(master_exe) or os.path.getsize(master_exe) < 1000000:
            print("🔧 Pre-warming master Chrome driver (one-time setup)...")
            patcher.auto()
            master_exe = patcher.executable_path

        if os.path.exists(master_exe) and os.path.getsize(master_exe) > 1000000:
            print(f"✅ Master Chrome driver ready: {master_exe}")
            for idx in range(len(groups)):
                worker_c_dir = os.path.join(os.getcwd(), "undetected_cache", f"worker_{idx}")
                os.makedirs(worker_c_dir, exist_ok=True)
                worker_c_exe = os.path.join(worker_c_dir, "chromedriver.exe")
                if not os.path.exists(worker_c_exe) or os.path.getsize(worker_c_exe) != os.path.getsize(master_exe):
                    try:
                        shutil.copy2(master_exe, worker_c_exe)
                    except Exception:
                        pass
            print(f"✅ Isolated Chrome drivers replicated to all {len(groups)} worker caches (0ms collision-free launch).\n")
    except Exception as drv_err:
        print(f"ℹ️ Driver pre-population note: {drv_err}\n")

    # Also replicate bundled Chromium driver if workers use chromium
    chromium_driver = os.path.join(os.getcwd(), "driver", "chromedriver.exe")
    if not os.path.exists(chromium_driver):
        chromium_driver = r"D:\next_slot\driver\chromedriver.exe"
    if os.path.exists(chromium_driver):
        for idx in range(len(groups)):
            worker_c_dir = os.path.join(os.getcwd(), "undetected_cache", f"worker_{idx}")
            os.makedirs(worker_c_dir, exist_ok=True)
            worker_c_exe = os.path.join(worker_c_dir, "chromedriver.exe")
            if not os.path.exists(worker_c_exe) or os.path.getsize(worker_c_exe) != os.path.getsize(chromium_driver):
                try:
                    shutil.copy2(chromium_driver, worker_c_exe)
                except Exception:
                    pass
        print(f"✅ Isolated Chromium drivers replicated to all {len(groups)} worker caches for parallel launch.\n")

    processes = []
    for idx, (group, (email, password)) in enumerate(zip(groups, assigned_logins)):
        print(f"\n🚀 Launching automation for group '{group}' with email {email} (worker #{idx+1})")

        cache_dir = os.path.join(os.getcwd(), "undetected_cache", f"worker_{idx}")
        os.makedirs(cache_dir, exist_ok=True)

        env = os.environ.copy()
        env['UNDETECTED_CHROMEDRIVER_CACHE_DIR'] = cache_dir

        # --- Browser selection: default to stable bundled chromium ---
        browser = BROWSER_ASSIGNMENTS.get(idx, "chromium")
        # -------------------------------------------------------------

        py_exe = sys.executable
        show_browser_arg = " --show-browser" if show_browser_cfg else ""
        cmd = [
            "powershell.exe",
            "-NoExit",
            "-Command",
            f'& "{py_exe}" worker.py --email {email} --password {password} --group {group} --excel pilgrims_details.xlsx --worker-id {idx} --browser {browser}{show_browser_arg}'
        ]
        print(f"   Command: {' '.join(cmd)}")
        print(f"   Cache dir: {cache_dir}")

        proc = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE, env=env)
        processes.append((proc, group, idx))
        if launch_delay_cfg > 0:
            time.sleep(launch_delay_cfg)

    print(f"\n🚀 All {len(processes)} browser workers launched in parallel!")
    print("⏳ Monitoring pre-flight login readiness across all workers...")

    # Non-blocking concurrent readiness check across all workers
    max_wait_ready = max(90, len(processes) * 25)
    all_ready_start = time.time()
    pending = list(processes)
    while pending and time.time() - all_ready_start < max_wait_ready:
        still_pending = []
        for proc, group, idx in pending:
            ready_file = os.path.join(os.getcwd(), "ready", f"{group}_{idx}.ready")
            if os.path.exists(ready_file):
                print(f"   ✅ Worker #{idx+1} ({group}) logged in and ready.")
            else:
                still_pending.append((proc, group, idx))
        pending = still_pending
        if pending:
            time.sleep(1.0)

    if not pending:
        print("\n🎉 ALL WORKERS LOGGED IN AND STANDING BY FOR BOOKING TIME!")
    else:
        print(f"\n⚠️ {len(pending)} worker(s) still initializing. Continuing anyway.")

    print("\nThey will run in separate PowerShell consoles. Press Ctrl+C to terminate all.")
    try:
        for proc, _, _ in processes:
            proc.wait()
    except KeyboardInterrupt:
        print("Terminating all workers...")
        for proc, _, _ in processes:
            proc.terminate()

    # ============================================================
    # Post-Booking Results & Winning Logins Summary
    # ============================================================
    print("\n" + "="*70)
    print("🏁 POST-BOOKING RESULTS & LOGIN ASSIGNMENT SUMMARY")
    print("="*70)
    ready_dir = os.path.join(os.getcwd(), "ready")
    confirmed_success = {}
    pending_payment = {}
    if os.path.exists(ready_dir):
        for fname in os.listdir(ready_dir):
            grp = fname.split("_")[0]
            if fname.endswith("_success.done"):
                try:
                    with open(os.path.join(ready_dir, fname), "r") as lf:
                        winner_email = lf.read().strip().split("_")[0]
                    confirmed_success[grp] = winner_email
                except Exception:
                    pass
            elif fname.endswith("_paynow.lock") or fname.endswith("_payment.lock"):
                try:
                    with open(os.path.join(ready_dir, fname), "r") as lf:
                        winner_email = lf.read().strip().split("_")[0]
                    pending_payment[grp] = winner_email
                except Exception:
                    pass

    if confirmed_success:
        for grp, winner_email in sorted(confirmed_success.items()):
            print(f"  🎉 [{grp}] BOOKING COMPLETED & PAYMENT CONFIRMED: {winner_email}")
            try:
                import record_success
                record_success.record_successful_booking(winner_email, grp)
            except Exception as e:
                print(f"  ⚠️ Could not record to successful_bookings.xlsx: {e}")
    elif pending_payment:
        for grp, winner_email in sorted(pending_payment.items()):
            print(f"  ℹ️ [{grp}] Payment submitted by {winner_email}, but final confirmation receipt was not captured. (Not recorded as PASSED)")
    else:
        print("  ℹ️ No active booking locks were detected.")

    try:
        import sync_db_to_excel
        sync_db_to_excel.sync()
    except Exception:
        pass
    print("="*70 + "\n")

    # Optional final cleanup (keep as in original launcher.py)
    if CLEAN_CACHE_AT_START:
        print("🧹 Cleaning up cache directories...")
        clean_cache_dirs()

    print(f"⏱️  Total launcher runtime: {time.perf_counter() - startup_start:.2f}s")
    print("Launcher finished.")

if __name__ == '__main__':
    main()