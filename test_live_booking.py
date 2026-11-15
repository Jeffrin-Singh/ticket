"""
test_live_booking.py - Live Visual Browser Automation Test
Runs a single worker with a VISIBLE browser window on the user's desktop,
logging in, solving CAPTCHA, navigating to Srivani booking, and checking live quota status.
"""

import os
import sys
import time
import logging

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Force visible browser window
os.environ["SHOW_BROWSER"] = "1"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

import booking_utils
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

EMAIL = "badmavathitravels@gmail.com"
PASSWORD = "Padma@123"
GROUP = "family1"

def main():
    print("=" * 70)
    print("🚀 LAUNCHING LIVE VISIBLE BROWSER TEST...")
    print("=" * 70)
    print(f"📧 Login Account: {EMAIL}")
    print(f"👨‍👩‍👧‍👦 Family Group: {GROUP}")
    print("🖥️  Mode: VISIBLE CHROME BROWSER (Watch your screen!)")
    print("=" * 70)

    # 1. Launch browser & perform login
    print("\n⏳ [Step 1/4] Opening Google Chrome and navigating to TTD login portal...")
    driver = booking_utils.perform_login(EMAIL, PASSWORD, worker_id=0, browser="chrome")

    if not driver:
        print("\n❌ Failed to log into TTD portal. Please check the log messages above.")
        return

    print("\n✅ [Step 2/4] Successfully logged into TTD portal!")
    time.sleep(2)

    # 2. Navigate to Srivani Donation flow
    print("\n⏳ [Step 3/4] Navigating to Srivani Trust Donations page...")
    wait = WebDriverWait(driver, 20)

    try:
        # Click Srivani link
        link_selectors = [
            (By.XPATH, "//a[contains(@href,'#/srivaniedonations')]"),
            (By.XPATH, "//a[text()='Srivani Trust Donations']"),
            (By.CSS_SELECTOR, "li.donat a")
        ]
        donation_link = None
        for by, selector in link_selectors:
            try:
                donation_link = wait.until(EC.presence_of_element_located((by, selector)))
                if donation_link:
                    break
            except Exception:
                continue

        if donation_link:
            driver.execute_script("arguments[0].scrollIntoView(true);", donation_link)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", donation_link)
            print("   👉 Clicked 'Srivani Trust Donations' link.")

        time.sleep(1.5)
        booking_utils.remove_overlays(driver)
        booking_utils.remove_all_overlays(driver)

        # Click Continue to Donate
        print("   👉 Clicking 'Continue to Donate'...")
        try:
            continue_btn = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//button[@id='smp' and contains(@ng-click, 'continueToDonate')]")
            ))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", continue_btn)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", continue_btn)
            print("   👉 Clicked 'Continue to Donate'.")
        except Exception as e:
            print(f"   ⚠️ Could not click 'Continue to Donate' automatically: {e}")

        time.sleep(1.5)
        booking_utils.remove_overlays(driver)
        booking_utils.remove_all_overlays(driver)

        # 3. Check Live Quota Availability
        print("\n⏳ [Step 4/4] Submitting donation form to inspect live quota status...")
        try:
            booking_utils.fill_donation_form(driver, 10000)
            print("   👉 Filled donation amount (Rs. 10,000) and accepted terms.")
            time.sleep(0.5)
            booking_utils.click_continue_donation(driver, auto_close=True)
            print("   👉 Clicked 'Continue Submit' on donation form.")
        except Exception as e:
            print(f"   ⚠️ Form fill error: {e}")

        time.sleep(2)

        # Check for Quota Exceeded alert or popup
        alert_info = booking_utils.check_ttd_alerts(driver)
        screenshot_path = os.path.join("screenshots", "live_test_quota.png")
        os.makedirs("screenshots", exist_ok=True)
        driver.save_screenshot(screenshot_path)
        print(f"\n📸 Saved live screenshot to: {screenshot_path}")

        if alert_info.get("found"):
            print(f"\n📢 TTD Live Server Response: [{alert_info.get('type')}]")
            print(f"   \"{alert_info.get('text')}\"")
        else:
            print(f"\n🌐 Current URL: {driver.current_url}")
            body_text = driver.execute_script("return document.body ? document.body.innerText : '';")
            if "quota exceeded" in body_text.lower():
                print("📢 TTD Server: 'Cannot book as quota exceeded' (Slots are full for today).")
            elif "darshan" in body_text.lower():
                print("📢 TTD Server: Darshan booking page loaded!")
            else:
                print("📢 Srivani page reached.")

        print("\n" + "=" * 70)
        print("🎉 LIVE BROWSER TEST COMPLETE!")
        print("🖥️  The browser window will remain open for 45 seconds for your inspection.")
        print("=" * 70)

        # Keep open for inspection
        time.sleep(45)

    except Exception as e:
        print(f"\n❌ Error during live test: {e}")
        time.sleep(15)
    finally:
        try:
            driver.quit()
            print("Browser closed cleanly.")
        except Exception:
            pass

if __name__ == '__main__':
    main()
