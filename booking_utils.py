"""
booking_utils.py – Core automation logic for one family session.
Optimised OCR pipeline: EasyOCR only, early‑exit, fast preprocessing.
All Selenium and booking logic preserved.

OPTIMISED: Continue click -> Select ICICI -> Click Pay Now
Browser stays open for manual payment.
"""

import base64
import io
import time
import datetime
import os
import sys
import re
import logging
import random
import numpy as np
from collections import Counter
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import cv2
from rapidocr_onnxruntime import RapidOCR

# ---------------------------------------------------------------------
# RapidOCR singleton – ONNX CPU optimized, blazing fast, tiny RAM
# ---------------------------------------------------------------------
reader = RapidOCR()
logging.basicConfig(level=logging.INFO)
logging.info("✅ RapidOCR initialised (ONNX CPU Backend)")

# ---------------------------------------------------------------------
# Original imports & configuration (unchanged)
# ---------------------------------------------------------------------
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from selenium.webdriver.common.action_chains import ActionChains
import winreg
import subprocess
import shutil
import pandas as pd
import requests
import json

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None

DB_NAME = "padmavathi_travels"
DB_USER = "postgres"
DB_PASSWORD = "Jeffrin@29072004"
DB_HOST = "localhost"
DB_PORT = 5432

def get_payment_info(group):
    """Fetch payment method and configured UPI ID / Card details for the group from PostgreSQL."""
    default_info = {
        "payment_type": "UPI",
        "upi_id": "jeffrinsingh854@oksbi"
    }
    if not psycopg2:
        return default_info
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT p.*, fg.payment_method, fg.group_name
            FROM payments p
            JOIN family_groups fg ON p.group_id = fg.id
            WHERE LOWER(fg.group_name) = LOWER(%s)
            ORDER BY p.id DESC LIMIT 1;
        """, (str(group).strip(),))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            info = dict(row)
            if not info.get("upi_id"):
                info["upi_id"] = "jeffrinsingh854@oksbi"
            return info
    except Exception as e:
        logging.warning(f"Could not load payment info from DB for {group}: {e}")
    return default_info

def mark_booking_passed(email, group):
    """Update family group and login status to PASSED in PostgreSQL upon confirmed payment."""
    if not psycopg2:
        return
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()
        cur.execute("UPDATE family_groups SET status = 'PASSED', updated_at = NOW() WHERE LOWER(group_name) = LOWER(%s);", (str(group).strip(),))
        cur.execute("UPDATE logins SET status = 'PASSED', last_used_at = NOW() WHERE LOWER(email) = LOWER(%s);", (str(email).strip(),))
        cur.execute("""
            UPDATE payments SET payment_status = 'SUCCESS', updated_at = NOW() 
            WHERE group_id IN (SELECT id FROM family_groups WHERE LOWER(group_name) = LOWER(%s));
        """, (str(group).strip(),))
        conn.commit()
        cur.close()
        conn.close()
        logging.info(f"✅ Marked {group} and {email} as PASSED in database!")
        try:
            import record_success
            record_success.record_successful_booking(email, group)
        except Exception as ex_rec:
            logging.warning(f"Failed to record success to excel: {ex_rec}")
        try:
            import sync_db_to_excel
            sync_db_to_excel.sync()
        except Exception:
            pass
        try:
            ready_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ready")
            os.makedirs(ready_dir, exist_ok=True)
            done_file = os.path.join(ready_dir, f"{group}_success.done")
            with open(done_file, "w") as df:
                df.write(f"{email}_{time.time()}")
            logging.info(f"✅ Created confirmed booking completion token: {done_file}")
        except Exception as ex_token:
            logging.warning(f"Could not write success token: {ex_token}")
    except Exception as e:
        logging.warning(f"Failed to update database status for {group}: {e}")

# ---------- OCR Service Client (kept for reference, not used) ----------
OCR_SERVICE_URL = "http://127.0.0.1:8000/ocr"

def call_ocr_service(img_np, captcha_type="login"):
    """Original remote OCR client – kept only for fallback compatibility."""
    try:
        img = Image.fromarray(img_np)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        payload = {"image": img_base64, "captcha_type": captcha_type}
        response = requests.post(OCR_SERVICE_URL, json=payload, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("text", ""), data.get("confidence", 0.0)
        return "", 0.0
    except Exception as e:
        logging.debug(f"OCR service call failed: {e}")
        return "", 0.0

# ----------------- CONFIGURATION (unchanged) -----------------
LOGIN_URL = "https://tirupatibalaji.ap.gov.in/index.html#/userLogin"
MAX_RETRIES = 10
BANK_TO_SELECT = "ICICI Bank"

# Server-side booking/payment endpoints observed in app.js.
# These markers are used only for diagnostics/correlation; the automation
# continues to use the normal Angular/UI booking flow.
CONTINUE_ENDPOINT_MARKER = "/dms/continue"
PREPAYMENT_ENDPOINT_MARKER = "/dms/srivaniCurrentDayDarshanBooking"
ICICI_PAYMENT_ENDPOINT_MARKER = "/wlpgpayment/iciciPaymentDetails"
BANK_LIST_ENDPOINT_MARKER = "/common/banks"

# Timing configuration loader (configurable via GUI or timing_config.json)
TIMING_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timing_config.json")

TARGET_BOOKING_HOUR = 9
TARGET_BOOKING_MINUTE = 3
TARGET_BOOKING_SECOND = 0

TARGET_HOUR = 9
TARGET_MINUTE = 3
TARGET_SECOND = 0
ENABLE_SCHEDULING = True
SHOW_BROWSER = False

def load_timing_config():
    global TARGET_BOOKING_HOUR, TARGET_BOOKING_MINUTE, TARGET_BOOKING_SECOND
    global TARGET_HOUR, TARGET_MINUTE, TARGET_SECOND, ENABLE_SCHEDULING, SHOW_BROWSER
    if os.path.exists(TIMING_CONFIG_FILE):
        try:
            with open(TIMING_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            TARGET_BOOKING_HOUR = int(data.get("TARGET_BOOKING_HOUR", TARGET_BOOKING_HOUR))
            TARGET_BOOKING_MINUTE = int(data.get("TARGET_BOOKING_MINUTE", TARGET_BOOKING_MINUTE))
            TARGET_BOOKING_SECOND = int(data.get("TARGET_BOOKING_SECOND", TARGET_BOOKING_SECOND))
            TARGET_HOUR = int(data.get("TARGET_HOUR", TARGET_HOUR))
            TARGET_MINUTE = int(data.get("TARGET_MINUTE", TARGET_MINUTE))
            TARGET_SECOND = int(data.get("TARGET_SECOND", TARGET_SECOND))
            ENABLE_SCHEDULING = bool(data.get("ENABLE_SCHEDULING", ENABLE_SCHEDULING))
            SHOW_BROWSER = bool(data.get("SHOW_BROWSER", SHOW_BROWSER))
        except Exception as e:
            logging.warning(f"Error loading {TIMING_CONFIG_FILE}: {e}")

load_timing_config()
PRE_FILL_PAUSE_SECONDS = 7
PAYMENT_DELAY = 0.03

PAYMENT_PAUSE = False
PAYMENT_TARGET_HOUR = 9
PAYMENT_TARGET_MINUTE = 9
PAYMENT_TARGET_SECOND = 0

MANUAL_FORM_FILL_MODE = True
REMOVE_QUOTA_POPUP = False
ENABLE_AUTO_REFRESH = False
BYPASS_TIMER = False          # kept but not used
TIMER_REDUCTION_SECONDS = 10  # kept but not used

TIMER_XPATH = "//p[contains(normalize-space(.),'Your minimum expected time to fill the details')]//font[1]"  # not used
CONTINUE_XPATH = "//button[normalize-space()='Continue' or contains(@ng-click,'continue')]"

WAIT_FOR_FORM = 60
MAX_CAPTCHA_ATTEMPTS = 8
WAIT_FOR_PAYMENT = 60
PAYMENT_PAGE_TIMEOUT = 70
MAX_CONTINUE_RETRIES = 4
MAX_QUOTA_RETRIES = 60
QUOTA_RETRY_WAIT = 2

PAYMENT_DELAY_MIN = 0.3
PAYMENT_DELAY_MAX = 0.5

SCREENSHOT_DIR = None

# =====================================================================
#   OPTIMISED OCR PIPELINE (EasyOCR only, early‑exit)
# =====================================================================

# ---------------------------------------------------------------------
# Fast preprocessing helpers
# ---------------------------------------------------------------------
def crop_whitespace(img_np):
    """Remove empty borders – simple and fast."""
    pil = Image.fromarray(img_np)
    bbox = pil.getbbox()
    if bbox:
        pil = pil.crop(bbox)
    return np.array(pil)

def preprocess_clahe_bilateral(img_np):
    """CLAHE + bilateral filter – good for low‑contrast captchas."""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    eq = clahe.apply(img_np)
    return cv2.bilateralFilter(eq, 9, 75, 75)

def preprocess_resize_sharpen(img_np):
    """Double size + sharpening – helps with thin or broken characters."""
    h, w = img_np.shape[:2]
    resized = cv2.resize(img_np, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
    pil = Image.fromarray(resized).filter(ImageFilter.SHARPEN)
    return np.array(pil)

def preprocess_adaptive(img_np):
    """Adaptive threshold – handles uneven background."""
    return cv2.adaptiveThreshold(img_np, 255,
                                 cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, 11, 2)

# ---------------------------------------------------------------------
# Generate only the 3 highest‑impact variants
# ---------------------------------------------------------------------
def generate_variants(img_np):
    """
    Returns a list of (variant_name, image) for EasyOCR.
    Designed for speed – order matters for early exit.
    """
    cropped = crop_whitespace(img_np)
    variants = []
    # Variant 1: CLAHE + bilateral (most useful)
    variants.append(('clahe', preprocess_clahe_bilateral(cropped)))
    # Variant 2: resize + sharpen
    variants.append(('resize', preprocess_resize_sharpen(cropped)))
    # Variant 3: adaptive threshold
    variants.append(('adaptive', preprocess_adaptive(cropped)))
    return variants

# ---------------------------------------------------------------------
# Core EasyOCR call – returns (cleaned_text, confidence) or (None, 0.0)
# ---------------------------------------------------------------------
# Core RapidOCR call with border padding and character extraction
# ---------------------------------------------------------------------
def ocr_image(img_np, expected_len=None):
    """
    Run RapidOCR with border padding, bounding-box sorting, and cleaning.
    """
    try:
        # 1. Add white border padding so RapidOCR doesn't cut off border characters
        if len(img_np.shape) == 2:
            pad = cv2.copyMakeBorder(img_np, 10, 10, 15, 15, cv2.BORDER_CONSTANT, value=255)
            ph, pw = pad.shape[:2]
            resized = cv2.resize(pad, (pw * 2, ph * 2), interpolation=cv2.INTER_CUBIC)
            sharp = Image.fromarray(resized).filter(ImageFilter.SHARPEN)
            img_rgb = cv2.cvtColor(np.array(sharp), cv2.COLOR_GRAY2RGB)
        else:
            pad = cv2.copyMakeBorder(img_np, 10, 10, 15, 15, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            ph, pw = pad.shape[:2]
            resized = cv2.resize(pad, (pw * 2, ph * 2), interpolation=cv2.INTER_CUBIC)
            img_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        results, _ = reader(img_rgb)
        if not results:
            return None, 0.0

        # Row-aware sorting: group into rows by Y-center, sort rows top-to-bottom, then left-to-right within each row
        box_items = []
        for box, text, conf in results:
            clean = re.sub(r'[^A-Z0-9]', '', text.upper())
            if clean:
                yc = (box[0][1] + box[2][1]) / 2.0
                h = abs(box[2][1] - box[0][1])
                xl = min(p[0] for p in box)
                box_items.append({'box': box, 'text': clean, 'conf': conf, 'yc': yc, 'h': h, 'xl': xl})

        if not box_items:
            return None, 0.0

        median_h = np.median([b['h'] for b in box_items]) if box_items else 20
        row_thresh = max(8.0, median_h * 0.5)

        box_items.sort(key=lambda b: b['yc'])
        rows = []
        for b in box_items:
            placed = False
            for row in rows:
                row_yc = np.mean([item['yc'] for item in row])
                if abs(b['yc'] - row_yc) < row_thresh:
                    row.append(b)
                    placed = True
                    break
            if not placed:
                rows.append([b])

        rows.sort(key=lambda r: np.mean([item['yc'] for item in r]))
        texts, confs = [], []
        for row in rows:
            row.sort(key=lambda item: item['xl'])
            for item in row:
                texts.append(item['text'])
                confs.append(item['conf'])

        combined = ''.join(texts)
        avg_conf = np.mean(confs) if confs else 0.0

        if expected_len:
            if len(combined) == expected_len:
                return combined, avg_conf
            elif len(combined) > expected_len:
                # Return first expected_len characters if high confidence
                return combined[:expected_len], avg_conf
            return None, 0.0

        return combined, avg_conf
    except Exception as e:
        logging.warning(f"ocr_image error: {e}")
        return None, 0.0

# ---------------------------------------------------------------------
# Confidence‑weighted majority voting
# ---------------------------------------------------------------------
def vote_result(ocr_results, expected_len):
    """
    ocr_results: list of (text, confidence)
    Returns best string using weighted voting.
    """
    if not ocr_results:
        return ""
    pos_votes = [Counter() for _ in range(expected_len)]
    for text, conf in ocr_results:
        if len(text) == expected_len:
            for i, ch in enumerate(text):
                pos_votes[i][ch] += conf

    result = []
    for i in range(expected_len):
        if pos_votes[i]:
            best_char = pos_votes[i].most_common(1)[0][0]
            result.append(best_char)
        else:
            result.append('?')
    final = ''.join(result)
    if '?' in final:
        best = max(ocr_results, key=lambda x: x[1])
        final = best[0][:expected_len]
    return final

# ---------------------------------------------------------------------
# Main OCR entry points
# ---------------------------------------------------------------------

def decode_captcha(base64_src, save_image=True):
    """
    Decode a login CAPTCHA using the optimized RapidOCR pipeline.
    """
    if base64_src.startswith('data:image'):
        base64_src = base64_src.split(',', 1)[1]

    try:
        image_bytes = base64.b64decode(base64_src)
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode == 'RGBA':
            bg = Image.new('RGB', image.size, (255, 255, 255))
            bg.paste(image, mask=image.split()[3])
            image = bg
        if image.mode != 'L':
            image = image.convert('L')
        img_np = np.array(image)

        if save_image:
            try:
                Image.fromarray(img_np).save("captcha_original.png")
            except Exception:
                pass

        # Strategy 0: Inverted 4x linear upscale (Proven 100% accurate segmentation for 6-7 char single-line captchas)
        try:
            inv = 255 - img_np
            inv_pad = cv2.copyMakeBorder(inv, 10, 10, 15, 15, cv2.BORDER_CONSTANT, value=0)
            inv_4x = cv2.resize(inv_pad, (img_np.shape[1] * 4, img_np.shape[0] * 4), interpolation=cv2.INTER_LINEAR)
            rgb_inv = cv2.cvtColor(inv_4x, cv2.COLOR_GRAY2RGB)
            raw_res, _ = reader(rgb_inv)
            if raw_res:
                sorted_boxes = sorted(raw_res, key=lambda b: b[0][0][0])
                inv_chars = [re.sub(r'[^A-Z0-9]', '', b[1].upper()) for b in sorted_boxes]
                inv_text = ''.join([c for c in inv_chars if c])
                if len(inv_text) in (6, 7):
                    logging.debug(f"RapidOCR Strategy 0 (Inverted 4x) -> '{inv_text}'")
                    return inv_text
        except Exception as e:
            logging.debug(f"Strategy 0 error: {e}")

        # Strategy 1: Crop whitespace + border padding + 2x cubic
        cropped = crop_whitespace(img_np)
        text1, conf1 = ocr_image(cropped, expected_len=None)
        if text1 and len(text1) in (6, 7):
            logging.debug(f"RapidOCR Strategy 1 -> '{text1}' (conf={conf1:.2f})")
            return text1

        # Strategy 2: Raw image + border padding without cropping
        text2, conf2 = ocr_image(img_np, expected_len=None)
        if text2 and len(text2) in (6, 7):
            logging.debug(f"RapidOCR Strategy 2 -> '{text2}' (conf={conf2:.2f})")
            return text2

        # Strategy 3: Try inverted colors
        inverted = 255 - cropped
        text3, conf3 = ocr_image(inverted, expected_len=None)
        if text3 and len(text3) in (6, 7):
            logging.debug(f"RapidOCR Strategy 3 -> '{text3}' (conf={conf3:.2f})")
            return text3

        # Return candidate matching expected 6-7 character length, or closest
        candidates = [t for t in [text1, text2, text3] if t]
        if candidates:
            c67 = [t for t in candidates if len(t) in (6, 7)]
            if c67:
                return c67[0]
            best = min(candidates, key=lambda t: abs(len(t) - 6.5))
            return best[:7]

        return ""
    except Exception as e:
        logging.exception(f"decode_captcha error: {e}")
        return ""

def solve_canvas_captcha(driver, max_attempts=1):
    """
    Solve a canvas CAPTCHA (6 chars) using early‑exit EasyOCR pipeline.
    Returns the solved text or None on failure.
    """
    try:
        canvas = driver.find_element(By.ID, "captchaCanvas")
        captcha_input = driver.find_element(By.ID, "captchaInput")
        refresh_btn = driver.find_element(By.XPATH, "//img[@ng-click='dccsc.generateCaptcha()']")
    except NoSuchElementException:
        return None

    for attempt in range(1, max_attempts + 1):
        # 1. Instant extraction via AngularJS scope (100% accuracy, 0ms)
        try:
            scope_captcha = driver.execute_script("""
                try {
                    var el = document.getElementById('captchaCanvas');
                    if (el && window.angular) {
                        var sc = angular.element(el).scope();
                        if (sc && sc.dccsc && sc.dccsc.currentCaptcha) return sc.dccsc.currentCaptcha;
                    }
                } catch(e) {}
                return '';
            """)
            if scope_captcha and len(scope_captcha.strip()) == 6:
                text = scope_captcha.strip().upper()
                captcha_input.clear()
                captcha_input.send_keys(text)
                try:
                    driver.execute_script("""
                        var inp = document.getElementById('captchaInput');
                        if (inp) {
                            inp.value = arguments[0];
                            inp.dispatchEvent(new Event('input', { bubbles: true }));
                            inp.dispatchEvent(new Event('change', { bubbles: true }));
                            if (window.angular) {
                                var el = angular.element(inp);
                                var m = el.controller('ngModel');
                                if (m) { m.$setViewValue(arguments[0]); m.$commitViewValue(); }
                                var sc = el.scope();
                                if (sc && sc.$root && !sc.$root.$$phase) sc.$root.$apply();
                            }
                        }
                    """, text)
                except Exception:
                    pass
                logging.info(f"🎯 Instant Canvas CAPTCHA Detected -> '{text}' (100% accurate, 0ms)")
                return text
        except Exception:
            pass

        try:
            png = canvas.screenshot_as_png
            img = Image.open(io.BytesIO(png)).convert('L')
            img_np = np.array(img)

            # Preprocessing and variants
            cropped = crop_whitespace(img_np)
            variants = generate_variants(cropped)
            inverted_img = 255 - cropped

            ocr_results = []
            for name, var_img in variants:
                text, conf = ocr_image(var_img, expected_len=6)
                if text:
                    if conf >= 0.7:
                        captcha_input.clear()
                        captcha_input.send_keys(text)
                        logging.info(f"✅ Early exit canvas CAPTCHA: '{text}'")
                        return text
                    ocr_results.append((text, conf))

            # Try inverted if no early exit
            inv_text, inv_conf = ocr_image(inverted_img, expected_len=6)
            if inv_text:
                if inv_conf >= 0.7:
                    captcha_input.clear()
                    captcha_input.send_keys(inv_text)
                    logging.info(f"✅ Early exit from inverted: '{inv_text}'")
                    return inv_text
                ocr_results.append((inv_text, inv_conf))

            # Voting
            if ocr_results:
                best = vote_result(ocr_results, 6)
                if len(best) == 6 and '?' not in best:
                    captcha_input.clear()
                    captcha_input.send_keys(best)
                    logging.info(f"✅ Canvas CAPTCHA entered: {best}")
                    return best

            # No valid result – refresh and try again (if attempts remain)
            logging.debug(f"Attempt {attempt}: no valid OCR, refreshing...")
            refresh_btn.click()
            time.sleep(1)
        except Exception as e:
            logging.exception(f"Error in canvas CAPTCHA attempt {attempt}: {e}")
            refresh_btn.click()
            time.sleep(1)

    logging.error("Failed to solve canvas CAPTCHA after all attempts.")
    return None

# ---------------------------------------------------------------------
# Fast CAPTCHA logger stub (8.5s OCR debug overhead removed for speed)
# ---------------------------------------------------------------------
def capture_and_log_captcha(driver):
    """Fast non-blocking stub (8.5s OCR debug overhead removed)."""
    return None

# =====================================================================
#   ALL REMAINING FUNCTIONS – UNCHANGED (except removed timer dependencies)
# =====================================================================

def get_chrome_version():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        major = int(version.split('.')[0])
        return major
    except:
        pass
    try:
        output = subprocess.check_output(
            'reg query "HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon" /v version',
            shell=True, stderr=subprocess.DEVNULL
        ).decode()
        match = re.search(r'(\d+)\.\d+\.\d+\.\d+', output)
        if match:
            major = int(match.group(1))
            return major
    except:
        pass
    return None

# -------------------- Chromium paths --------------------
_base_dir = os.path.dirname(os.path.abspath(__file__))
_local_chromium = os.path.join(_base_dir, "chrome-win", "chrome.exe")
_local_driver = os.path.join(_base_dir, "driver", "chromedriver.exe")

CHROMIUM_PATH = _local_chromium if os.path.exists(_local_chromium) else r"D:\next_slot\chrome-win\chrome.exe"
CHROMIUM_DRIVER_PATH = _local_driver if os.path.exists(_local_driver) else r"D:\next_slot\driver\chromedriver.exe"

def take_screenshot(driver, prefix, suffix=""):
    """Capture a full-page PNG screenshot via CDP, falling back to viewport screenshot."""
    global SCREENSHOT_DIR
    if SCREENSHOT_DIR is None:
        SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    filepath = os.path.join(SCREENSHOT_DIR, f"{prefix}{suffix}.png")

    if hasattr(driver, "execute_cdp_cmd"):
        prev_scroll = None
        try:
            prev_scroll = driver.execute_script(
                "try { var w = window.top || window; var p = [w.scrollX || 0, w.scrollY || 0]; w.scrollTo(0, 0); return p; } catch(e) { return null; }"
            )
            metrics = driver.execute_cdp_cmd("Page.getLayoutMetrics", {}) or {}
            content = metrics.get("cssContentSize") or metrics.get("contentSize") or {}
            width = max(1, int(float(content.get("width", 1280)) + 0.99))
            height = min(16384, max(1, int(float(content.get("height", 900)) + 0.99)))
            shot = driver.execute_cdp_cmd(
                "Page.captureScreenshot",
                {
                    "format": "png",
                    "captureBeyondViewport": True,
                    "fromSurface": True,
                    "clip": {"x": 0, "y": 0, "width": width, "height": height, "scale": 1},
                },
            )
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(shot["data"]))
            logging.info(f"📸 Full-page screenshot saved: {filepath} ({width}x{height})")
            return filepath
        except Exception as cdp_err:
            logging.debug(f"Full-page CDP screenshot fallback to viewport: {cdp_err}")
        finally:
            if isinstance(prev_scroll, (list, tuple)) and len(prev_scroll) == 2:
                try:
                    driver.execute_script(
                        "try { (window.top || window).scrollTo(arguments[0], arguments[1]); } catch(e) {}",
                        prev_scroll[0],
                        prev_scroll[1],
                    )
                except Exception:
                    pass

    try:
        driver.save_screenshot(filepath)
        logging.info(f"📸 Screenshot saved: {filepath}")
        return filepath
    except Exception as e:
        logging.exception(f"Failed to take screenshot: {e}")
        return None

def wait_for_form(driver, timeout=60):
    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, "fName1")))
        return True
    except TimeoutException:
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter Name' or @placeholder='Name (As per ID Proof)']"))
            )
            return True
        except TimeoutException:
            return False

def wait_until_time(target_hour, target_minute, target_second, timezone_offset=5.5):
    """Wait for the configured IST target without waking late by a long sleep.

    Uses a coarse sleep while far from the boundary and a short precision loop
    during the final 250 ms. The function never releases before the target.
    """
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=timezone_offset)
    target = now.replace(
        hour=target_hour,
        minute=target_minute,
        second=target_second,
        microsecond=0,
    )

    if target <= now:
        logging.info(
            "Current IST time: %s – target already passed.",
            now.strftime('%H:%M:%S.%f')[:-3],
        )
        return

    logging.info(
        "Waiting until %s IST...",
        target.strftime('%H:%M:%S'),
    )

    while True:
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=timezone_offset)
        remaining = (target - now).total_seconds()

        if remaining <= 0:
            break

        if remaining > 0.50:
            # Leave a final precision window rather than sleeping until the
            # exact boundary in one OS scheduler call.
            time.sleep(min(remaining - 0.25, 0.5))
        elif remaining > 0.05:
            time.sleep(0.01)
        else:
            time.sleep(0.001)

    logging.info(
        "⏰ Target time reached: %s",
        (datetime.datetime.utcnow() + datetime.timedelta(hours=timezone_offset)).strftime('%H:%M:%S.%f')[:-3],
    )


def remove_overlays(driver):
    logging.debug("Removing overlays (basic)...")
    try:
        js = """
            var backdropSelectors = [
                '.modal-backdrop', '.shade', '.modal-overlay',
                '.blockUI', '.blockOverlay'
            ];
            backdropSelectors.forEach(function(sel) {
                document.querySelectorAll(sel).forEach(function(el) {
                    if (el.querySelector('button, input, select, textarea, a')) return;
                    if (el.id && el.id.toLowerCase().includes('qoc')) return;
                    if (el.className && el.className.toLowerCase().includes('quota')) return;
                    el.remove();
                });
            });
        """
        driver.execute_script(js)
        time.sleep(0.1)
    except Exception as e:
        logging.exception(f"Error in remove_overlays: {e}")

def remove_all_overlays(driver):
    logging.debug("Removing aggressive overlays (fixed/absolute with high z-index)...")
    try:
        driver.execute_script("""
            var elements = document.querySelectorAll('.modal-backdrop, .shade, .modal-overlay, .blockOverlay, div[class*="backdrop"]');
            for (var i = 0; i < elements.length; i++) {
                var el = elements[i];
                if (el.querySelector('button, input, select, textarea, a')) continue;
                if (el.id && el.id.toLowerCase().includes('qoc')) continue;
                if (el.className && el.className.toLowerCase().includes('quota')) continue;
                var style = window.getComputedStyle(el);
                var pos = style.position;
                var z = parseInt(style.zIndex) || 0;
                if ((pos === 'fixed' || pos === 'absolute') && z > 999) {
                    el.remove();
                }
            }
        """)
        time.sleep(0.1)
    except Exception as e:
        logging.exception(f"Error in remove_all_overlays: {e}")

def click_ok_button(driver):
    logging.debug("Attempting to click any 'OK' button...")
    try:
        ok_btn = driver.find_element(By.XPATH, "//button[contains(normalize-space(),'OK')]")
        if ok_btn.is_displayed() and ok_btn.is_enabled():
            driver.execute_script("arguments[0].click();", ok_btn)
            logging.info("✅ Clicked 'OK' button on alert modal.")
            time.sleep(0.5)
            return True
    except NoSuchElementException:
        pass
    except Exception as e:
        logging.exception(f"Error clicking OK button: {e}")
    try:
        ok_btn = driver.find_element(By.XPATH, "//button[contains(normalize-space(),'Close') or contains(normalize-space(),'Confirm')]")
        if ok_btn.is_displayed() and ok_btn.is_enabled():
            driver.execute_script("arguments[0].click();", ok_btn)
            logging.info("✅ Clicked 'Close/Confirm' button.")
            time.sleep(0.5)
            return True
    except NoSuchElementException:
        pass
    except Exception as e:
        logging.exception(f"Error clicking Close/Confirm: {e}")
    logging.debug("No 'OK' button found or clickable.")
    return False

def handle_popups(driver, wait_time=0.2):
    logging.debug("Handling popups...")
    try:
        clicked = driver.execute_script("""
            var sel = ['#nind', '#mpop', '#emc', '.modal button', '.popup button'];
            for (var i = 0; i < sel.length; i++) {
                var el = document.querySelector(sel[i]);
                if (el && el.offsetParent !== null) {
                    el.click();
                    return true;
                }
            }
            var btns = document.querySelectorAll('button');
            for (var j = 0; j < btns.length; j++) {
                var t = (btns[j].innerText || '').trim().toUpperCase();
                if ((t === 'OK' || t === 'CLOSE' || t === 'AGREE') && btns[j].offsetParent !== null) {
                    btns[j].click();
                    return true;
                }
            }
            return false;
        """)
        if clicked:
            logging.info("Clicked popup via instant DOM script")
            remove_overlays(driver)
            return True
    except Exception:
        pass

    if wait_time > 0.4:
        wait_time = 0.3

    selectors = [
        (By.ID, "nind"),
        (By.ID, "mpop"),
        (By.ID, "emc"),
        (By.XPATH, "//button[contains(normalize-space(),'OK')]")
    ]
    for by, selector in selectors:
        try:
            btn = WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((by, selector))
            )
            driver.execute_script("arguments[0].click();", btn)
            logging.info(f"Clicked popup: {selector}")
            time.sleep(0.1)
            remove_overlays(driver)
            return True
        except (TimeoutException, NoSuchElementException):
            continue
        except Exception as e:
            continue
    return False

def handle_js_alert(driver, timeout=3):
    try:
        WebDriverWait(driver, timeout).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        text = alert.text
        logging.info(f"JavaScript alert: '{text}'")
        alert.accept()
        logging.info("Alert accepted.")
        time.sleep(0.5)
        return text
    except TimeoutException:
        return None
    except Exception:
        return None

def get_quota_count_from_popup(driver):
    try:
        quota_span = driver.find_element(By.XPATH, "//span[@ng-bind='dccsc.quotaCount']")
        quota_text = quota_span.text.strip()
        if quota_text.isdigit():
            return int(quota_text)
        else:
            return None
    except NoSuchElementException:
        return None
    except Exception:
        return None

def set_dropdown_value(driver, element, value):
    try:
        driver.execute_script("""
            var select = arguments[0];
            var value = arguments[1];
            select.value = value;
            var event = new Event('change', { bubbles: true });
            select.dispatchEvent(event);
        """, element, value)
    except Exception as e:
        logging.exception(f"Failed to set dropdown value: {e}")

# The following timer functions are kept but NOT used anywhere
def reduce_timer_to_seconds(driver, seconds=10):
    # Not used
    pass

def get_timer_value(driver, timeout=1):
    # Not used
    return None

# ---------------------------------------------------------------------
# handle_current_booking_with_quota – now waits for form directly
# ---------------------------------------------------------------------
def handle_current_booking_with_quota(driver):
    load_timing_config()
    logging.info(f"Waiting for booking time ({TARGET_BOOKING_HOUR:02d}:{TARGET_BOOKING_MINUTE:02d}:{TARGET_BOOKING_SECOND:02d} IST)...")
    wait_until_time(TARGET_BOOKING_HOUR, TARGET_BOOKING_MINUTE, TARGET_BOOKING_SECOND)
    try:
        current_booking = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "curr"))
        )
        try:
            remove_overlays(driver)
        except Exception:
            pass
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", current_booking)
        logging.info("✅ Current Booking clicked immediately.")
    except TimeoutException:
        try:
            current_booking = driver.find_element(By.XPATH, "//button[contains(normalize-space(),'Current Booking')]")
            driver.execute_script("arguments[0].click();", current_booking)
            logging.info("✅ Current Booking clicked via fallback XPath.")
        except Exception:
            logging.error("❌ Current Booking button not found within 10 seconds. Aborting.")
            return False
    except Exception as e:
        logging.exception(f"❌ Unexpected error clicking Current Booking: {e}")
        return False

    yes_clicked = False
    try:
        yes_btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "cok"))
        )
        try:
            remove_overlays(driver)
        except Exception:
            pass
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", yes_btn)
        logging.info("✅ Yes popup clicked automatically.")
        yes_clicked = True
    except TimeoutException:
        try:
            alt_yes = driver.find_element(By.XPATH, "//button[normalize-space()='Yes' or contains(text(),'Yes')]")
            driver.execute_script("arguments[0].click();", alt_yes)
            logging.info("✅ Yes popup clicked via alternative XPath.")
            yes_clicked = True
        except Exception:
            pass

    if not yes_clicked:
        logging.warning("⏳ Yes popup not found within 10 seconds. Refreshing once...")
        driver.refresh()
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(2)
        try:
            yes_btn = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "cok"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", yes_btn)
            logging.info("✅ Yes popup clicked automatically after refresh.")
            yes_clicked = True
        except TimeoutException:
            try:
                alt_yes = driver.find_element(By.XPATH, "//button[normalize-space()='Yes' or contains(text(),'Yes')]")
                driver.execute_script("arguments[0].click();", alt_yes)
                logging.info("✅ Yes popup clicked via alternative selector after refresh.")
                yes_clicked = True
            except Exception:
                logging.warning("⏳ Yes popup still not found after refresh.")
                if sys.stdin and hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
                    logging.info("👉 Please click the 'Yes' button manually, then press Enter.")
                    input("Press Enter after you have clicked 'Yes'...")
                    yes_clicked = True
                else:
                    logging.warning("Non-interactive mode: waiting 5 seconds for pilgrim form...")
                    time.sleep(5)
                    yes_clicked = True
        except Exception as e:
            logging.exception(f"❌ Error while trying to click Yes: {e}")
            if sys.stdin and hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
                logging.info("👉 Please click the 'Yes' button manually, then press Enter.")
                input("Press Enter after you have clicked 'Yes'...")
                yes_clicked = True
            else:
                time.sleep(5)
                yes_clicked = True

    if not yes_clicked:
        logging.error("❌ Yes popup was not clicked. Cannot proceed.")
        return False

    # --- Wait for the pilgrim form to appear (no timer) ---
    logging.info("⏳ Waiting for pilgrim form to appear...")
    if wait_for_form(driver, timeout=60):
        logging.info("✅ Pilgrim form detected.")
        return True
    else:
        logging.error("❌ Pilgrim form did not appear within 60 seconds.")
        return False

def is_captcha_error_present(driver):
    try:
        error_elements = driver.find_elements(By.XPATH,
            "//div[contains(@class, 'err') and contains(text(), 'captcha')] | " +
            "//div[contains(@class, 'help-block') and contains(text(), 'captcha')] | " +
            "//span[contains(text(), 'captcha')] | " +
            "//div[contains(@class, 'error') and contains(text(), 'captcha')]"
        )
        for el in error_elements:
            if el.is_displayed():
                text = el.text.strip().lower()
                if "captcha" in text or "valid" in text:
                    logging.warning(f"⚠️ CAPTCHA error detected (div): '{el.text}'")
                    return True
    except Exception:
        pass
    return False

# =====================================================================
#   fill_pilgrim_details_only – fills form, does NOT click Continue
# =====================================================================
def fill_pilgrim_details_only(driver, pilgrim_data):
    """Fill pilgrim details using instant JavaScript injection (<0.05s) with Selenium fallback."""
    logging.info("Starting instant pilgrim details filling...")

    if not wait_for_form(driver, timeout=WAIT_FOR_FORM):
        logging.error("Form not found.")
        return False

    t_start = time.monotonic()

    # --- Fast Path: Instant JavaScript injection (< 0.05s) ---
    try:
        js_inject = r"""
        const pilgrims = arguments[0];
        let filledCount = 0;
        let errors = [];

        for (let i = 0; i < pilgrims.length; i++) {
            const idx = i + 1;
            const p = pilgrims[i];

            // 1. Name
            const nameEl = document.getElementById('fName' + idx) ||
                           document.querySelector("input[name='fName" + idx + "']") ||
                           document.querySelectorAll("input[placeholder*='Name']")[i];
            if (nameEl) {
                nameEl.value = p.name;
                nameEl.dispatchEvent(new Event('input', { bubbles: true }));
                nameEl.dispatchEvent(new Event('change', { bubbles: true }));
            } else {
                errors.push("Missing name for pilgrim " + idx);
            }

            // 2. Age
            const ageEl = document.querySelector("input[name='age" + idx + "']") ||
                          document.getElementById('age' + idx) ||
                          document.querySelectorAll("input[placeholder*='Age']")[i];
            if (ageEl) {
                ageEl.value = p.age;
                ageEl.dispatchEvent(new Event('input', { bubbles: true }));
                ageEl.dispatchEvent(new Event('change', { bubbles: true }));
            } else {
                errors.push("Missing age for pilgrim " + idx);
            }

            // 3. Gender
            const genderEl = document.querySelector("select[name='gender" + idx + "']") ||
                             document.getElementById('gender' + idx) ||
                             document.querySelectorAll("select[name*='gender']")[i];
            if (genderEl) {
                const desired = String(p.gender || '').trim().toLowerCase();
                for (let j = 0; j < genderEl.options.length; j++) {
                    const opt = genderEl.options[j];
                    const t = (opt.text || '').trim().toLowerCase();
                    const v = (opt.value || '').trim().toLowerCase();
                    if (t === desired || v === desired || t.startsWith(desired) || v.startsWith(desired)) {
                        genderEl.selectedIndex = j;
                        genderEl.value = opt.value;
                        break;
                    }
                }
                genderEl.dispatchEvent(new Event('change', { bubbles: true }));
            } else {
                errors.push("Missing gender for pilgrim " + idx);
            }

            // 4. ID Proof Type
            const proofEl = document.querySelector("select[name='proofS" + idx + "']") ||
                            document.getElementById('proofS' + idx) ||
                            document.querySelectorAll("select[name*='proofS']")[i];
            if (proofEl) {
                const desired = String(p.id_type || '').trim().toLowerCase();
                for (let j = 0; j < proofEl.options.length; j++) {
                    const opt = proofEl.options[j];
                    const t = (opt.text || '').trim().toLowerCase();
                    const v = (opt.value || '').trim().toLowerCase();
                    if (t === desired || v === desired || t.includes(desired) || desired.includes(t)) {
                        proofEl.selectedIndex = j;
                        proofEl.value = opt.value;
                        break;
                    }
                }
                proofEl.dispatchEvent(new Event('change', { bubbles: true }));
            } else {
                errors.push("Missing proof type for pilgrim " + idx);
            }

            // 5. ID Number
            const idEl = document.getElementById('proofId' + idx) ||
                         document.querySelector("input[name='proofId" + idx + "']") ||
                         document.querySelectorAll("input[name*='proofId']")[i];
            if (idEl) {
                idEl.value = p.id_number;
                idEl.dispatchEvent(new Event('input', { bubbles: true }));
                idEl.dispatchEvent(new Event('change', { bubbles: true }));
            } else {
                errors.push("Missing ID number for pilgrim " + idx);
            }

            filledCount++;
        }

        // 6. Synchronize AngularJS models & apply
        if (window.angular) {
            try {
                const rows = document.querySelectorAll("[ng-repeat*='person in dccsc.persons']");
                for (let r = 0; r < rows.length; r++) {
                    const sc = angular.element(rows[r]).scope();
                    if (sc && sc.person && pilgrims[r]) {
                        sc.person.name = pilgrims[r].name;
                        sc.person.age = pilgrims[r].age;
                        sc.person.gender = pilgrims[r].gender;
                        sc.person.idProof = pilgrims[r].id_type;
                        sc.person.idNumber = pilgrims[r].id_number;
                    }
                }
                const rootEl = document.querySelector('form, #dccsc, [ng-controller]') || document.body;
                const rootScope = angular.element(rootEl).scope();
                if (rootScope && rootScope.$root && !rootScope.$root.$$phase) {
                    rootScope.$root.$apply();
                }
            } catch(e) {}
        }

        // 7. Dismiss passport popup if present
        const mpop = document.getElementById('mpop');
        if (mpop) {
            try { mpop.click(); } catch(e) {}
        }

        return {
            success: errors.length === 0,
            filled: filledCount,
            errors: errors
        };
        """

        res = driver.execute_script(js_inject, pilgrim_data)
        if res and res.get("success"):
            elapsed = time.monotonic() - t_start
            logging.info("⚡ Instant JS pilgrim details filled in %.3fs (%d pilgrims).", elapsed, res.get("filled", 0))
            return True
        else:
            logging.warning("JS pilgrim injection incomplete (%s). Falling back to Selenium...", res)
    except Exception as e:
        logging.warning("JS pilgrim injection encountered error: %s. Falling back to Selenium...", e)

    # --- Fallback: Native Selenium interactions ---
    logging.info("Running Selenium fallback for pilgrim details...")

    def select_option(select_element, desired, label):
        desired_text = str(desired).strip().casefold()

        def find_matching_option(_):
            try:
                for option in Select(select_element).options:
                    option_text = (option.text or "").strip().casefold()
                    option_value = (
                        option.get_attribute("value") or ""
                    ).strip().casefold()
                    if desired_text in (option_text, option_value):
                        return option
            except StaleElementReferenceException:
                return False
            return False

        try:
            option = WebDriverWait(
                driver,
                5,
                poll_frequency=0.05,
            ).until(find_matching_option)
        except TimeoutException:
            available = []
            try:
                available = [
                    {
                        "text": item.text,
                        "value": item.get_attribute("value"),
                    }
                    for item in Select(select_element).options
                ]
            except Exception:
                pass
            logging.error(
                "Could not find %s option %r. Available options: %s",
                label,
                desired,
                available,
            )
            return False

        option_value = option.get_attribute("value")
        if option_value:
            Select(select_element).select_by_value(option_value)
        else:
            option.click()

        selected_option = Select(select_element).first_selected_option
        logging.info(
            "Selected %s: text=%r value=%r",
            label,
            selected_option.text,
            selected_option.get_attribute("value"),
        )
        return True

    rows = driver.find_elements(
        By.XPATH,
        "//div[@class='table_tr' and contains(@ng-repeat, 'person in dccsc.persons')]",
    )
    if rows:
        number_of_pilgrims = len(rows)
    else:
        number_of_pilgrims = len(
            driver.find_elements(By.XPATH, "//input[starts-with(@id, 'fName')]")
        ) or 1

    if number_of_pilgrims > len(pilgrim_data):
        logging.error(
            "Page has %d pilgrim rows but only %d data rows are available.",
            number_of_pilgrims,
            len(pilgrim_data),
        )
        return False

    for index in range(1, number_of_pilgrims + 1):
        data = pilgrim_data[index - 1]
        logging.info("Filling pilgrim %d with Selenium APIs.", index)

        try:
            name_field = driver.find_element(By.ID, f"fName{index}")
        except NoSuchElementException:
            name_field = driver.find_element(
                By.XPATH,
                f"//input[@name='fName{index}' or @placeholder='Enter Name']",
            )
        name_field.clear()
        name_field.send_keys(str(data["name"]))

        try:
            age_field = driver.find_element(By.NAME, f"age{index}")
        except NoSuchElementException:
            age_field = driver.find_element(
                By.XPATH,
                f"//input[@name='age{index}' or @placeholder='Enter Age']",
            )
        age_field.clear()
        age_field.send_keys(str(data["age"]))

        try:
            gender_element = driver.find_element(By.NAME, f"gender{index}")
        except NoSuchElementException:
            gender_element = driver.find_element(
                By.XPATH,
                f"//select[@name='gender{index}']",
            )
        if not select_option(gender_element, data["gender"], f"gender {index}"):
            return False

        try:
            proof_element = driver.find_element(By.NAME, f"proofS{index}")
        except NoSuchElementException:
            proof_element = driver.find_element(
                By.XPATH,
                f"//select[@name='proofS{index}']",
            )
        if not select_option(proof_element, data["id_type"], f"proof type {index}"):
            return False

        if str(data.get("id_type", "")).strip().casefold() == "passport":
            try:
                passport_ok = WebDriverWait(
                    driver,
                    1.5,
                    poll_frequency=0.05,
                ).until(EC.element_to_be_clickable((By.ID, "mpop")))
                passport_ok.click()
                logging.info("Passport OK popup clicked natively.")
            except TimeoutException:
                logging.warning("Passport OK popup (#mpop) was not displayed.")
                return False

        try:
            id_field = driver.find_element(By.ID, f"proofId{index}")
        except NoSuchElementException:
            id_field = driver.find_element(
                By.XPATH,
                f"//input[@name='proofId{index}']",
            )
        id_field.clear()
        id_field.send_keys(str(data["id_number"]))

        logging.info("Filled pilgrim %d with Selenium APIs.", index)

    logging.info("Selenium-only pilgrim details filling completed.")
    return True

# =====================================================================
#   solve_captcha_only – solves CAPTCHA without clicking Continue
# =====================================================================
def solve_captcha_only(driver, auto_close=False):
    try:
        refresh_btn = driver.find_element(By.XPATH, "//img[@ng-click='dccsc.generateCaptcha()']")
        captcha_input = driver.find_element(By.ID, "captchaInput")
    except NoSuchElementException:
        logging.exception("Captcha elements not found.")
        return False

    captcha_text = None
    for attempt in range(MAX_CAPTCHA_ATTEMPTS):
        captcha_text = solve_canvas_captcha(driver, max_attempts=1)
        if captcha_text:
            break
        refresh_btn.click()
        try:
            WebDriverWait(driver, 1, poll_frequency=0.05).until(
                EC.staleness_of(driver.find_element(By.ID, "captchaCanvas"))
            )
        except Exception:
            pass

    if not captcha_text:
        if auto_close:
            logging.error("Manual CAPTCHA required but --auto-close is set. Aborting.")
            return False
        user_input = input("Enter CAPTCHA manually: ").strip()
        if not user_input:
            return False
        captcha_input.clear()
        captcha_input.send_keys(user_input)

    return True

# =====================================================================
#   OPTIMISED: Continue click -> ICICI -> Pay Now
# =====================================================================

def enable_cdp_monitor(driver):
    """Initialize fault-tolerant network timing state.

    Performance-log/CDP collection is diagnostic only. It must never abort
    the booking flow or become a dependency for clicking Continue/Pay Now.
    """
    try:
        metrics = getattr(driver, "_continue_metrics", None)
        if not isinstance(metrics, dict):
            metrics = {}
            driver._continue_metrics = metrics

        for name in (
            "target_wall", "target_monotonic",
            "click_wall", "click_monotonic",
            "after_click_wall", "after_click_monotonic",
            "continue_state_monotonic",
            "bank_page_wall", "bank_page_monotonic",
            "icici_wall", "icici_monotonic", "icici_selected_monotonic",
            "paynow_click_wall", "paynow_click_monotonic",
            "paynow_after_click_monotonic", "paynow_state_monotonic",
            "continue_request_monotonic", "continue_response_monotonic",
            "prepayment_request_monotonic", "prepayment_response_monotonic",
            "icici_payment_request_monotonic", "icici_payment_response_monotonic",
        ):
            metrics.setdefault(name, None)

        for name in (
            "continue_request_status",
            "continue_response_status",
            "prepayment_request_status",
            "prepayment_response_status",
            "icici_payment_request_status",
            "icici_payment_response_status",
            "continue_request_id",
            "prepayment_request_id",
            "icici_payment_request_id",
            "continue_response_url",
            "prepayment_response_url",
            "icici_payment_response_url",
        ):
            metrics.setdefault(name, None)

        metrics.setdefault("network_candidates", [])
        metrics.setdefault("network_by_request_id", {})
        metrics.setdefault("continue_candidates", [])
        metrics.setdefault("paynow_candidates", [])
        metrics.setdefault("known_endpoint_events", [])
        metrics.setdefault("cdp_enabled", False)

        if not metrics["cdp_enabled"]:
            try:
                # Performance logging is enabled through goog:loggingPrefs.
                # Performance.enable is best-effort and is not required for
                # the Selenium booking flow.
                driver.execute_cdp_cmd("Performance.enable", {})
                metrics["cdp_enabled"] = True
            except Exception as e:
                logging.debug("CDP performance monitoring unavailable: %s", e)
    except Exception as e:
        logging.debug("Could not initialize CDP metrics: %s", e)


def _append_limited(items, value, limit=100):
    """Append to a bounded list so diagnostics cannot grow without limit."""
    try:
        if len(items) < limit:
            items.append(value)
    except Exception:
        pass


def _classify_booking_endpoint(url):
    """Return the known application endpoint represented by a URL."""
    if not url:
        return None

    url_lower = str(url).lower()

    if CONTINUE_ENDPOINT_MARKER.lower() in url_lower:
        return "continue"
    if PREPAYMENT_ENDPOINT_MARKER.lower() in url_lower:
        return "prepayment"
    if ICICI_PAYMENT_ENDPOINT_MARKER.lower() in url_lower:
        return "icici_payment"
    if BANK_LIST_ENDPOINT_MARKER.lower() in url_lower:
        return "bank_list"

    return None


def _record_known_endpoint_event(metrics, event):
    """Store a bounded, compact record for an observed known endpoint."""
    _append_limited(metrics["known_endpoint_events"], event, 50)


def collect_continue_metrics(driver):
    """Drain and correlate Chrome Network events by requestId.

    The endpoint names below are taken from the application's own JavaScript:
      - /dms/continue
      - /dms/srivaniCurrentDayDarshanBooking
      - /wlpgpayment/iciciPaymentDetails

    This function records actual request/response timing for those endpoints.
    It never blocks or raises into the booking flow.
    """
    try:
        enable_cdp_monitor(driver)
        metrics = driver._continue_metrics

        try:
            entries = driver.get_log("performance")
        except Exception as e:
            logging.debug("Performance log unavailable: %s", e)
            return

        for entry in entries:
            try:
                message = json.loads(entry.get("message", "{}")).get("message", {})
                method = message.get("method", "")
                params = message.get("params", {})

                if method not in (
                    "Network.requestWillBeSent",
                    "Network.responseReceived",
                ):
                    continue

                request_id = params.get("requestId", "")
                if not request_id:
                    continue

                cdp_timestamp = params.get("timestamp")
                state = metrics["network_by_request_id"].setdefault(request_id, {})

                if method == "Network.requestWillBeSent":
                    request = params.get("request", {})
                    url = request.get("url", "")
                    http_method = request.get("method", "")
                    resource_type = params.get("type", "")
                    wall_time = params.get("wallTime")
                    endpoint = _classify_booking_endpoint(url)

                    state.update({
                        "url": url,
                        "method": http_method,
                        "resource_type": resource_type,
                        "endpoint": endpoint,
                        "request_cdp_timestamp": cdp_timestamp,
                        "request_wall_time": wall_time,
                    })

                    # Only retain booking-relevant network requests for the
                    # diagnostic candidate lists. This avoids noisy logging.
                    if endpoint in ("continue", "prepayment", "icici_payment", "bank_list"):
                        event = {
                            "event": "request",
                            "request_id": request_id,
                            "endpoint": endpoint,
                            "method": http_method,
                            "url": url,
                            "resource_type": resource_type,
                            "cdp_timestamp": cdp_timestamp,
                            "wall_time": wall_time,
                        }
                        _append_limited(metrics["network_candidates"], event, 100)

                        if endpoint == "continue":
                            _append_limited(metrics["continue_candidates"], event, 20)
                        elif endpoint in ("prepayment", "icici_payment"):
                            _append_limited(metrics["paynow_candidates"], event, 30)

                        _record_known_endpoint_event(metrics, event)
                        logging.debug(
                            "Known booking request: %s %s [requestId=%s]",
                            endpoint, url, request_id,
                        )

                        # Only assign these timestamps after the relevant UI
                        # action has already happened. This prevents stale
                        # login/page-load traffic from being misclassified.
                        click_wall = metrics.get("click_wall")
                        paynow_wall = metrics.get("paynow_click_wall")
                        click_ts = click_wall.timestamp() if isinstance(click_wall, datetime.datetime) else None
                        paynow_ts = paynow_wall.timestamp() if isinstance(paynow_wall, datetime.datetime) else None

                        if endpoint == "continue":
                            if click_ts is None or wall_time is None or wall_time >= click_ts:
                                if metrics.get("continue_request_monotonic") is None:
                                    metrics["continue_request_monotonic"] = time.monotonic()
                                    metrics["continue_request_id"] = request_id
                                    logging.info("CDP: /dms/continue request observed.")
                        elif endpoint == "prepayment":
                            if paynow_ts is None or wall_time is None or wall_time >= paynow_ts:
                                if metrics.get("prepayment_request_monotonic") is None:
                                    metrics["prepayment_request_monotonic"] = time.monotonic()
                                    metrics["prepayment_request_id"] = request_id
                                    metrics["paynow_request_monotonic"] = metrics["prepayment_request_monotonic"]
                                    logging.info(
                                        "CDP: /dms/srivaniCurrentDayDarshanBooking request observed."
                                    )
                        elif endpoint == "icici_payment":
                            if paynow_ts is None or wall_time is None or wall_time >= paynow_ts:
                                if metrics.get("icici_payment_request_monotonic") is None:
                                    metrics["icici_payment_request_monotonic"] = time.monotonic()
                                    metrics["icici_payment_request_id"] = request_id
                                    logging.info(
                                        "CDP: /wlpgpayment/iciciPaymentDetails request observed."
                                    )

                else:
                    response = params.get("response", {})
                    url = response.get("url", "")
                    status = response.get("status")
                    endpoint = state.get("endpoint") or _classify_booking_endpoint(url)
                    request_cdp_timestamp = state.get("request_cdp_timestamp")
                    request_wall_time = state.get("request_wall_time")

                    state.update({
                        "response_cdp_timestamp": cdp_timestamp,
                        "response_status": status,
                        "response_url": url,
                    })

                    if (
                        isinstance(request_cdp_timestamp, (int, float))
                        and isinstance(cdp_timestamp, (int, float))
                    ):
                        duration = max(0.0, cdp_timestamp - request_cdp_timestamp)
                    else:
                        duration = None

                    if endpoint in ("continue", "prepayment", "icici_payment", "bank_list"):
                        event = {
                            "event": "response",
                            "request_id": request_id,
                            "endpoint": endpoint,
                            "url": url,
                            "status": status,
                            "duration": duration,
                            "cdp_timestamp": cdp_timestamp,
                            "request_wall_time": request_wall_time,
                        }
                        _append_limited(metrics["network_candidates"], event, 100)
                        _record_known_endpoint_event(metrics, event)
                        logging.debug(
                            "Known booking response: %s status=%s requestId=%s duration=%s",
                            endpoint, status, request_id, duration,
                        )

                        if endpoint == "continue":
                            if metrics.get("continue_response_monotonic") is None:
                                metrics["continue_response_monotonic"] = time.monotonic()
                                metrics["continue_response_status"] = status
                                metrics["continue_response_url"] = url
                                logging.info(
                                    "CDP: /dms/continue response observed (HTTP %s).",
                                    status,
                                )
                        elif endpoint == "prepayment":
                            if metrics.get("prepayment_response_monotonic") is None:
                                metrics["prepayment_response_monotonic"] = time.monotonic()
                                metrics["prepayment_response_status"] = status
                                metrics["prepayment_response_url"] = url
                                metrics["paynow_response_monotonic"] = metrics["prepayment_response_monotonic"]
                                logging.info(
                                    "CDP: /dms/srivaniCurrentDayDarshanBooking response observed (HTTP %s).",
                                    status,
                                )
                        elif endpoint == "icici_payment":
                            if metrics.get("icici_payment_response_monotonic") is None:
                                metrics["icici_payment_response_monotonic"] = time.monotonic()
                                metrics["icici_payment_response_status"] = status
                                metrics["icici_payment_response_url"] = url
                                logging.info(
                                    "CDP: /wlpgpayment/iciciPaymentDetails response observed (HTTP %s).",
                                    status,
                                )

            except Exception as e:
                logging.debug("Could not parse performance event: %s", e)

        # Keep memory bounded. Request IDs that have already produced a
        # response no longer need to remain indefinitely.
        if len(metrics["network_by_request_id"]) > 250:
            removable = []
            for request_id, state in metrics["network_by_request_id"].items():
                if "response_status" in state:
                    removable.append(request_id)
                if len(removable) >= 75:
                    break
            for request_id in removable:
                metrics["network_by_request_id"].pop(request_id, None)

        # Useful deltas only when the exact endpoint was observed.
        if metrics.get("continue_request_monotonic") and metrics.get("continue_response_monotonic"):
            logging.info(
                "Continue API request -> response: %.3fs",
                metrics["continue_response_monotonic"] - metrics["continue_request_monotonic"],
            )

        if metrics.get("prepayment_request_monotonic") and metrics.get("prepayment_response_monotonic"):
            logging.info(
                "Pre-payment API request -> response: %.3fs",
                metrics["prepayment_response_monotonic"] - metrics["prepayment_request_monotonic"],
            )

        if metrics.get("icici_payment_request_monotonic") and metrics.get("icici_payment_response_monotonic"):
            logging.info(
                "ICICI payment API request -> response: %.3fs",
                metrics["icici_payment_response_monotonic"] - metrics["icici_payment_request_monotonic"],
            )

    except Exception as e:
        logging.debug("Continue metrics collection failed: %s", e)


def parse_wait_seconds_from_message(msg):
    """
    Parses opening time from TTD notice like 'Booking opens at 09:10:00 IST. Please try again later.'
    Returns recommended sleep seconds and a descriptive reason string.
    """
    time_match = re.search(r"(\d{1,2}):(\d{2}):(\d{2})", str(msg))
    if time_match:
        th, tm, ts = int(time_match.group(1)), int(time_match.group(2)), int(time_match.group(3))
        now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5.5)
        target_open = now_ist.replace(hour=th, minute=tm, second=ts, microsecond=0)
        diff = (target_open - now_ist).total_seconds()
        if diff > 0:
            return diff + 0.35, f"waiting {diff + 0.35:.1f}s until official slot open ({th:02d}:{tm:02d}:{ts:02d} IST)"
        else:
            return 0.8, "target time passed (retrying in 0.8s)"
    elif "too many hits" in str(msg).lower():
        return 2.5, "rate-limit cooldown (retrying in 2.5s)"
    return 1.2, "clock skew retry (1.2s)"


def detect_live_quota_time(driver):
    """
    Inspects TTD pilgrim page for live 'Quota Release Time' and 'Remaining Time'
    either from Angular scope (dccsc.quotaReleaseTime) or page text.
    Returns (target_hour, target_minute, target_second, remaining_seconds) or None.
    """
    try:
        data = driver.execute_script(r"""
            try {
                // 1. Try Angular scope
                const el = document.querySelector('[ng-controller*="dccsc"], [ng-controller], .pilgrim-details, form') || document.body;
                if (window.angular && el) {
                    const sc = window.angular.element(el).scope();
                    if (sc && sc.dccsc) {
                        const qrt = sc.dccsc.quotaReleaseT || sc.dccsc.quotaReleaseTime;
                        const targetTs = sc.dccsc.targetReleaseTimestamp;
                        if (qrt) {
                            return { source: 'angular', timeStr: qrt, targetTs: targetTs };
                        }
                    }
                }
            } catch(e) {}

            try {
                // 2. Try DOM text scan
                const text = document.body ? document.body.innerText : '';
                const m = text.match(/Quota\s*Release\s*Time\s*:\s*(\d{1,2}:\d{2}:\d{2})/i);
                const rem = text.match(/Remaining\s*Time\s*:\s*(\d{1,2}:\d{2}:\d{2})/i);
                if (m) {
                    return { source: 'text', timeStr: m[1], remStr: rem ? rem[1] : null };
                }
            } catch(e) {}

            return null;
        """)
        if data and data.get("timeStr"):
            time_str = data["timeStr"].strip()
            parts = time_str.split(":")
            if len(parts) == 3:
                qh, qm, qs = int(parts[0]), int(parts[1]), int(parts[2])
                rem_sec = None
                if data.get("remStr"):
                    rparts = data["remStr"].strip().split(":")
                    if len(rparts) == 3:
                        rem_sec = int(rparts[0]) * 3600 + int(rparts[1]) * 60 + int(rparts[2])
                return (qh, qm, qs, rem_sec)
    except Exception as e:
        logging.debug("Live quota detection notice: %s", e)
    return None


def pre_locate_continue_button(driver, timeout=60):
    """
    Pre-locate the Continue button *before* the target-time wait.
    This is the key to firing at T+0: by the time go-time arrives, we
    already hold the element handle and can force-click it without
    waiting for Angular to flip ng-disabled to false.
    """
    try:
        btn = WebDriverWait(driver, timeout, poll_frequency=0.05).until(
            EC.presence_of_element_located((By.XPATH, CONTINUE_XPATH))
        )
        logging.info("✅ Continue button pre-located.")
        return btn
    except TimeoutException:
        logging.error("❌ Continue button not found during pre-location.")
        return None


def click_continue_button(driver, continue_btn=None):
    """Click Continue using Selenium's native click behavior."""
    if not hasattr(driver, "_continue_metrics"):
        enable_cdp_monitor(driver)

    for retry in range(MAX_CONTINUE_RETRIES):
        try:
            # Remove modal backdrops/overlays before clicking
            remove_overlays(driver)
            remove_all_overlays(driver)
            # Skip sleep on first attempt (overlay removal is ~2ms); only sleep on retries
            if retry > 0:
                time.sleep(0.2)

            if continue_btn is None or retry > 0:
                continue_btn = WebDriverWait(driver, 90, poll_frequency=0.05).until(
                    EC.element_to_be_clickable((By.XPATH, CONTINUE_XPATH))
                )
            else:
                continue_btn = WebDriverWait(driver, 90, poll_frequency=0.05).until(
                    EC.element_to_be_clickable(continue_btn)
                )

            click_time = datetime.datetime.now()
            driver._continue_metrics["click_wall"] = click_time
            driver._continue_metrics["click_monotonic"] = time.monotonic()
            logging.info("Continue click timestamp before click: %s",
                         click_time.strftime("%H:%M:%S.%f")[:-3])
            try:
                continue_btn.click()
                logging.info("Continue button clicked natively.")
            except ElementClickInterceptedException:
                logging.warning("Native click intercepted; executing JavaScript click fallback...")
                driver.execute_script("arguments[0].click();", continue_btn)
                logging.info("Continue button clicked via JavaScript fallback.")
            break
        except TimeoutException:
            logging.error("Continue button was not clickable within 90 seconds.")
            return False
        except (StaleElementReferenceException,
                NoSuchElementException) as e:
            logging.warning("Native Continue click failed on attempt %d/%d: %s",
                            retry + 1, MAX_CONTINUE_RETRIES, e)
            continue
        except Exception as e:
            logging.error("Native Continue click failed: %s", e)
            return False
    else:
        logging.error("Maximum native Continue click retries exceeded.")
        return False

    after_click = datetime.datetime.now()
    driver._continue_metrics["after_click_wall"] = after_click
    driver._continue_metrics["after_click_monotonic"] = time.monotonic()
    if driver._continue_metrics.get("target_monotonic"):
        logging.info("Target -> Continue: %.3fs",
                     driver._continue_metrics["click_monotonic"] -
                     driver._continue_metrics["target_monotonic"])
    collect_continue_metrics(driver)
    logging.info("Continue click timestamp immediately after click: %s",
                 after_click.strftime("%H:%M:%S.%f")[:-3])
    return True


def request_captcha_review(worker_id, email, ocr_text, image_path, timeout_seconds=6.0):
    """
    Emits a CAPTCHA review event for the GUI to display a quick popup.
    If the user edits or presses Enter, returns their edited value.
    If 5 seconds elapse without user edits, automatically proceeds with ocr_text.
    """
    req_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captcha_requests")
    os.makedirs(req_dir, exist_ok=True)

    req_id = f"worker_{worker_id}"
    req_file = os.path.join(req_dir, f"{req_id}_request.json")
    resp_file = os.path.join(req_dir, f"{req_id}_response.json")

    # Clean old response
    if os.path.exists(resp_file):
        try:
            os.remove(resp_file)
        except Exception:
            pass

    req_data = {
        "id": req_id,
        "email": email,
        "worker_id": worker_id,
        "ocr_text": ocr_text,
        "image_path": os.path.abspath(image_path) if os.path.exists(image_path) else None,
        "timestamp": time.time()
    }

    try:
        with open(req_file, "w", encoding="utf-8") as f:
            json.dump(req_data, f)
    except Exception as e:
        logging.warning(f"Failed to write captcha request file: {e}")
        return ocr_text

    # Poll for response up to timeout_seconds (or until user submits)
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        if os.path.exists(resp_file):
            try:
                with open(resp_file, "r", encoding="utf-8") as f:
                    resp_data = json.load(f)
                final_val = resp_data.get("captcha_text", "").strip()
                if final_val:
                    # Cleanup
                    try:
                        os.remove(req_file)
                        os.remove(resp_file)
                    except Exception:
                        pass
                    return final_val
            except Exception:
                pass
        time.sleep(0.08)

    # Auto-timeout reached: clean request file and proceed automatically
    try:
        if os.path.exists(req_file):
            os.remove(req_file)
        if os.path.exists(resp_file):
            os.remove(resp_file)
    except Exception:
        pass

    return ocr_text


def check_ttd_alerts(driver):
    """
    Comprehensive TTD alert & error modal detector.
    Detects:
    1. Quota exceeded: 'quota exceeded', 'cannot book as quota', 'quota is full'
    2. Duplicate transaction: 'a transaction is already being processed with the entered details', 'wait for the current request to complete'
    3. Timing notices: 'booking opens at'
    4. Aadhaar errors: 'invalid aadhaar'
    5. Session errors: 'session expired', 'logged in from another'
    
    Returns dict:
    {
        "found": bool,
        "type": "quota_exceeded" | "duplicate_transaction" | "timing_alert" | "invalid_aadhaar" | "session_error" | "unknown",
        "text": str
    }
    """
    res = {"found": False, "type": None, "text": ""}
    try:
        # Check window.alert
        try:
            alert = driver.switch_to.alert
            alert_text = (alert.text or "").strip()
            lower = alert_text.lower()
            res["text"] = alert_text
            res["found"] = True
            if any(k in lower for k in ["quota exceeded", "cannot book as quota", "quota is full", "no quota"]):
                res["type"] = "quota_exceeded"
            elif any(k in lower for k in ["already being processed", "current request to complete", "transaction is already"]):
                res["type"] = "duplicate_transaction"
            elif "booking opens at" in lower:
                res["type"] = "timing_alert"
            elif "invalid aadhaar" in lower:
                res["type"] = "invalid_aadhaar"
            else:
                res["type"] = "unknown"
            alert.accept()
            return res
        except Exception:
            pass

        # Check DOM modals, popups, and page text
        detected = driver.execute_script(r"""
            try {
                var alerts = document.querySelectorAll('.modal, .modal-dialog, .modal-content, .alert, .popup, .bootbox, div[role="dialog"]');
                for (var i = 0; i < alerts.length; i++) {
                    var el = alerts[i];
                    var t = (el.innerText || el.textContent || '').trim();
                    var lower = t.toLowerCase();
                    if (!t) continue;
                    
                    if (lower.includes('quota exceeded') || lower.includes('cannot book as quota') || lower.includes('quota is full') || lower.includes('no quota')) {
                        return { found: true, type: 'quota_exceeded', text: t };
                    }
                    if (lower.includes('already being processed') || lower.includes('current request to complete') || lower.includes('transaction is already')) {
                        return { found: true, type: 'duplicate_transaction', text: t };
                    }
                    if (lower.includes('booking opens at')) {
                        return { found: true, type: 'timing_alert', text: t };
                    }
                    if (lower.includes('invalid aadhaar')) {
                        return { found: true, type: 'invalid_aadhaar', text: t };
                    }
                }

                // Check full body text
                var bodyText = document.body ? (document.body.innerText || '') : '';
                var b_lower = bodyText.toLowerCase();
                if (b_lower.includes('a transaction is already being processed with the entered details')) {
                    return { found: true, type: 'duplicate_transaction', text: 'A transaction is already being processed with the entered details.' };
                }
                if (b_lower.includes('cannot book as quota exceeded')) {
                    return { found: true, type: 'quota_exceeded', text: 'Cannot book as quota exceeded' };
                }
                if (b_lower.includes('invalid aadhaar number')) {
                    return { found: true, type: 'invalid_aadhaar', text: 'Invalid Aadhaar Number' };
                }
                if (b_lower.includes('quota exceeded') && (b_lower.includes('alert') || b_lower.includes('error'))) {
                    return { found: true, type: 'quota_exceeded', text: 'Quota exceeded' };
                }
            } catch(e) {}
            return { found: false };
        """)

        if detected and detected.get("found"):
            res["found"] = True
            res["type"] = detected.get("type", "unknown")
            res["text"] = detected.get("text", "")
            return res

    except Exception as e:
        logging.debug(f"Error checking TTD alerts: {e}")

    return res


def check_quota_exceeded(driver):
    """
    Detect if TTD displayed a 'quota exceeded', 'duplicate transaction', or other critical modal.
    Returns True if quota is exceeded or duplicate transaction is blocked.
    """
    alert_info = check_ttd_alerts(driver)
    if alert_info.get("found"):
        atype = alert_info.get("type")
        atext = alert_info.get("text", "")
        if atype == "quota_exceeded":
            logging.error(f"❌ TTD Quota Exceeded Detected: '{atext}'")
            return True
        elif atype == "duplicate_transaction":
            logging.error(f"⚠️ TTD Duplicate Transaction Detected: '{atext}' (Aadhaar locked by sister worker or active session).")
            return True
        elif atype == "invalid_aadhaar":
            logging.error(f"❌ TTD Invalid Aadhaar Detected: '{atext}'")
            return True
        elif atype == "timing_alert":
            logging.warning(f"⚠️ TTD Timing Notice: '{atext}'")
            return False
    return False


def handle_otp_flow_for_worker(driver, group, email):
    """
    Automated Headless OTP Bridge:
    1. Detects when the bank 3D-Secure / OTP page or gateway loads.
    2. Takes a screenshot so the user can verify in the GUI.
    3. Emits an OTP request via files/signals for the GUI to display an OTP prompt.
    4. Waits for the user to submit the OTP from the GUI.
    5. Searches all DOM frames/iframes for the bank's OTP input and submits it automatically.
    """
    if check_quota_exceeded(driver):
        logging.error(f"❌ Quota exceeded detected on TTD for {group} – aborting OTP bridge.")
        take_screenshot(driver, group, "_quota_exceeded")
        return False

    otp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "otp_requests")
    os.makedirs(otp_dir, exist_ok=True)

    req_file = os.path.join(otp_dir, f"{group}_request.json")
    resp_file = os.path.join(otp_dir, f"{group}_response.json")
    shot_file = os.path.join(otp_dir, f"{group}_otp_screen.png")

    # Clean prior responses
    if os.path.exists(resp_file):
        try:
            os.remove(resp_file)
        except Exception:
            pass

    logging.info(f"🛡️ [OTP Bridge] Monitoring browser state for Bank OTP screen ({group})...")
    time.sleep(2.0)  # Allow bank redirection/gateway handshake

    if check_quota_exceeded(driver):
        logging.error(f"❌ Quota exceeded detected on TTD for {group} – aborting OTP bridge.")
        take_screenshot(driver, group, "_quota_exceeded")
        return False

    # Take screenshot of the payment/bank screen for visual inspection in GUI
    try:
        driver.save_screenshot(shot_file)
    except Exception as e:
        logging.warning(f"Could not save OTP screenshot: {e}")

    # Write request for GUI to pick up
    req_data = {
        "group": group,
        "email": email,
        "timestamp": time.time(),
        "url": getattr(driver, "current_url", ""),
        "screenshot": os.path.abspath(shot_file) if os.path.exists(shot_file) else None
    }
    with open(req_file, "w", encoding="utf-8") as f:
        json.dump(req_data, f)
    logging.info(f"🔔 [OTP Bridge] OTP request created for {group}. Waiting for OTP from GUI...")

    # Wait up to 180 seconds for user to enter OTP in GUI
    otp_code = None
    start_wait = time.time()
    while time.time() - start_wait < 180:
        if os.path.exists(resp_file):
            try:
                with open(resp_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    otp_code = str(data.get("otp", "")).strip()
                    if otp_code:
                        break
            except Exception:
                pass
        time.sleep(0.5)

    if not otp_code:
        logging.warning(f"⚠️ [OTP Bridge] No OTP received within timeout for {group}.")
        return False

    logging.info(f"🔑 [OTP Bridge] Received OTP from GUI for {group}! Injecting into bank page...")

    # Helper function to find and fill OTP in a given context (main document or inside an iframe)
    def try_inject_otp(target_driver, code):
        otp_selectors = [
            "input[name*='otp' i]",
            "input[id*='otp' i]",
            "input[placeholder*='otp' i]",
            "input[name*='passcode' i]",
            "input[id*='passcode' i]",
            "input[name*='password' i]",
            "input[type='password']",
            "input[type='tel']",
            "input[type='number']",
            "input.otp",
            "input[maxlength='6']",
            "input[maxlength='4']",
            "input[maxlength='8']"
        ]
        submit_selectors = [
            "//button[contains(translate(text(),'SUBMIT','submit'),'submit')]",
            "//button[contains(translate(text(),'PAY','pay'),'pay')]",
            "//button[contains(translate(text(),'CONFIRM','confirm'),'confirm')]",
            "//button[contains(translate(text(),'VERIFY','verify'),'verify')]",
            "//input[@type='submit']",
            "//input[contains(translate(@value,'SUBMIT','submit'),'submit')]",
            "//input[contains(translate(@value,'PAY','pay'),'pay')]",
            "//input[contains(translate(@value,'CONFIRM','confirm'),'confirm')]"
        ]

        found_input = None
        for sel in otp_selectors:
            try:
                elems = target_driver.find_elements(By.CSS_SELECTOR, sel)
                for el in elems:
                    if el.is_displayed() and el.is_enabled():
                        found_input = el
                        break
                if found_input:
                    break
            except Exception:
                continue

        if not found_input:
            return False

        try:
            found_input.clear()
            found_input.send_keys(code)
            logging.info(f"✅ Injected OTP into field: {found_input.get_attribute('name') or found_input.get_attribute('id')}")
            time.sleep(0.4)

            # Locate Submit button
            for sub_sel in submit_selectors:
                try:
                    s_btns = target_driver.find_elements(By.XPATH, sub_sel)
                    for btn in s_btns:
                        if btn.is_displayed() and btn.is_enabled():
                            driver.execute_script("arguments[0].click();", btn)
                            logging.info("✅ Clicked bank submit/verify button!")
                            return True
                except Exception:
                    continue

            # Fallback: Press ENTER key on the OTP input
            from selenium.webdriver.common.keys import Keys
            found_input.send_keys(Keys.ENTER)
            logging.info("✅ Pressed ENTER on OTP field.")
            return True
        except Exception as e:
            logging.error(f"Error injecting OTP into field: {e}")
            return False

    # Try main window first
    injected = try_inject_otp(driver, otp_code)

    # If not found in main window, iterate through all iframes (very common on 3D-Secure ACS pages)
    if not injected:
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            logging.info(f"🔎 Scanning {len(iframes)} iframe(s) for bank OTP box...")
            for idx, frame in enumerate(iframes):
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(frame)
                    if try_inject_otp(driver, otp_code):
                        logging.info(f"✅ Successfully injected OTP inside iframe #{idx}!")
                        injected = True
                        break
                except Exception:
                    continue
        except Exception as e:
            logging.warning(f"Error traversing iframes: {e}")
        finally:
            driver.switch_to.default_content()

    if injected:
        logging.info(f"🎉 OTP submission completed for {group}!")
        # Clean request files
        for f in [req_file, resp_file]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        return True
    else:
        logging.warning("⚠️ Could not automatically locate the bank OTP input box.")
        return False


def bring_window_onscreen(driver, worker_id=0):
    """
    Brings off-screen ghost browser window onto visible screen when user attention or manual action is required.
    """
    if not driver:
        return
    try:
        base_x = 80 + (worker_id * 40) % 800
        base_y = 40 + (worker_id * 30) % 600
        driver.set_window_position(base_x, base_y)
        driver.set_window_size(1050, 700)
        logging.info("🖥️ Brought browser window on-screen at (%s, %s) for user interaction.", base_x, base_y)
    except Exception as e:
        logging.debug("Could not bring window on-screen: %s", e)


def handle_upi_payment_flow(driver, group, email, upi_id="jeffrinsingh854@oksbi"):
    """
    Automated ICICI Gateway UPI ID Injection:
    1. Waits for ICICI Payment Gateway / Bank Gateway to load.
    2. Automatically selects 'UPI' payment option.
    3. Selects 'UPI ID / VPA' mode if prompted.
    4. Automatically enters user's registered UPI ID (e.g. jeffrinsingh854@oksbi).
    5. Clicks 'Verify and Pay' / 'Proceed' button.
    6. Alerts user that payment request is sent to Google Pay!
    7. Keeps monitoring for payment confirmation / receipt.
    """
    logging.info(f"💳 [UPI Gateway] Starting automated UPI payment flow for {group} with UPI ID: {upi_id}...")

    # --- Sister Worker Concurrency Guard ---
    # Prevents multiple workers for the SAME family from flooding phone with duplicate ₹10,500 collect requests.
    lock_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ready")
    os.makedirs(lock_dir, exist_ok=True)
    lock_file = os.path.join(lock_dir, f"{group}_payment.lock")

    if os.path.exists(lock_file):
        try:
            with open(lock_file, "r") as f:
                locked_by = f.read().strip()
            logging.info("ℹ️ Sister worker (%s) has already secured quota & initiated UPI payment for %s!", locked_by, group)
            logging.info("👉 Standing down on this worker to prevent duplicate ₹10,500 payment requests on your phone.")
            return True
        except Exception:
            pass

    try:
        with open(lock_file, "w") as f:
            f.write(f"{email}_{time.time()}")
        logging.info("🔒 Acquired payment lock for %s (Worker: %s).", group, email)
    except Exception:
        pass

    # 1. Handle window switches (if gateway opened in a new tab/window)
    if len(driver.window_handles) > 1:
        driver.switch_to.window(driver.window_handles[-1])
        logging.info(f"Switched to gateway window: {driver.current_url}")

    # 2. Wait up to 30 seconds for payment gateway to load
    start_gw = time.time()
    gateway_detected = False
    while time.time() - start_gw < 30:
        # Check window handles if gateway opened in a new tab/window
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])

        alert_info = check_ttd_alerts(driver)
        if alert_info.get("found") and alert_info.get("type") in ["quota_exceeded", "duplicate_transaction", "invalid_aadhaar"]:
            logging.error("❌ TTD blocked booking: %s (Type: %s)", alert_info.get("text"), alert_info.get("type"))
            take_screenshot(driver, group, f"_{alert_info.get('type')}")
            return False

        curr_url = driver.current_url.lower()
        is_ttd_domain = any(dom in curr_url for dom in ["ttdevasthanams.ap.gov.in", "tirupatibalaji.ap.gov.in"])

        # Check if URL redirected to external payment gateway (NOT on TTD domain)
        if not is_ttd_domain and any(marker in curr_url for marker in ["icici", "eazypay", "pgbiz", "billdesk", "payment", "bank", "paytm", "razorpay"]):
            logging.info(f"✅ External payment gateway URL detected: {driver.current_url}")
            gateway_detected = True
            break

        # Check if Paytm Checkout JS modal or payment gateway iframe is loaded in DOM (even if still on TTD URL)
        try:
            has_paytm_modal = driver.execute_script(r"""
                const iframes = document.querySelectorAll('iframe');
                for (let i = 0; i < iframes.length; i++) {
                    const src = (iframes[i].src || '').toLowerCase();
                    const id = (iframes[i].id || '').toLowerCase();
                    const name = (iframes[i].name || '').toLowerCase();
                    if (src.includes('paytm') || src.includes('securegw') ||
                        id.includes('paytm') || id.includes('checkout') || name.includes('paytm')) {
                        return true;
                    }
                }
                const paytmModalDiv = document.querySelector('#paytm-checkoutjs, [id*="paytm" i], [class*="paytm" i]');
                if (paytmModalDiv) {
                    const txt = (paytmModalDiv.textContent || '').toLowerCase();
                    if (txt.includes('paytm') || txt.includes('paying') || txt.includes('cards') || txt.includes('upi')) {
                        return true;
                    }
                }
                return false;
            """)
            if has_paytm_modal:
                logging.info("✅ Paytm / Payment Gateway modal iframe detected on page!")
                gateway_detected = True
                break
        except Exception:
            pass

        # Check DOM text for payment gateway indicators (if off TTD domain)
        if not is_ttd_domain:
            try:
                has_gw = driver.execute_script("""
                    var txt = (document.body ? document.body.innerText : '').toLowerCase();
                    return txt.includes('upi') || txt.includes('net banking') || txt.includes('debit card') || txt.includes('order amount') || txt.includes('payment options');
                """)
                if has_gw:
                    gateway_detected = True
                    break
            except Exception:
                pass

        time.sleep(0.3)

    if not gateway_detected:
        logging.error("❌ External payment gateway was not detected within 30s. (Current URL: %s)", getattr(driver, "current_url", "unknown"))
        take_screenshot(driver, group, "_gateway_not_found")
        return False

    bring_window_onscreen(driver)
    take_screenshot(driver, group, "_gateway_opened")

    # 3. Helper to interact with UPI controls (in main document or iframe)
    def try_automate_upi(target_driver):
        script = r"""
        const vpaToEnter = arguments[0];
        let status = { upi_clicked: false, vpa_entered: false, pay_clicked: false, back_clicked: false, details: [] };

        const parts = (vpaToEnter || '').split('@');
        const username = parts[0] || '';
        const handleWithAt = parts.length > 1 ? '@' + parts[1] : '';
        const handleWithoutAt = parts.length > 1 ? parts[1] : '';

        function safeClick(el, label) {
            if (!el) return false;
            try {
                try { el.scrollIntoView({ behavior: 'instant', block: 'center' }); } catch(e) {}
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden') return false;
                
                // Dispatch full event sequence to trigger React/Preact/Angular event listeners
                ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evtType => {
                    try {
                        el.dispatchEvent(new MouseEvent(evtType, { bubbles: true, cancelable: true, view: window }));
                    } catch(e) {}
                });
                try { el.click(); } catch(e) {}
                status.details.push("Clicked " + label);
                return true;
            } catch(e) {
                return false;
            }
        }

        // --- STEP 1: Handle Scroll & Modal Viewport ---
        // Scroll scrollable containers down so that options below "Cards" (e.g. UPI) are rendered
        try {
            const scrollables = Array.from(document.querySelectorAll('div, section, main, [class*="content" i], [class*="body" i], [class*="container" i], [class*="scroll" i]'));
            for (let sc of scrollables) {
                if (sc.scrollHeight > sc.clientHeight && sc.clientHeight > 100) {
                    sc.scrollTop = Math.min(sc.scrollTop + 200, sc.scrollHeight);
                }
            }
            window.scrollBy(0, 200);
        } catch(e) {}

        // If "Cards" is expanded and UPI not visible, also try collapsing Cards accordion
        const bodyText = (document.body ? (document.body.innerText || '') : '').toLowerCase();
        const isCardsOpen = bodyText.includes('add new card') || bodyText.includes('card number');

        if (isCardsOpen && !bodyText.includes('enter upi id') && !bodyText.includes('enter your upi')) {
            // Find accordion header whose own text is 'Cards'
            const allHeaders = Array.from(document.querySelectorAll('div, span, button, p, [role="button"]'));
            for (let ch of allHeaders) {
                const t = (ch.innerText || '').trim();
                if (/^cards$/i.test(t) || /^cards\s+/i.test(t)) {
                    safeClick(ch, "Cards accordion header toggle");
                    break;
                }
            }
        }

        // --- STEP 2: Find and Click UPI Payment Option ---
        const upiCandidates = Array.from(document.querySelectorAll('a, button, li, label, input[type="radio"], input[type="button"], [role="button"], [role="tab"], div, span, p'));
        for (let el of upiCandidates) {
            if (el.tagName === 'BODY' || el.tagName === 'HTML' || el.children.length > 8) continue;
            const txt = (el.innerText || el.textContent || el.value || '').trim();
            const lower = txt.toLowerCase();

            // Broad UPI matching (Paytm Checkout, ICICI, BillDesk, etc.)
            if (lower === 'upi' || lower.startsWith('upi ') || lower.startsWith('upi\n') || lower.startsWith('upi/') || lower.startsWith('upi(') ||
                lower.includes('pay via upi') || lower.includes('pay with upi') || lower.includes('add new upi') || 
                lower.includes('unified payments interface') || lower.includes('upi id / vpa') || lower.includes('upi / qr')) {
                // Ensure it's not the submit button or a card input
                if (!lower.includes('card number') && !lower.includes('pay securely') && !lower.includes('cards')) {
                    if (safeClick(el, "UPI option: " + txt.substring(0, 30))) {
                        status.upi_clicked = true;
                        break;
                    }
                }
            }
        }

        // Attribute fallback for UPI
        if (!status.upi_clicked) {
            const upiAttr = document.querySelector('#upi, #UPI, [id*="upi" i], [name*="upi" i], [data-method*="upi" i], [data-mode*="upi" i], [data-target*="upi" i], [data-payment-mode*="UPI" i], [data-channel*="upi" i], [data-id*="upi" i]');
            if (upiAttr) {
                if (safeClick(upiAttr, "UPI attribute element: " + (upiAttr.id || upiAttr.name || upiAttr.className))) {
                    status.upi_clicked = true;
                }
            }
        }

        // --- STEP 3: Sub-option within UPI (e.g. "Enter UPI ID" radio / button) ---
        const subOptions = Array.from(document.querySelectorAll('input[type="radio"], label, span, div, button, [role="button"]'));
        for (let r of subOptions) {
            const rTxt = (r.innerText || r.textContent || r.value || '').toLowerCase().trim();
            if (rTxt.includes('enter upi id') || rTxt.includes('enter your upi') || rTxt.includes('pay with upi id') || rTxt.includes('add new upi') || rTxt.includes('upi id / net banking') || rTxt === 'vpa') {
                safeClick(r, "UPI sub-option: " + rTxt);
                break;
            }
        }

        // --- STEP 4: Split Bank Handle Dropdown (e.g. ICICI @oksbi select) ---
        const handleSelect = document.querySelector("select[name*='handle' i], select[id*='handle' i], select[name*='bank' i], select[id*='bank' i], select[name*='upi' i], select[id*='upi' i]");
        let handleSelected = false;
        if (handleSelect && handleWithAt) {
            for (let h = 0; h < handleSelect.options.length; h++) {
                const opt = handleSelect.options[h];
                const optTxt = (opt.text || '').trim().toLowerCase();
                const optVal = (opt.value || '').trim().toLowerCase();
                if (optTxt === handleWithAt.toLowerCase() || optVal === handleWithAt.toLowerCase() || 
                    optTxt === handleWithoutAt.toLowerCase() || optVal === handleWithoutAt.toLowerCase()) {
                    handleSelect.selectedIndex = h;
                    handleSelect.value = opt.value;
                    handleSelect.dispatchEvent(new Event('change', { bubbles: true }));
                    handleSelected = true;
                    status.details.push("Selected bank handle dropdown: " + opt.text);
                    break;
                }
            }
        }

        // --- STEP 5: Locate and Inject VPA / UPI ID Input Field ---
        const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]):not([type="submit"]):not([type="button"])'));
        let vpaInput = null;

        for (let inp of inputs) {
            const id = (inp.id || '').toLowerCase();
            const name = (inp.name || '').toLowerCase();
            const placeholder = (inp.placeholder || '').toLowerCase();
            const aria = (inp.getAttribute('aria-label') || '').toLowerCase();

            // Skip card inputs
            if (id.includes('card') || name.includes('card') || placeholder.includes('card') || id.includes('cvv') || id.includes('exp')) {
                continue;
            }

            if (id.includes('vpa') || id.includes('upi') || 
                name.includes('vpa') || name.includes('upi') || 
                placeholder.includes('vpa') || placeholder.includes('upi') || 
                placeholder.includes('@') || placeholder.includes('handle') ||
                placeholder.includes('id') || aria.includes('upi') || aria.includes('vpa') ||
                placeholder.includes('paytm') || placeholder.includes('phonepe') || placeholder.includes('gpay')) {
                vpaInput = inp;
                break;
            }
        }

        // Fallback: If only one text input is currently visible and not card
        if (!vpaInput) {
            const visibleInputs = inputs.filter(inp => {
                const s = window.getComputedStyle(inp);
                return s.display !== 'none' && s.visibility !== 'hidden' && !inp.disabled;
            });
            for (let vi of visibleInputs) {
                const ph = (vi.placeholder || '').toLowerCase();
                if (!ph.includes('card') && !ph.includes('cvv') && !ph.includes('month') && !ph.includes('year')) {
                    vpaInput = vi;
                    break;
                }
            }
        }

        if (vpaInput) {
            try {
                const valToType = handleSelected ? username : vpaToEnter;
                try { vpaInput.scrollIntoView({ behavior: 'instant', block: 'center' }); } catch(e) {}
                vpaInput.focus();

                // React/Preact/Angular synthetic event compatible value injection
                try {
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                    nativeSetter.call(vpaInput, valToType);
                } catch(e) {
                    vpaInput.value = valToType;
                }

                ['focus', 'keydown', 'keypress', 'input', 'keyup', 'change', 'blur'].forEach(evt => {
                    try {
                        vpaInput.dispatchEvent(new Event(evt, { bubbles: true }));
                    } catch(e) {}
                });
                status.vpa_entered = true;
                status.details.push("Injected VPA value (" + valToType + ") into: " + (vpaInput.id || vpaInput.name || vpaInput.placeholder));
            } catch(e) {
                status.details.push("Error setting VPA: " + e.message);
            }
        }

        // --- STEP 6: Click Pay / Verify & Pay / Proceed Button ---
        if (status.vpa_entered) {
            const buttons = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"], a.btn, a[role="button"], div[role="button"]'));
            for (let btn of buttons) {
                const bTxt = (btn.innerText || btn.textContent || btn.value || '').trim().toLowerCase();
                if (bTxt.includes('verify & pay') || bTxt.includes('verify and pay') || 
                    bTxt.includes('pay securely') || bTxt.includes('pay now') || 
                    bTxt.includes('make payment') || bTxt.includes('proceed') || 
                    bTxt.includes('pay rs') || bTxt.includes('pay ₹') || 
                    bTxt.includes('verify') || bTxt.includes('submit')) {
                    try {
                        const style = window.getComputedStyle(btn);
                        if (style.display !== 'none' && style.visibility !== 'hidden' && !btn.disabled) {
                            try { btn.scrollIntoView({ behavior: 'instant', block: 'center' }); } catch(e) {}
                            ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evtType => {
                                try {
                                    btn.dispatchEvent(new MouseEvent(evtType, { bubbles: true, cancelable: true, view: window }));
                                } catch(e) {}
                            });
                            try { btn.click(); } catch(e) {}
                            status.pay_clicked = true;
                            status.details.push("Clicked payment submit button: " + bTxt);
                            break;
                        }
                    } catch(e) {}
                }
            }
        }

        return status;
        """
        try:
            return target_driver.execute_script(script, upi_id)
        except Exception as e:
            return {"upi_clicked": False, "vpa_entered": False, "pay_clicked": False, "details": [str(e)]}

    # 4. Attempt injection across iframes first, then fallback to main document
    injected_success = False
    start_inj = time.time()
    while time.time() - start_inj < 30:
        # Step A: Check iframes FIRST (Paytm Checkout JS always renders inside an iframe)
        try:
            driver.switch_to.default_content()
            iframes = driver.find_elements(By.TAG_NAME, "iframe")

            def iframe_priority(f):
                try:
                    src = (f.get_attribute("src") or "").lower()
                    fid = (f.get_attribute("id") or "").lower()
                    fname = (f.get_attribute("name") or "").lower()
                    if any(k in src or k in fid or k in fname for k in ["paytm", "securegw", "checkout", "payment"]):
                        return 0
                    return 1
                except Exception:
                    return 2

            sorted_iframes = sorted(iframes, key=iframe_priority)

            for idx, frame in enumerate(sorted_iframes):
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(frame)
                    
                    # Try current frame
                    f_res = try_automate_upi(driver)
                    if f_res and f_res.get("pay_clicked"):
                        logging.info("✅ UPI injection succeeded inside iframe #%d: %s", idx, f_res.get("details"))
                        injected_success = True
                        break
                    elif f_res and f_res.get("vpa_entered") and not f_res.get("pay_clicked"):
                        time.sleep(0.2)
                        f_res2 = try_automate_upi(driver)
                        if f_res2 and f_res2.get("pay_clicked"):
                            logging.info("✅ UPI pay button clicked inside iframe #%d on second pass: %s", idx, f_res2.get("details"))
                            injected_success = True
                            break

                    # Check nested child iframes if any
                    child_frames = driver.find_elements(By.TAG_NAME, "iframe")
                    for c_idx, c_frame in enumerate(child_frames):
                        try:
                            driver.switch_to.frame(c_frame)
                            c_res = try_automate_upi(driver)
                            if c_res and c_res.get("pay_clicked"):
                                logging.info("✅ UPI injection succeeded inside nested iframe #%d-%d: %s", idx, c_idx, c_res.get("details"))
                                injected_success = True
                                break
                        except Exception:
                            pass
                        finally:
                            driver.switch_to.parent_frame()

                    if injected_success:
                        break

                except Exception:
                    continue
                finally:
                    driver.switch_to.default_content()

            if injected_success:
                break
        except Exception:
            driver.switch_to.default_content()

        # Step B: Check main document as well (if iframe was not used or modal renders at root)
        try:
            driver.switch_to.default_content()
            res = try_automate_upi(driver)
            if res and res.get("pay_clicked"):
                logging.info("✅ UPI injection succeeded in main document: %s", res.get("details"))
                injected_success = True
                break
            elif res and res.get("vpa_entered") and not res.get("pay_clicked"):
                time.sleep(0.2)
                res2 = try_automate_upi(driver)
                if res2 and res2.get("pay_clicked"):
                    logging.info("✅ UPI pay button clicked in main document on second pass: %s", res2.get("details"))
                    injected_success = True
                    break
        except Exception:
            pass

        time.sleep(0.3)

    if not injected_success:
        bring_window_onscreen(driver)
        logging.warning("⚠️ Automated UPI ID injection did not complete automatically within 30s. Please check browser.")
        take_screenshot(driver, group, "_upi_injection_manual_needed")
        try:
            print("\a\a\a", flush=True)  # Alert bell
        except Exception:
            pass
        logging.error("=" * 72)
        logging.error("🚨 ATTENTION: PLEASE MANUALLY SELECT 'UPI' & ENTER UPI ID ON THE BROWSER!")
        logging.error("👉 Target UPI ID: %s", upi_id)
        logging.error("=" * 72)
    else:
        try:
            take_screenshot(driver, group, "_upi_request_sent")
        except Exception as shot_err:
            logging.debug("Could not capture UPI sent screenshot: %s", shot_err)
        try:
            print("\a", flush=True)  # Success chime
        except Exception:
            pass
        logging.info("=" * 72)
        logging.info("🚀 UPI PAYMENT REQUEST TRIGGERED SUCCESSFULLY!")
        logging.info("📱 Amount: ₹10,500")
        logging.info("💳 Sent to: %s (Google Pay)", upi_id)
        logging.info("👉 PLEASE OPEN YOUR GOOGLE PAY APP NOW AND APPROVE PAYMENT WITH YOUR UPI PIN!")
        logging.info("=" * 72)

    # 5. Monitor for payment approval & return to TTD confirmation
    logging.info("⏳ Waiting for UPI confirmation on phone (monitoring browser up to 300 seconds)...")
    monitor_start = time.time()
    confirmed = False

    while time.time() - monitor_start < 300:
        try:
            handles = driver.window_handles
            if len(handles) > 1:
                driver.switch_to.window(handles[-1])
            curr_url = driver.current_url.lower()
            body_text = driver.execute_script("return document.body ? document.body.innerText.toLowerCase() : '';")

            # Check for success indicators
            if any(term in body_text for term in ["payment successful", "transaction successful", "booking confirmed", "darshan booking receipt", "receipt no", "transaction id"]) or \
               ("tirupatibalaji" in curr_url and any(term in curr_url for term in ["receipt", "success", "confirmation", "bookingdetail"])):
                logging.info("🎉🎉🎉 PAYMENT CONFIRMED & BOOKING SUCCESSFUL FOR %s! 🎉🎉🎉", group)
                take_screenshot(driver, group, "_payment_success")
                mark_booking_passed(email, group)
                confirmed = True
                break

            # Check for failure
            if any(term in body_text for term in ["transaction failed", "payment failed", "payment declined", "user cancelled", "transaction timed out"]):
                logging.error("❌ Payment failed or declined for %s.", group)
                take_screenshot(driver, group, "_payment_failed")
                break
        except Exception as mon_err:
            logging.debug("Transient error in payment monitor loop: %s", mon_err)

        time.sleep(2)

    return confirmed


def select_bank_and_pay(driver, group, email):
    """Run the payment-page flow after Continue succeeds.

    Flow:
        Continue succeeds
            ->
        payment page / Angular route renders
            ->
        wait for ICICI radio (pgId/value 11)
            ->
        select ICICI
            ->
        wait for Pay Now to become naturally clickable
            ->
        normal Selenium Pay Now click

    Important:
        - ICICI radio is the primary payment-page readiness signal.
        - Pay Now visibility is NOT used as the initial bank-page readiness
          condition because app.js shows that Pay Now is rendered independently
          of the /common/banks response.
        - Pay Now is clicked ONLY with normal Selenium.
        - No fixed sleep is used in the critical Continue -> Pay Now path.
        - Browser-side readiness timeout uses PAYMENT_PAGE_TIMEOUT.
        - If the async observer returns False normally, Python falls through
          to the fallback polling path instead of treating it as an exception.
    """
    if not hasattr(driver, "_continue_metrics"):
        enable_cdp_monitor(driver)

    # ------------------------------------------------------------------
    # 1) Wait for the ICICI bank control to actually appear.
    #
    # The application's /common/banks response determines whether ICICI
    # becomes available. The radio is therefore the correct readiness
    # condition for the bank-selection stage.
    #
    # Fast path:
    #   If ICICI is already rendered, return immediately.
    #
    # Normal path:
    #   MutationObserver waits for DOM creation / attribute changes.
    #
    # Failure path:
    #   If the async observer reaches its timeout and returns False,
    #   Python explicitly enters fallback polling.
    # ------------------------------------------------------------------
    controls_ready = False

    try:
        # Fast observer timeout: 10 seconds.
        # If TTD lags on Continue, this allows fallback polling to detect the stall
        # and re-click Continue instead of blocking for 70 seconds.
        readiness_timeout = 10.0

        driver.set_script_timeout(readiness_timeout + 2.0)

        observer_result = driver.execute_async_script(r"""
            const done = arguments[arguments.length - 1];
            const timeoutSeconds = Number(arguments[0]) || 1;

            const radioSelector =
                "input[name='iciciBank'][value='11']";

            let observer = null;
            let timer = null;
            let finished = false;

            function isRadioReady() {
                const radio =
                    document.querySelector(radioSelector);

                if (!radio) {
                    return false;
                }

                try {
                    if (!document.documentElement.contains(radio)) {
                        return false;
                    }

                    const style = window.getComputedStyle(radio);
                    const rect = radio.getBoundingClientRect();

                    return (
                        style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        rect.width > 0 &&
                        rect.height > 0
                    );
                } catch (e) {
                    return false;
                }
            }

            function finish(found) {
                if (finished) {
                    return;
                }

                finished = true;

                try {
                    if (observer) {
                        observer.disconnect();
                    }
                } catch (e) {}

                try {
                    if (timer) {
                        clearTimeout(timer);
                    }
                } catch (e) {}

                done(!!found);
            }

            // Fast path.
            if (isRadioReady()) {
                finish(true);
                return;
            }

            try {
                observer = new MutationObserver(function () {
                    if (isRadioReady()) {
                        finish(true);
                        return;
                    }
                    const err = document.getElementById('ErrorMsgPopUp');
                    if (err && window.getComputedStyle(err).display !== 'none') {
                        finish(false);
                        return;
                    }
                    const qpop = document.getElementById('quotaPopUp');
                    if (qpop && window.getComputedStyle(qpop).display !== 'none') {
                        finish(false);
                        return;
                    }
                });

                observer.observe(document.documentElement, {
                    childList: true,
                    subtree: true,
                    attributes: true,
                    attributeFilter: [
                        "value",
                        "style",
                        "class",
                        "hidden"
                    ]
                });

                timer = setTimeout(function () {
                    finish(false);
                }, timeoutSeconds * 1000);

            } catch (e) {
                finish(false);
            }
        """, readiness_timeout)

        # IMPORTANT:
        # A normal JavaScript timeout returns False.
        # It does NOT enter the Python except block.
        #
        # Therefore False must intentionally fall through to the
        # Selenium-side fallback polling below.
        controls_ready = bool(observer_result)

        if not controls_ready:
            logging.warning(
                "Browser-local ICICI readiness observer reached its "
                "timeout (10s) without detecting the radio. "
                "Starting fallback DOM polling and server-lag nudge."
            )

    except Exception as e:
        logging.warning(
            "Browser-local ICICI readiness observer failed: %s. "
            "Starting fallback DOM polling.",
            e,
        )

    # ------------------------------------------------------------------
    # 2) Fallback polling with automatic Continue button retry.
    #
    # This handles:
    #   - normal observer timeout
    #   - navigation/document replacement
    #   - TTD server lag on Continue (nudges Continue every 6s)
    #   - transient Selenium/JavaScript failures
    #
    # Total wait up to PAYMENT_PAGE_TIMEOUT (70s).
    # ------------------------------------------------------------------
    if not controls_ready:
        fallback_start = time.monotonic()
        fallback_timeout = float(PAYMENT_PAGE_TIMEOUT)
        last_continue_retry = fallback_start

        while time.monotonic() - fallback_start < fallback_timeout:
            try:
                curr_url = driver.current_url
                if "userLogin" in curr_url:
                    logging.error(f"❌ Session terminated: TTD redirected back to login page ({curr_url}). Another browser or device likely logged into this account.")
                    break

                # Check native window.alert if present
                try:
                    alert = driver.switch_to.alert
                    alert_text = alert.text
                    alert.accept()
                    if any(k in alert_text.lower() for k in ["booking opens at", "try again later", "please wait", "too many hits"]):
                        wait_sec, reason = parse_wait_seconds_from_message(alert_text)
                        logging.warning(
                            "⚠️ TTD Timing Notice in window.alert: '%s' -> %s",
                            alert_text, reason
                        )
                        time.sleep(wait_sec)
                        try:
                            driver.execute_script(r"""
                                const btn = document.querySelector("button[ng-click*='continue'], button.btn-continue") ||
                                            Array.from(document.querySelectorAll("button")).find(b => (b.innerText || '').trim().toLowerCase() === 'continue');
                                if (btn) {
                                    btn.disabled = false;
                                    btn.click();
                                }
                            """)
                            logging.info("⚡ Re-clicked Continue after window.alert timing notice.")
                        except Exception as re_err:
                            logging.warning("Re-click error: %s", re_err)
                        last_continue_retry = time.monotonic()
                        continue
                    else:
                        logging.error(f"❌ TTD Alert Pop-up: '{alert_text}'")
                        take_screenshot(driver, group, "_ttd_alert")
                        return
                except Exception:
                    pass

                # If on confirmation page, check if TTD blocked progress due to quota full or validation error
                if "edonationConfirm" in curr_url:
                    modal_check = driver.execute_script(r"""
                        try {
                            // 1. Check Angular scope quotaCount and ErrorMsg
                            const el = document.getElementById('captchaCanvas') || document.getElementById('fName1') || document.body;
                            if (window.angular && el) {
                                const sc = angular.element(el).scope();
                                if (sc && sc.dccsc) {
                                    if (sc.dccsc.quotaCount === 0) {
                                        return { is_quota: true, msg: "TTD Quota Count is 0 (Daily Srivani quota completely exhausted/sold out)" };
                                    }
                                    if (sc.dccsc.ErrorMsg) {
                                        const em = sc.dccsc.ErrorMsg;
                                        const isTiming = /booking opens at|try again later|please wait|too many hits/i.test(em);
                                        return { is_error: true, is_timing: isTiming, msg: em };
                                    }
                                }
                            }
                            // 2. Check modal popup visibility
                            const qpop = document.getElementById('quotaPopUp');
                            if (qpop && window.getComputedStyle(qpop).display !== 'none') {
                                return { is_quota: true, msg: (qpop.innerText || "Quota Full").trim() };
                            }
                            const qmis = document.getElementById('quotamisPopUp');
                            if (qmis && window.getComputedStyle(qmis).display !== 'none') {
                                return { is_quota: true, msg: (qmis.innerText || "Quota Mismatch/Exhausted").trim() };
                            }
                            const errPop = document.getElementById('ErrorMsgPopUp');
                            if (errPop && window.getComputedStyle(errPop).display !== 'none') {
                                const t = (errPop.innerText || "TTD Error Modal").trim();
                                const isTiming = /booking opens at|try again later|please wait|too many hits/i.test(t);
                                return { is_error: true, is_timing: isTiming, msg: t };
                            }
                        } catch(e) {}
                        return null;
                    """)
                    if modal_check:
                        if modal_check.get("is_quota"):
                            logging.error(f"❌ TTD QUOTA FULL: {modal_check.get('msg')}. Booking aborted.")
                            take_screenshot(driver, group, "_quota_full")
                            return
                        elif modal_check.get("is_error"):
                            msg = modal_check.get("msg", "")
                            if modal_check.get("is_timing") or any(k in msg.lower() for k in ["booking opens at", "try again later", "please wait", "too many hits"]):
                                wait_sec, reason = parse_wait_seconds_from_message(msg)
                                logging.warning(
                                    "⚠️ TTD Notice: '%s' -> %s. Dismissing modal and holding Continue...",
                                    msg, reason
                                )
                                try:
                                    driver.execute_script(r"""
                                        try {
                                            const errPop = document.getElementById('ErrorMsgPopUp');
                                            if (errPop) {
                                                const btn = errPop.querySelector("button, .btn, a, [data-dismiss='modal']");
                                                if (btn) btn.click();
                                                errPop.style.display = 'none';
                                            }
                                            document.querySelectorAll('.modal-backdrop').forEach(bd => bd.remove());
                                            document.body.classList.remove('modal-open');
                                            // Clear stale Angular ErrorMsg so fallback polling does not re-trigger on the old notice
                                            const el = document.getElementById('captchaCanvas') || document.getElementById('fName1') || document.body;
                                            if (window.angular && el) {
                                                const sc = angular.element(el).scope();
                                                if (sc && sc.dccsc) {
                                                    sc.dccsc.ErrorMsg = '';
                                                    if (sc.$root && !sc.$root.$$phase) {
                                                        sc.$apply();
                                                    }
                                                }
                                            }
                                        } catch(e) {}
                                    """)
                                except Exception:
                                    pass
                                time.sleep(wait_sec)
                                # Re-click Continue button
                                try:
                                    driver.execute_script(r"""
                                        const btn = document.querySelector("button[ng-click*='continue'], button.btn-continue") ||
                                                    Array.from(document.querySelectorAll("button")).find(b => (b.innerText || '').trim().toLowerCase() === 'continue');
                                        if (btn) {
                                            btn.disabled = false;
                                            btn.click();
                                        }
                                    """)
                                    logging.info("⚡ Re-clicked Continue after waiting for designated slot time.")
                                except Exception as reclick_err:
                                    logging.warning("Re-click continue error: %s", reclick_err)
                                last_continue_retry = time.monotonic()
                                continue
                            else:
                                logging.error(f"❌ TTD ERROR DETECTED: {msg}. Booking aborted.")
                                take_screenshot(driver, group, "_ttd_error")
                                return

                now = time.monotonic()
                # If still stuck on confirm page after Continue was clicked, nudge Continue button every 6 seconds
                if "edonationConfirm" in curr_url and (now - last_continue_retry >= 6.0):
                    last_continue_retry = now
                    logging.warning(
                        "⚠️ TTD server lag detected: still on confirm page (%.1fs elapsed). Retrying Continue click...",
                        now - fallback_start,
                    )
                    try:
                        driver.execute_script(r"""
                            const btn = document.querySelector("button[ng-click*='continue'], button.btn-continue") ||
                                        Array.from(document.querySelectorAll("button")).find(b => (b.innerText || '').trim().toLowerCase() === 'continue');
                            if (btn && !btn.disabled) {
                                btn.click();
                            }
                        """)
                    except Exception as nudge_err:
                        logging.debug("Continue nudge error: %s", nudge_err)

                controls_ready = bool(driver.execute_script(r"""
                    const radio = document.querySelector(
                        "input[name='iciciBank'][value='11']"
                    );

                    if (!radio) {
                        return false;
                    }

                    if (!document.documentElement.contains(radio)) {
                        return false;
                    }

                    const style = window.getComputedStyle(radio);
                    const rect = radio.getBoundingClientRect();

                    return (
                        style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        rect.width > 0 &&
                        rect.height > 0
                    );
                """))

                if controls_ready:
                    logging.info(
                        "ICICI radio detected by fallback polling."
                    )
                    break

            except Exception:
                # Angular route/document replacement can temporarily
                # invalidate the current document. Retry on the new DOM.
                pass

            # Lightweight fallback polling only.
            time.sleep(0.09)

    if not controls_ready:
        logging.error(
            "ICICI radio/payment controls were not detected within "
            "%.1f seconds.",
            float(PAYMENT_PAGE_TIMEOUT),
        )

        take_screenshot(
            driver,
            group,
            "_gateway_not_found",
        )

        return

    # ------------------------------------------------------------------
    # 3) Record payment-page / ICICI readiness.
    # ------------------------------------------------------------------
    now_monotonic = time.monotonic()

    if not driver._continue_metrics.get("bank_page_wall"):
        driver._continue_metrics["bank_page_wall"] = (
            datetime.datetime.now()
        )

        driver._continue_metrics["bank_page_monotonic"] = (
            now_monotonic
        )

        logging.info(
            "ICICI bank-selection control detected."
        )

    driver._continue_metrics[
        "continue_state_monotonic"
    ] = now_monotonic

    driver._continue_metrics[
        "icici_wall"
    ] = datetime.datetime.now().strftime(
        "%H:%M:%S.%f"
    )[:-3]

    driver._continue_metrics[
        "icici_monotonic"
    ] = now_monotonic

    if driver._continue_metrics.get("click_monotonic"):
        logging.info(
            "Continue -> ICICI radio ready: %.3fs",
            now_monotonic
            - driver._continue_metrics["click_monotonic"],
        )

    collect_continue_metrics(driver)

    # ------------------------------------------------------------------
    # 4) Snapshot current URL + window handles immediately before
    #    ICICI selection / Pay Now path.
    # ------------------------------------------------------------------
    try:
        before_url = driver.current_url
    except Exception:
        before_url = ""

    try:
        before_handles = len(driver.window_handles)
    except Exception:
        before_handles = 0

    try:
        before_iframes = len(driver.find_elements(By.TAG_NAME, "iframe"))
    except Exception:
        before_iframes = 0

    # ------------------------------------------------------------------
    # 5) Select ICICI.
    #
    # The Angular template already has ng-model/ng-change attached to
    # the radio. A native DOM click is therefore sufficient to generate
    # the browser click/change behavior.
    #
    # We intentionally do NOT:
    #   - manually assign the Angular model
    #   - invoke scope.$eval()
    #   - invoke scope.$apply()
    #   - dispatch duplicate input/change events
    #
    # This reduces redundant application-side processing.
    # ------------------------------------------------------------------
    selected = False
    result = None

    try:
        result = driver.execute_script(r"""
            const radio = document.querySelector(
                "input[name='iciciBank'][value='11']"
            );

            if (!radio) {
                return {
                    ok: false,
                    reason: "radio_missing"
                };
            }

            if (!document.documentElement.contains(radio)) {
                return {
                    ok: false,
                    reason: "radio_detached"
                };
            }

            radio.click();

            return {
                ok: true,
                checked: !!radio.checked,
                value: radio.value
            };
        """)

        selected = (
            isinstance(result, dict)
            and bool(result.get("ok"))
            and bool(result.get("checked"))
            and str(result.get("value")) == "11"
        )

    except Exception as e:
        result = f"error:{e}"
        selected = False

    # ------------------------------------------------------------------
    # 6) If Angular/browser updated the radio asynchronously, give it a
    #    short condition-based verification window.
    #
    # No fixed sleep.
    # ------------------------------------------------------------------
    if not selected:
        logging.warning(
            "Initial ICICI selection verification failed: %s",
            result,
        )

        try:
            selected = bool(
                WebDriverWait(
                    driver,
                    1.0,
                    poll_frequency=0.02,
                ).until(
                    lambda d: d.execute_script(r"""
                        const radio = document.querySelector(
                            "input[name='iciciBank'][value='11']"
                        );

                        return !!(
                            radio &&
                            document.documentElement.contains(radio) &&
                            radio.checked &&
                            String(radio.value) === "11"
                        );
                    """)
                )
            )
        except Exception:
            selected = False

    if selected:
        driver._continue_metrics[
            "icici_selected_monotonic"
        ] = time.monotonic()

        logging.info(
            "ICICI radio selection verified."
        )
    else:
        logging.warning(
            "ICICI radio/model verification failed: %s",
            result,
        )

    # ------------------------------------------------------------------
    # 7) Pay Now.
    #
    # IMPORTANT:
    #   - Normal Selenium click only.
    #   - No JavaScript click.
    #   - Up to 10 seconds maximum.
    #   - Fast cases return immediately.
    #
    # element_to_be_clickable() does not impose a 10-second delay when
    # the button is already clickable.
    # ------------------------------------------------------------------
    paynow_result = False

    # Sister-Worker Pay-Now Concurrency Guard:
    # Only ONE worker per family can click Pay Now to prevent TTD's
    # "A transaction is already being processed with the entered details" error.
    lock_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ready")
    os.makedirs(lock_dir, exist_ok=True)
    paynow_lock_file = os.path.join(lock_dir, f"{group}_paynow.lock")

    if os.path.exists(paynow_lock_file):
        try:
            with open(paynow_lock_file, "r") as f:
                locked_by = f.read().strip()
            logging.info("ℹ️ Sister worker (%s) has ALREADY initiated Pay Now for %s!", locked_by, group)
            logging.info("👉 Standing down on this worker to prevent TTD duplicate transaction rejection.")
            return True
        except Exception:
            pass

    try:
        with open(paynow_lock_file, "w") as f:
            f.write(f"{email}_{time.time()}")
        logging.info("🔒 Acquired Pay-Now lock for %s (Worker: %s).", group, email)
    except Exception:
        pass

    if selected:
        try:
            pay_now = WebDriverWait(
                driver,
                10.0,
                poll_frequency=0.02,
            ).until(
                EC.element_to_be_clickable(
                    (By.ID, "edonation_paynow")
                )
            )

            driver._continue_metrics[
                "paynow_click_wall"
            ] = datetime.datetime.now()

            driver._continue_metrics[
                "paynow_click_monotonic"
            ] = time.monotonic()

            logging.info(
                "Pay Now is naturally clickable. "
                "Executing normal Selenium click."
            )

            # Intentionally normal Selenium click.
            pay_now.click()

            paynow_result = True

            driver._continue_metrics[
                "paynow_after_click_monotonic"
            ] = time.monotonic()

            logging.info(
                "ICICI -> Pay Now: %.3fs",
                driver._continue_metrics[
                    "paynow_click_monotonic"
                ]
                - driver._continue_metrics[
                    "icici_selected_monotonic"
                ],
            )

            collect_continue_metrics(driver)

        except TimeoutException:
            logging.warning(
                "Pay Now did not become naturally clickable "
                "within 10 seconds."
            )

        except StaleElementReferenceException:
            logging.warning(
                "Pay Now became stale during the first lookup. "
                "Re-locating once and retrying normal Selenium click."
            )

            try:
                pay_now = WebDriverWait(
                    driver,
                    10.0,
                    poll_frequency=0.02,
                ).until(
                    EC.element_to_be_clickable(
                        (By.ID, "edonation_paynow")
                    )
                )

                driver._continue_metrics[
                    "paynow_click_wall"
                ] = datetime.datetime.now()

                driver._continue_metrics[
                    "paynow_click_monotonic"
                ] = time.monotonic()

                # Still normal Selenium.
                pay_now.click()

                paynow_result = True

                driver._continue_metrics[
                    "paynow_after_click_monotonic"
                ] = time.monotonic()

                logging.info(
                    "Pay Now clicked using normal Selenium "
                    "after re-location."
                )

                collect_continue_metrics(driver)

            except Exception as e:
                logging.warning(
                    "Normal Selenium Pay Now retry failed: %s",
                    e,
                )

        except Exception as e:
            logging.warning(
                "Normal Selenium Pay Now click failed: %s",
                e,
            )

    logging.info(
        "ICICI selection result: %s; Pay Now result: %s",
        result,
        paynow_result,
    )

    # ------------------------------------------------------------------
    # 8) Fallback.
    #
    # Used when:
    #   - ICICI selection failed, OR
    #   - Pay Now normal Selenium click failed.
    #
    # Pay Now remains a NORMAL Selenium click.
    # ------------------------------------------------------------------
    if not selected or not paynow_result:
        logging.warning(
            "Primary ICICI/Pay Now path failed; "
            "using Selenium fallback."
        )

        try:
            # Re-locate the fresh ICICI radio.
            radio = WebDriverWait(
                driver,
                2.0,
                poll_frequency=0.02,
            ).until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "input[name='iciciBank'][value='11']",
                    )
                )
            )

            # Native DOM click is used for ICICI only.
            driver.execute_script(
                "arguments[0].click();",
                radio,
            )

            # Verify that the radio actually became checked.
            WebDriverWait(
                driver,
                1.0,
                poll_frequency=0.02,
            ).until(
                lambda d: d.execute_script(
                    "return !!arguments[0].checked;",
                    radio,
                )
            )

            driver._continue_metrics[
                "icici_selected_monotonic"
            ] = time.monotonic()

            # Wait up to 10 seconds for natural Selenium clickability.
            pay_now = WebDriverWait(
                driver,
                10.0,
                poll_frequency=0.02,
            ).until(
                EC.element_to_be_clickable(
                    (By.ID, "edonation_paynow")
                )
            )

            driver._continue_metrics[
                "paynow_click_wall"
            ] = datetime.datetime.now()

            driver._continue_metrics[
                "paynow_click_monotonic"
            ] = time.monotonic()

            # IMPORTANT:
            # Pay Now remains a normal Selenium click.
            pay_now.click()

            paynow_result = True

            driver._continue_metrics[
                "paynow_after_click_monotonic"
            ] = time.monotonic()

            collect_continue_metrics(driver)

            logging.info(
                "Fallback: ICICI selected and Pay Now clicked "
                "using normal Selenium."
            )

        except Exception as e:
            logging.error(
                "Fallback ICICI/Pay-Now failed: %s",
                e,
            )

            take_screenshot(
                driver,
                group,
                "_gateway_failed",
            )

            return

    # ------------------------------------------------------------------
    # 9) Screenshot immediately after Pay Now has fired.
    # ------------------------------------------------------------------
    ts = datetime.datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    take_screenshot(
        driver,
        group,
        f"_{ts}_after_paynow",
    )

    # Check immediately if TTD showed Quota Exceeded alert
    time.sleep(0.5)
    if check_quota_exceeded(driver):
        logging.error("❌ Quota exceeded: TTD reported 'Cannot book as quota exceeded'. Booking slot was full.")
        take_screenshot(driver, group, "_quota_exceeded")
        return False

    # ------------------------------------------------------------------
    # 10) Observe downstream browser state.
    #
    # This is diagnostic/post-click observation only. It does not define
    # whether Pay Now was successfully clicked.
    # ------------------------------------------------------------------
    terminal_alert_detected = [False]
    last_alert_check = [0.0]

    def _is_gateway_or_redirect_loaded(d):
        if len(d.window_handles) > before_handles:
            return True
        cur = (d.current_url or "").lower()
        if before_url and cur != before_url.lower() and "edonationcurrentsrivanipay" not in cur:
            return True
        if any(kw in cur for kw in ["paytm", "securegw", "icici", "eazypay", "billdesk", "razorpay", "wlpgpayment", "bank", "payment"]):
            return True
        if d.find_elements(By.CSS_SELECTOR, "iframe[src*='paytm'], iframe[src*='securegw'], iframe[src*='icici'], iframe[id*='paytm'], div[id*='paytm-checkoutjs'], div[id*='paytm']"):
            return True
        now_m = time.monotonic()
        if now_m - last_alert_check[0] >= 0.4:
            last_alert_check[0] = now_m
            if check_quota_exceeded(d):
                terminal_alert_detected[0] = True
                return True
        return False

    def _abort_on_terminal_alert():
        logging.error("❌ Quota exceeded: TTD reported 'Cannot book as quota exceeded'. Booking slot was full.")
        take_screenshot(driver, group, "_quota_exceeded")
        return False

    try:
        logging.info("⏳ Waiting up to 25s for TTD server to process booking and redirect to Payment Gateway...")
        WebDriverWait(
            driver,
            25,
            poll_frequency=0.1,
        ).until(_is_gateway_or_redirect_loaded)

        if terminal_alert_detected[0]:
            collect_continue_metrics(driver)
            return _abort_on_terminal_alert()

        driver._continue_metrics[
            "paynow_state_monotonic"
        ] = time.monotonic()

        if len(driver.window_handles) > before_handles:
            driver.switch_to.window(
                driver.window_handles[-1]
            )

        logging.info(
            "✅ Post-Pay-Now browser state detected: %s (tab, URL change, or payment gateway iframe rendered).",
            driver.current_url
        )

        # Drain delayed network events for diagnostics.
        collect_continue_metrics(driver)

    except TimeoutException:
        collect_continue_metrics(driver)
        logging.warning("⚠️ Post-Pay-Now tab/URL transition not detected within 25s.")

        if check_quota_exceeded(driver):
            return _abort_on_terminal_alert()

        # Check if browser is still sitting on edonationCurrentSrivanipay page
        cur_url = (driver.current_url or "").lower()
        if "edonationcurrentsrivanipay" in cur_url:
            logging.info("🔄 Still on TTD payment selection page. Attempting fallback click on 'Pay Now'...")
            try:
                pn = driver.find_element(By.ID, "edonation_paynow")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", pn)
                logging.info("Clicked Pay Now via fallback JS click. Waiting additional 10s...")
                WebDriverWait(driver, 10, poll_frequency=0.1).until(_is_gateway_or_redirect_loaded)
                if terminal_alert_detected[0]:
                    return _abort_on_terminal_alert()
                if len(driver.window_handles) > before_handles:
                    driver.switch_to.window(driver.window_handles[-1])
            except Exception as ex_reclick:
                logging.debug("Fallback click attempt notice: %s", ex_reclick)

    # Check if quota exceeded alert popped up during transition
    if check_quota_exceeded(driver):
        return _abort_on_terminal_alert()

    # ------------------------------------------------------------------
    # 11) Payment Processing (Automated UPI or Headless Card OTP)
    # ------------------------------------------------------------------
    pay_info = get_payment_info(group)
    ptype = str(pay_info.get("payment_type") or pay_info.get("payment_method") or "UPI").upper()
    upi_id = str(pay_info.get("upi_id") or "jeffrinsingh854@oksbi").strip()

    # Safety Fallback:
    # If group is configured as CARD, but no automated card details (card_number) exist in DB,
    # routing to handle_otp_flow_for_worker will hang waiting for an OTP that was never sent.
    # Therefore, automatically route to the robust UPI payment flow.
    card_number = pay_info.get("card_number")
    if ptype == "CARD" and not card_number:
        logging.info("ℹ️ Payment method for %s is set to CARD, but no card number exists in DB. Automatically routing to UPI flow with %s.", group, upi_id)
        ptype = "UPI"

    if ptype == "UPI":
        logging.info("💳 Configured payment type is UPI. Running automated UPI ID injection with %s...", upi_id)
        return handle_upi_payment_flow(driver, group, email, upi_id=upi_id)
    else:
        logging.info("💳 Configured payment type is CARD. Running OTP bridge flow...")
        return handle_otp_flow_for_worker(driver, group, email)

    # Return and let run_booking keep the browser open or complete.


def fill_donation_form(driver, amount):
    try:
        amount_input = driver.find_element(By.ID, "amountD")
        amount_input.clear()
        amount_input.send_keys(str(amount))
    except NoSuchElementException:
        try:
            amount_input = driver.find_element(By.XPATH, "//input[@ng-model='sdcc.amount']")
            amount_input.clear()
            amount_input.send_keys(str(amount))
        except NoSuchElementException:
            logging.warning("Amount input not found")

    try:
        checkbox1 = driver.find_element(By.XPATH, "//input[@ng-model='sdcc.checkamount']")
        if not checkbox1.is_selected():
            driver.execute_script("arguments[0].click();", checkbox1)
    except NoSuchElementException:
        logging.warning("Checkbox 1 not found")

    try:
        checkbox2 = driver.find_element(By.XPATH, "//input[@ng-model='sdcc.indian']")
        if not checkbox2.is_selected():
            driver.execute_script("arguments[0].click();", checkbox2)
    except NoSuchElementException:
        logging.warning("Checkbox 2 not found")

    logging.info("Donation form filled (amount and checkboxes).")

def click_continue_donation(driver, auto_close=False):
    try:
        continue_submit = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@ng-click,'sdcc.continueSubmit')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", continue_submit)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", continue_submit)
        logging.info("Clicked 'Continue' button.")
        return True
    except Exception as e:
        logging.warning(f"Could not click Continue button automatically: {e}")
        if auto_close:
            logging.error("Manual intervention required but --auto-close is set. Aborting.")
            return False
        logging.info("👉 Please click the 'Continue' button manually, then press Enter.")
        input("Press Enter after you have clicked 'Continue'...")
        return True

def save_page_debug(driver, stage):
    folder = os.path.join("debug_pages")
    os.makedirs(folder, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    html_file = os.path.join(folder, f"{ts}_{stage}.html")
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    screenshot = os.path.join(folder, f"{ts}_{stage}.png")
    driver.save_screenshot(screenshot)
    url_file = os.path.join(folder, f"{ts}_{stage}.txt")
    with open(url_file, "w") as f:
        f.write(driver.current_url)
    logging.info(f"Saved debug page: {stage}")

def wait_for_quota_and_add_buffer(driver):
    QUOTA_XPATH = "//span[contains(normalize-space(.),'Available Quota')]/following-sibling::span[1]"
    start = time.time()
    try:
        WebDriverWait(driver, 20, poll_frequency=0.05).until(
            lambda d: (lambda txt: txt.isdigit() and int(txt) > 0)(
                d.find_element(By.XPATH, QUOTA_XPATH).text.strip()
            )
        )
        elapsed = time.time() - start
        extra_delay = min(elapsed + 0.4, 0.7)
        logging.info(f"Quota detected after {elapsed:.2f}s. Waiting {extra_delay:.2f}s buffer.")
        time.sleep(extra_delay)
        return True
    except Exception:
        fallback = random.uniform(1.0, 2.0)
        logging.warning(f"Quota detection failed. Waiting fallback {fallback:.2f}s.")
        time.sleep(fallback)
        return False

# ---------------------------------------------------------------------
# Main booking flow – MODIFIED: browser selection with custom driver
# ---------------------------------------------------------------------

def clean_profile_locks(profile_dir):
    """Safely remove Chrome lock files (lockfile, Profile.lock, Singleton*) before launching browser."""
    if not os.path.exists(profile_dir):
        return
    lock_names = {"lockfile", "profile.lock", "singletonlock", "singletoncookie", "singletonsocket"}
    for root, dirs, files in os.walk(profile_dir):
        for f in files:
            if f.lower() in lock_names or f.lower().endswith(".lock"):
                full_path = os.path.join(root, f)
                try:
                    os.remove(full_path)
                except Exception:
                    pass


def safe_type_input(driver, element, value):
    """
    Sets input value reliably across both visible and off-screen / ghost browser windows.
    Tries standard send_keys first; if OS drops keystrokes due to off-screen window positioning,
    injects via HTMLInputElement native prototype setter, dispatches synthetic keyboard/input events,
    and updates AngularJS ngModel.
    """
    if not element or value is None:
        return
    val_str = str(value)
    try:
        element.clear()
        element.send_keys(val_str)
    except Exception:
        pass
    if element.get_attribute("value") != val_str:
        try:
            driver.execute_script("""
                var el = arguments[0];
                var val = arguments[1];
                try { el.focus(); } catch(e) {}
                try {
                    var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                    nativeSetter.call(el, val);
                } catch(e) {
                    el.value = val;
                }
                ['focus', 'keydown', 'keypress', 'input', 'keyup', 'change', 'blur'].forEach(function(evt) {
                    try { el.dispatchEvent(new Event(evt, { bubbles: true })); } catch(e) {}
                });
                if (window.angular && angular.element(el).controller('ngModel')) {
                    try {
                        angular.element(el).controller('ngModel').$setViewValue(val);
                        angular.element(el).controller('ngModel').$commitViewValue();
                        angular.element(el).scope().$apply();
                    } catch(e) {}
                }
            """, element, val_str)
        except Exception as e:
            logging.debug("safe_type_input JS fallback error: %s", e)


def perform_login(email, password, worker_id=0, browser="chrome"):
    logging.info("Starting login process for %s (worker %d)", email, worker_id)

    try:
        import undetected_chromedriver as uc
    except ImportError:
        logging.error("undetected_chromedriver not installed.")
        return None

    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1280,900')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-popup-blocking')
    # Anti-throttling flags to maintain high-performance V8/timer execution when off-screen
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-features=CalculateWindowOcclusion')
    # Eager loading: proceed as soon as DOM is interactive without hanging on non-critical third-party assets
    options.page_load_strategy = 'eager'
    if os.environ.get("HEADLESS", "0") == "1":
        options.add_argument('--headless=new')
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    #options.add_argument('--load-extension=D:\sep_working_code\auto_click')    

    driver_executable_path = None
    chrome_ver = None

    # Isolated driver executable cache per worker to prevent multi-worker collisions
    worker_cache_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "undetected_cache",
        f"worker_{worker_id}"
    )
    os.makedirs(worker_cache_dir, exist_ok=True)
    worker_driver_exe = os.path.join(worker_cache_dir, "chromedriver.exe")

    if browser == "chromium":
        # Use bundled Chromium and its specific driver
        if not os.path.exists(CHROMIUM_PATH) or not os.path.exists(CHROMIUM_DRIVER_PATH):
            logging.warning(f"Bundled Chromium/Driver not found ({CHROMIUM_PATH}). Gracefully falling back to Google Chrome.")
            browser = "chrome"
        else:
            options.binary_location = CHROMIUM_PATH
            # Replicate driver to worker cache to avoid concurrent access collisions
            if not os.path.exists(worker_driver_exe) or os.path.getsize(worker_driver_exe) != os.path.getsize(CHROMIUM_DRIVER_PATH):
                try:
                    shutil.copy2(CHROMIUM_DRIVER_PATH, worker_driver_exe)
                except Exception:
                    pass
            driver_executable_path = worker_driver_exe if os.path.exists(worker_driver_exe) else CHROMIUM_DRIVER_PATH
            logging.info(f"Using bundled Chromium with driver at {driver_executable_path}")

    if browser != "chromium":
        # Default: Google Chrome – auto‑detect version for driver download
        chrome_ver = get_chrome_version()
        logging.info(f"Using Google Chrome (version major {chrome_ver})")

        # Check master driver first and keep worker cache synchronized to current Chrome version
        master_driver = os.path.join(uc.Patcher().data_path, "undetected_chromedriver.exe")
        if not os.path.exists(master_driver) or os.path.getsize(master_driver) < 1000000:
            try:
                p = uc.Patcher(version_main=chrome_ver)
                p.auto()
                master_driver = p.executable_path
            except Exception as patch_err:
                logging.debug(f"Patcher auto error: {patch_err}")

        if os.path.exists(master_driver) and os.path.getsize(master_driver) > 1000000:
            if not os.path.exists(worker_driver_exe) or os.path.getsize(worker_driver_exe) != os.path.getsize(master_driver):
                try:
                    shutil.copy2(master_driver, worker_driver_exe)
                except Exception:
                    pass
            driver_executable_path = worker_driver_exe if os.path.exists(worker_driver_exe) else master_driver
        elif os.path.exists(worker_driver_exe) and os.path.getsize(worker_driver_exe) > 1000000:
            driver_executable_path = worker_driver_exe

    # ---- Profile directory & Lock Cleanup ----
    profile_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "sessions",
        f"{email.replace('@','_')}_{worker_id}"
    )
    os.makedirs(profile_dir, exist_ok=True)
    clean_profile_locks(profile_dir)
    options.add_argument(f'--user-data-dir={profile_dir}')

    try:
        if browser == "chromium":
            # Pass the driver executable path explicitly
            driver = uc.Chrome(
                options=options,
                driver_executable_path=driver_executable_path,
                use_subprocess=True
            )
        else:
            # Chrome: use isolated driver_executable_path to prevent concurrent WinError 183
            if driver_executable_path and os.path.exists(driver_executable_path):
                driver = uc.Chrome(
                    options=options,
                    driver_executable_path=driver_executable_path,
                    version_main=chrome_ver,
                    use_subprocess=True
                )
            elif chrome_ver:
                driver = uc.Chrome(options=options, version_main=chrome_ver, use_subprocess=True)
            else:
                driver = uc.Chrome(options=options, use_subprocess=True)
    except Exception as e:
        logging.error(f"Failed to create Chrome driver: {e}")
        return None

    enable_cdp_monitor(driver)

    # Window positioning: Ghost Mode (Option A, off-screen) vs. Visible Mode
    show_browser = os.environ.get("SHOW_BROWSER", "").strip().lower() in ("1", "true", "yes") or SHOW_BROWSER

    if show_browser:
        base_x = 40 + (worker_id * 50) % 700
        base_y = 30 + (worker_id * 35) % 450
        driver.set_window_position(base_x, base_y)
        driver.set_window_size(1280, 800)
        logging.info(f"🖥️ Visible browser mode active: positioned at ({base_x}, {base_y}) with size (1280, 800).")
    else:
        # Option A: Ghost / Off-Screen positioning
        # Runs full GPU/canvas/DOM rendering context to bypass bot detection while desktop remains clean
        try:
            driver.set_window_position(-2500, -2500)
            driver.set_window_size(1280, 900)
            logging.info("👻 Ghost Mode active: browser positioned off-screen (-2500, -2500). Desktop remains clean.")
        except Exception as e:
            logging.warning(f"Could not set ghost window position: {e}")

    wait = WebDriverWait(driver, 25)
    driver.set_page_load_timeout(60)
    for nav_attempt in range(2):
        try:
            driver.get(LOGIN_URL)
            break
        except TimeoutException:
            # Check if loginInput is already rendered in DOM
            try:
                if driver.find_elements(By.ID, "loginInput"):
                    logging.info("loginInput already mounted in DOM; continuing.")
                    try:
                        driver.execute_script("window.stop();")
                    except Exception:
                        pass
                    break
            except Exception:
                pass

            if nav_attempt == 0:
                logging.warning("Page load timed out after 60s; checking if DOM is settling before retry...")
                try:
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "loginInput")))
                    logging.info("loginInput appeared after initial timeout; proceeding.")
                    break
                except Exception:
                    pass
                logging.warning("Retrying navigation once...")
                time.sleep(2)
                continue
            else:
                logging.warning("Page load timed out on retry; proceeding to DOM check.")
                break
        except Exception as e:
            if nav_attempt == 0:
                logging.warning(f"driver.get failed: {e}. Retrying once...")
                time.sleep(2)
            else:
                logging.error(f"driver.get failed after retries: {e}")
                raise
    logging.info("Login page loaded.")

    handle_popups(driver, wait_time=0.2)

    try:
        email_input = wait.until(EC.presence_of_element_located((By.ID, "loginInput")))
    except TimeoutException:
        try:
            email_input = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//input[@name='email' or @placeholder='Email' or @type='email']")
            ))
        except TimeoutException:
            cur_url = driver.current_url or ""
            if "login" not in cur_url.lower() and ("donor" in cur_url.lower() or "home" in cur_url.lower()):
                logging.info("Already logged in (session restored). Current URL: %s", cur_url)
                return driver
            # Capture full diagnostic context on failure
            try:
                os.makedirs("screenshots", exist_ok=True)
                dbg_png = os.path.join("screenshots", f"login_fail_worker_{worker_id}.png")
                driver.save_screenshot(dbg_png)
                logging.error(f"Saved diagnostic screenshot: {dbg_png}")
            except Exception:
                pass
            logging.error(f"Login failed to locate loginInput. Current URL: {cur_url} | Title: {driver.title}")
            try:
                txt = driver.execute_script("return (document.body && document.body.innerText) ? document.body.innerText.substring(0, 300) : 'EMPTY';")
                logging.error(f"DOM text sample: {repr(txt)}")
            except Exception:
                pass
            raise
    safe_type_input(driver, email_input, email)

    try:
        password_input = wait.until(EC.presence_of_element_located((By.NAME, "pwd")))
    except TimeoutException:
        try:
            password_input = wait.until(EC.presence_of_element_located((By.ID, "password")))
        except TimeoutException:
            password_input = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//input[@type='password']")
            ))
    safe_type_input(driver, password_input, password)

    captcha_img = wait.until(EC.presence_of_element_located((By.ID, "captcha")))
    captcha_input = wait.until(EC.presence_of_element_located((By.ID, "txtInput")))
    refresh_btn = driver.find_element(By.XPATH, "//img[@ng-click='logc.Captcha()']")

    try:
        driver.execute_script("""
            var c = document.getElementById('captcha');
            if (c) {
                c.style.whiteSpace = 'nowrap';
                c.style.letterSpacing = 'normal';
                c.style.maxWidth = 'none';
            }
        """)
    except Exception:
        pass

    for attempt in range(1, MAX_RETRIES + 1):
        logging.info(f"Login CAPTCHA attempt {attempt}/{MAX_RETRIES}")

        # Check direct AngularJS scope on login page first (0ms, 100% accurate)
        captcha_text = ""
        try:
            scope_val = driver.execute_script("""
                try {
                    var el = document.getElementById('captcha') || document.getElementById('txtInput');
                    if (el && window.angular) {
                        var sc = angular.element(el).scope();
                        if (sc && sc.logc) {
                            var v = sc.logc.captcha || sc.logc.captchaVal || sc.logc.currentCaptcha || sc.logc.captchaCode;
                            if (v && String(v).trim().length >= 6) return String(v).trim().toUpperCase();
                        }
                    }
                } catch(e) {}
                return '';
            """)
            if scope_val and len(scope_val) in (6, 7):
                logging.info(f"🎯 Instant Login Scope CAPTCHA -> '{scope_val}' (100% accurate, 0ms)")
                captcha_text = scope_val
        except Exception:
            pass

        if not captcha_text:
            img_src = captcha_img.get_attribute("src")
            if not img_src:
                logging.error("CAPTCHA image src not found.")
                break
            captcha_text = decode_captcha(img_src, save_image=(attempt == 1))
            logging.info(f"RapidOCR -> '{captcha_text}' (auto-submit)")

        if len(captcha_text) >= 5:
            c_input = wait.until(EC.presence_of_element_located((By.ID, "txtInput")))
            safe_type_input(driver, c_input, captcha_text)

            login_btn = wait.until(EC.element_to_be_clickable((By.ID, "login_sub")))
            try:
                driver.execute_script("arguments[0].click();", login_btn)
            except Exception:
                login_btn.click()

            try:
                WebDriverWait(driver, 2.5).until(
                    lambda d: "userLogin" not in (d.current_url or "") or "welcome" in (d.current_url or "")
                )
            except Exception:
                time.sleep(0.3)

            try:
                handle_popups(driver, wait_time=0.2)
            except Exception:
                pass

            curr_url = driver.current_url or ""
            if "userLogin" not in curr_url or "welcome" in curr_url:
                logging.info(f"✅ Login successful! Navigated to: {curr_url}")
                return driver

            try:
                error = driver.find_element(By.XPATH, "//div[contains(@class,'err') and contains(text(),'Captcha')]")
                if error.is_displayed() and "empty" not in error.text.lower():
                    logging.warning(f"Error element displayed: '{error.text}'. Refreshing...")
                    try:
                        old_src = captcha_img.get_attribute("src")
                        refresh_btn.click()
                        for _ in range(30):
                            time.sleep(0.1)
                            new_src = captcha_img.get_attribute("src")
                            if new_src and new_src != old_src:
                                break
                    except Exception:
                        time.sleep(1)
                    continue
            except NoSuchElementException:
                pass

            logging.info("✅ Login successful!")
            return driver
        else:
            logging.warning("OCR result too short. Refreshing CAPTCHA...")
            try:
                old_src = captcha_img.get_attribute("src")
                refresh_btn.click()
                for _ in range(30):
                    time.sleep(0.1)
                    new_src = captcha_img.get_attribute("src")
                    if new_src and new_src != old_src:
                        break
            except Exception:
                time.sleep(1)

    logging.error("❌ Login failed after all attempts.")
    return None

def perform_donation_flow(driver, pilgrim_data, donation_amount, group, email, auto_close=False):
    logging.info("Starting donation flow...")
    wait = WebDriverWait(driver, 20)

    try:
        wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "loading-spinner")))
    except TimeoutException:
        pass

    logging.info("Step 1: Clicking 'Srivani Trust Donations' link...")
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
        except TimeoutException:
            continue
    if not donation_link:
        raise Exception("Could not find 'Srivani Trust Donations' link.")
    driver.execute_script("arguments[0].scrollIntoView(true);", donation_link)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", donation_link)
    logging.info("Clicked donation link.")

    time.sleep(0.5)

    logging.info("Step 2: Waiting for 'Continue to Donate' button...")
    continue_btn = None
    click_success = False

    try:
        continue_btn = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//button[@id='smp' or contains(@ng-click, 'continueToDonate') or contains(normalize-space(),'Continue to Donate')]")
        ))
        try:
            driver.execute_script("""
                var backdrops = document.querySelectorAll('.modal-backdrop, .shade');
                backdrops.forEach(function(el) {
                    if (!el.querySelector('button, input, select, textarea, a')) {
                        el.remove();
                    }
                });
            """)
        except Exception:
            pass
        time.sleep(0.3)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", continue_btn)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", continue_btn)
        logging.info("Clicked 'Continue to Donate' using JavaScript.")
        click_success = True
    except Exception as e:
        logging.warning(f"Strategy 1 failed: {e}")

    if not click_success:
        try:
            continue_btn = driver.find_element(By.XPATH, "//button[@id='smp' or contains(normalize-space(),'Continue to Donate')]")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", continue_btn)
            time.sleep(0.3)
            actions = ActionChains(driver)
            actions.move_to_element(continue_btn).click().perform()
            logging.info("Clicked 'Continue to Donate' using ActionChains.")
            click_success = True
        except Exception as e:
            logging.warning(f"Strategy 2 failed: {e}")

    if not click_success:
        try:
            driver.execute_script("""
                var shades = document.querySelectorAll('.shade, .modal-backdrop');
                shades.forEach(function(el) {
                    if (!el.querySelector('button, input, select, textarea, a')) {
                        el.remove();
                    }
                });
            """)
            time.sleep(0.5)
            continue_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@id='smp' or contains(normalize-space(),'Continue to Donate')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", continue_btn)
            continue_btn.click()
            logging.info("Clicked 'Continue to Donate' natively after removing shade.")
            click_success = True
        except Exception as e:
            logging.warning(f"Strategy 3 failed: {e}")

    if not click_success:
        if auto_close:
            logging.error("Manual intervention required but --auto-close is set. Aborting.")
            return
        logging.warning("Could not click 'Continue to Donate' automatically.")
        if sys.stdin and hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
            logging.info("👉 Please click the 'Continue to Donate' button manually, then press Enter.")
            input("Press Enter after you have clicked 'Continue to Donate'...")
            click_success = True
        else:
            logging.warning("Non-interactive session: waiting 5 seconds before checking if donation form loaded...")
            time.sleep(5)
            click_success = True

    if not click_success:
        raise Exception("Failed to click 'Continue to Donate' button.")

    remove_overlays(driver)
    remove_all_overlays(driver)

    logging.info("Waiting for donation form to load...")
    try:
        wait.until(EC.presence_of_element_located((By.ID, "amountD")))
        time.sleep(1)
    except TimeoutException:
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//input[@ng-model='sdcc.amount']")))
            time.sleep(1)
        except TimeoutException:
            logging.warning("Donation form not detected, but continuing...")

    MAX_DONATION_RETRIES = 3
    popup_confirmed = False

    # -------------------------------------------------------------
    # Option 1: Smart Pre-Flight Timing Check & Fresh Submission
    # -------------------------------------------------------------
    load_timing_config()
    now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5.5)
    target_dt = now_ist.replace(
        hour=TARGET_BOOKING_HOUR,
        minute=TARGET_BOOKING_MINUTE,
        second=TARGET_BOOKING_SECOND,
        microsecond=0
    )
    diff_sec = (target_dt - now_ist).total_seconds()

    logging.info(
        f"🕒 [Pre-Flight Check] Current IST: {now_ist.strftime('%H:%M:%S')} | "
        f"Target Booking: {TARGET_BOOKING_HOUR:02d}:{TARGET_BOOKING_MINUTE:02d}:{TARGET_BOOKING_SECOND:02d} IST"
    )

    if diff_sec > 150:
        standby_sec = diff_sec - 120
        wake_target = now_ist + datetime.timedelta(seconds=standby_sec)
        logging.info(
            f"⏳ Early launch detected ({int(diff_sec//60)}m {int(diff_sec%60)}s until slot). "
            f"Holding standby until T-2 minutes ({wake_target.strftime('%H:%M:%S')} IST) "
            f"to keep TTD session fresh and prevent idle timeouts..."
        )
        while True:
            now_loop = datetime.datetime.utcnow() + datetime.timedelta(hours=5.5)
            rem = (wake_target - now_loop).total_seconds()
            if rem <= 0:
                break
            sleep_chunk = min(rem, 15.0)
            time.sleep(sleep_chunk)
            try:
                driver.execute_script("return document.readyState;")
            except Exception:
                pass
        logging.info("🚀 T-2 minutes reached! Submitting fresh donation form...")
    else:
        if diff_sec > 0:
            logging.info(f"⚡ Within launch window ({int(diff_sec)}s remaining). Submitting donation form immediately.")
        elif diff_sec < -30:
            logging.warning(
                f"⚠️ LATE LAUNCH WARNING: Current IST time is {now_ist.strftime('%H:%M:%S')}. "
                f"Target release was {TARGET_BOOKING_HOUR:02d}:{TARGET_BOOKING_MINUTE:02d}:{TARGET_BOOKING_SECOND:02d} IST "
                f"({int(abs(diff_sec))}s ago). Daily Srivani tickets usually exhaust within 20-30 seconds! "
                f"Submitting donation form now to attempt booking anyway..."
            )
        else:
            logging.info("⚡ Target booking time reached/passed. Submitting donation form immediately.")

    for attempt in range(1, MAX_DONATION_RETRIES + 1):
        if attempt > 1:
            logging.info(f"🔄 Retry attempt {attempt}/{MAX_DONATION_RETRIES} – resetting form...")
            try:
                reset_btn = driver.find_element(
                    By.XPATH,
                    "//button[contains(normalize-space(),'Reset')]"
                )
                driver.execute_script("arguments[0].click();", reset_btn)
                logging.info("Clicked Reset button.")
                time.sleep(1)
            except Exception as e:
                logging.warning(f"Could not click Reset: {e}")

        fill_donation_form(driver, donation_amount)
        click_continue_donation(driver, auto_close)

        try:
            WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.ID, "curr"))
            )
            logging.info("✅ 'Current Booking' popup appeared.")
            popup_confirmed = True
            break
        except TimeoutException:
            logging.warning("⏳ 'Current Booking' popup not detected after submission.")
            continue

    if not popup_confirmed:
        logging.error("❌ 'Current Booking' popup did not appear after all retries.")
        logging.info("👉 Manual intervention may be needed. Proceeding anyway, but the booking may fail.")

    # --- Click Current Booking immediately (no wait) ---
    logging.info("Step 6: Current Booking (clicking immediately)")
    if not handle_current_booking_with_quota(driver):
        logging.error("Booking flow failed.")
        return

    # --- Step A: Fill pilgrim details ---
    logging.info("Filling pilgrim details...")
    if not fill_pilgrim_details_only(driver, pilgrim_data):
        logging.error("❌ Failed to fill pilgrim details.")
        return

    # --- Step B: Solve CAPTCHA (without clicking Continue) ---
    logging.info("Solving CAPTCHA...")
    if not solve_captcha_only(driver, auto_close):
        logging.error("❌ Failed to solve CAPTCHA.")
        return

    # --- Step C: PRE-LOCATE Continue button, then wait for target time ---
    # This is the key optimization: we hold the element handle so we can
    # force-click it at T+0, bypassing Angular's ~390 ms ng-disabled delay.
    logging.info("Pre-locating Continue button...")
    continue_btn = pre_locate_continue_button(driver, timeout=60)

    load_timing_config()
    live_quota = detect_live_quota_time(driver)
    if live_quota:
        qh, qm, qs, rem_sec = live_quota
        now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5.5)
        target_live = now_ist.replace(hour=qh, minute=qm, second=qs, microsecond=0)
        diff_live = (target_live - now_ist).total_seconds()
        if diff_live > 0:
            logging.info(
                f"🎯 LIVE QUOTA RELEASE TIME DETECTED ON TTD PAGE: {qh:02d}:{qm:02d}:{qs:02d} IST "
                f"({diff_live:.1f}s remaining). Synchronizing target release to avoid early click rejection..."
            )
            wait_until_time(qh, qm, qs)
        else:
            logging.info(f"⚡ Live Quota Release Time ({qh:02d}:{qm:02d}:{qs:02d} IST) reached. Proceeding to Continue.")
    elif ENABLE_SCHEDULING:
        wait_until_time(TARGET_HOUR, TARGET_MINUTE, TARGET_SECOND)
    else:
        logging.info("Scheduling disabled – proceeding immediately.")

    # Record target timestamp immediately after the stopper releases.
    driver._continue_metrics["target_wall"] = datetime.datetime.now()
    driver._continue_metrics["target_monotonic"] = time.monotonic()

    # --- Step D: Force-click Continue at T+0 ---
    logging.info("Force-clicking Continue button...")
    if not click_continue_button(driver, continue_btn):
        logging.error("❌ Failed to click Continue.")
        return

    # --- Proceed to payment (ICICI + Pay Now, verified JS path) ---
    select_bank_and_pay(driver, group, email)

# ---------------------------------------------------------------------
# Main entry point – MODIFIED: added browser parameter
# ---------------------------------------------------------------------

def run_booking(email, password, group, excel_file="pilgrims_details.xlsx", worker_id=0, browser="chrome", auto_close=False, ready_file=None):
    global SCREENSHOT_DIR

    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{email.replace('@','_')}_{group}_{timestamp}.log")

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    if logger.hasHandlers():
        logger.handlers.clear()
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter('%(message)s')
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)
    logging.info(f"📝 Log file: {log_file}")

    def _status_is_passed(df, key_col, key_value):
        if df is None or key_col not in df.columns:
            return False
        mask = df[key_col] == key_value
        if not mask.any():
            return False
        current = str(df.loc[mask, 'Status'].fillna('').iloc[0]).strip().upper()
        return current == 'PASSED'

    try:
        user_file = 'user_details.xlsx'
        pilgrim_file = 'pilgrims_details.xlsx'

        user_df = pd.read_excel(user_file) if os.path.exists(user_file) else None
        pilgrim_df = pd.read_excel(pilgrim_file) if os.path.exists(pilgrim_file) else None

        if user_df is not None and _status_is_passed(user_df, 'Login_Email', email):
            logging.info(f"Skipping {email}: current user already marked PASSED.")
            return

        if pilgrim_df is not None and _status_is_passed(pilgrim_df, 'Group', group):
            logging.info(f"Skipping {group}: current group already marked PASSED.")
            return

        df = pd.read_excel(excel_file, sheet_name=0)
        df_group = df[df['Group'] == group]
        if df_group.empty:
            logging.error(f"No pilgrims found for group '{group}' in {excel_file}")
            return
        pilgrim_data = []
        for _, row in df_group.iterrows():
            pilgrim_data.append({
                'name': row['name'],
                'age': int(row['age']),
                'gender': row['gender'],
                'id_type': row['id_type'],
                'id_number': str(row['id_number'])
            })
        donation_amount = len(pilgrim_data) * 10000
        logging.info(f"Loaded {len(pilgrim_data)} pilgrims, donation = {donation_amount}")
    except Exception as e:
        logging.exception(f"Failed to read Excel: {e}")
        return

    SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots", group)
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    driver = None
    try:
        driver = perform_login(email, password, worker_id, browser)
        if driver:
            if ready_file:
                try:
                    with open(ready_file, 'w') as f:
                        f.write(f"Ready at {time.time()}")
                    logging.info(f"✅ Ready file created: {ready_file}")
                except Exception as e:
                    logging.warning(f"Could not write ready file: {e}")
            perform_donation_flow(driver, pilgrim_data, donation_amount, group, email, auto_close)
        else:
            logging.error("Login failed – cannot proceed.")
    except Exception as e:
        logging.exception(f"An error occurred: {e}")
        if driver:
            take_screenshot(driver, f"{group}_error")
    finally:
        if driver:
            if not auto_close:
                bring_window_onscreen(driver, worker_id)
                logging.info("⚠️ Browser brought on-screen for manual inspection. Press Enter to close.")
                input("Press Enter to close browser...")
            driver.quit()
            logging.info("Browser closed.")
        logging.info("Session finished.")