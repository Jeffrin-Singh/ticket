# Code Review: Current vs Backup (BKP)
## Robustness Analysis – Booking Utils

**Date:** 2026-08-15  
**Scope:** Read-only comparison; no modifications made

---

## 1. OVERALL VERDICT

**The backup code (bkp/booking_utils_old.py) is SIGNIFICANTLY MORE ROBUST than the current code.**

The current version has been simplified for ease of maintenance but **at the cost of critical reliability features**. Key production-grade safeguards have been removed:
- No browser fingerprinting/anti-detection
- No visual payment verification
- No elapsed-time tracking
- No atomic Excel updates
- No comprehensive screenshot diagnostics
- Shorter/riskier timeouts

---

## 2. KEY IMPROVEMENTS IN CURRENT CODE

| Feature | Current | BKP | Verdict |
|---------|---------|-----|---------|
| **Code simplicity** | ✅ Cleaner, fewer dependencies | ❌ Complex, many helpers | Current wins |
| **Maintenance burden** | ✅ Fewer function parameters | ❌ Extended signatures | Current wins |
| **LOC count** | ✅ ~1550 lines | ❌ ~2300 lines | Current wins |
| **Import overhead** | ✅ Minimal (no config, filelock, threading) | ❌ Heavy (config, google_sheets, filelock) | Current wins |
| **Startup time** | ✅ Simpler browser init | ❌ More setup (stealth JS, CDP) | Current wins |

**Takeaway:** Current code is leaner but less armored.

---

## 3. WEAKNESSES STILL PRESENT IN CURRENT CODE

### A. Browser Anti-Detection & Stealth
**Risk Level: HIGH**

| Aspect | Current | BKP |
|--------|---------|-----|
| User-agent randomization | ❌ None | ✅ Random pool |
| Window size randomization | ❌ None | ✅ Random pool |
| WebGL fingerprint randomization | ❌ None | ✅ Random pool |
| Locale/Audio randomization | ❌ None | ✅ Random pool |
| CDP stealth JS injection | ❌ None | ✅ Yes (via build_stealth_js) |
| Network blocking | ❌ None | ✅ Yes (tracking URLs) |

**Impact:** Current browser startup is predictable, more likely to be detected/blocked by anti-bot.

**Code Reference:**
- Current: `perform_login()` [lines 1154-1220]
- BKP: `perform_login()` [lines 1871-1950] – Has randomized fingerprinting + CDP injection

---

### B. Payment Flow Verification
**Risk Level: CRITICAL**

**Current approach (lines 987-1095 in current):**
```
select_bank_and_pay(driver, group):
  - Wait for radio button
  - Click radio
  - Click Pay Now
  - Check window handles for new popup
  - Use text-based keywords to detect popup
  - Return immediately without confirmation
  ❌ NO VISUAL VERIFICATION
```

**BKP approach (lines 1480-1700+ in backup):**
```
select_bank_and_pay(driver, group, email, booking_start_ts, screenshot_dir):
  - All of above, PLUS:
  - Call mark_passed_if_screenshot_matches()
  - Visual comparison: ORB alignment + QR masking + SSIM score
  - Compare against reference img/success.png
  - Only mark PASSED if similarity >= threshold
  - Save diagnostic screenshots
  ✅ VISUAL + TEXT VERIFICATION
```

**Impact:** Current code marks payments as successful based on weak text detection. Could report false positives if:
- Modal has different layout
- Keywords change
- Modal appears but doesn't actually trigger payment

**Exact Risk Points:**
- Line 1046 in current: `# Text-based popup detection is kept ONLY for diagnostic logging` – but NO visual verification fallback
- No image comparison logic
- No reference image at all

---

### C. Donation Form State Synchronization
**Risk Level: HIGH**

**Current (lines 1068-1097):**
```python
def fill_donation_form(driver, amount):
    amount_input.send_keys(str(amount))
    # No verification that Angular model updated
    # No sync event firing
    # No wait-for-value confirmation
```

**BKP (lines 1752-1810):**
```python
def fill_donation_form(driver, amount):
    amount_input.send_keys(amount_value)
    _fire_angular_sync_events(driver, amount_input)  # Trigger model update
    if not _wait_for_input_value(...):  # Verify value settled
        amount_input.clear()
        amount_input.send_keys(amount_value)
        _fire_angular_sync_events(driver, amount_input)
    # Same for checkboxes: click + sync + verify state
```

**Impact:** Current form fills may fail silently if Angular model doesn't update. BKP verifies state with polling.

---

### D. Current Booking Timeout
**Risk Level: MEDIUM**

| Timeout | Current | BKP | Impact |
|---------|---------|-----|--------|
| Current Booking clickable wait | 1s | 5s | Current: 80% faster to fail |
| Render stabilization buffer | None | 0.2s | Current: No buffer for modal animation |

**Line references:**
- Current: line 720 – `WebDriverWait(driver, 1)`
- BKP: line 1110 – `WebDriverWait(driver, 5, poll_frequency=0.1)` + `time.sleep(0.2)`

**Impact:** Current may click too early, before popup animation completes, causing click to miss.

---

### E. Quota Detection & Buffer Timing
**Risk Level: MEDIUM**

**Current (lines 1130-1145):**
```python
extra_delay = min(elapsed + 0.4, 0.7)
# RISK: adds elapsed time to buffer
# If quota appears at 0.3s, waits 0.7s (0.3 + 0.4)
# If quota appears at 2s, waits only 2.4s (capped at 0.7s)
# Logic is inverted – less buffer for slow quota
```

**BKP (line 1855):**
```python
extra_delay = min(elapsed * 0.2, 0.35)
# More sensible: percentage-based buffer
# If quota at 0.5s, waits 0.1s
# If quota at 2s, waits 0.35s (max)
```

**Impact:** Current quota buffer timing is counterintuitive; may fail to give enough buffer on slow quota.

---

## 4. WHAT BKP CODE DID BETTER

### A. Comprehensive Diagnostics & Screenshots
**Advantage: YES (BKP is much stronger)**

| Diagnostic | Current | BKP |
|-----------|---------|-----|
| Session-specific screenshot dir | ❌ Global SCREENSHOT_DIR | ✅ session_screenshot_dir per worker |
| Group-level logging | ❌ No | ✅ Yes (group param throughout) |
| Failure screenshots | ⚠️ Basic | ✅ At every failure point (_form_not_found, _captcha_not_found, _continue_timeout, _payment_detected, etc.) |
| Driver health check | ❌ None | ✅ `_driver_alive()` guards screenshot calls |
| Debug page dumps | ⚠️ Exists but unused | ✅ save_page_debug() actively called |
| Screenshot comparison logs | ❌ None | ✅ Detailed SSIM scores and alignment info |

**Code References:**
- Current: `take_screenshot(driver, prefix, suffix)` [line 413]
- BKP: `take_screenshot(driver, screenshot_dir, prefix, suffix)` [line 819] – much more robust

---

### B. Excel Status Tracking & Atomic Updates
**Advantage: YES (BKP only has this)**

**Current:** No Excel tracking whatsoever.

**BKP:** [lines 1680-1730]
```python
update_excel_status(file_path, key_col, key_value, new_status):
  - Uses filelock.FileLock for atomic updates
  - Prevents concurrent Excel corruption
  - Tracks "PASSED" / "FAILED" status
  - Records elapsed time

mark_passed(email, group):
  - Atomically marks both USER_EXCEL and PILGRIM_EXCEL
  - Called only after visual screenshot match
```

**Impact:** Current bookings have no persistent record of success/failure. BKP tracks every attempt atomically.

---

### C. Visual Payment Modal Verification
**Advantage: YES (BKP only has this)**

**Current:** Text keyword search only. No image comparison.

**BKP:** [lines 1670-1750]
```python
mark_passed_if_screenshot_matches():
  - Takes screenshot of payment page
  - Compares with reference img/success.png
  - Uses 3 strategies:
    1. ORB feature alignment (finds matching regions)
    2. QR code masking (ignores dynamic QR in comparison)
    3. SSIM score (structural similarity index)
  - Weighted final score: SSIM_CROP_WEIGHT * score_crop + SSIM_FULL_WEIGHT * score_full
  - Only marks PASSED if >= SCREENSHOT_MATCH_THRESHOLD

Helper functions:
  - _resize_for_comparison()
  - _detect_qr_mask()
  - _align_images_orb()
  - compare_images()
```

**Impact:** BKP has robust visual confirmation. Current relies on fragile text matching.

**Risk in Current:**
- No reference image
- No image comparison imports (no skimage.metrics.ssim)
- No ORB alignment
- No QR detection
- Modal could render differently but text keywords still match → false positive

---

### D. Performance Timing & Metrics
**Advantage: YES (BKP only has this)**

**Current:** No timing tracking.

**BKP:** [lines 1850+]
```python
_record_step_timing(stage_name, start_time):
  - Records perf_counter() for each stage
  - Used to log: "Current Booking clicked", "Browser ready", "Quota loaded", "Payment page", etc.
  - Helps identify bottlenecks

Also: elapsed_seconds recording for "Current Booking → Pay Now" interval
```

**Impact:** BKP can identify performance regressions. Current is a black box.

---

### E. Advanced Browser Initialization
**Advantage: YES (BKP only has this)**

**Current:** Basic options only.

**BKP:**
- Random user-agent from pool
- Random window size from pool
- Random locale from pool
- Random WebGL fingerprint
- Random audio sample rate
- CDP stealth JS injection via `build_stealth_js()`
- Network blocking for tracking URLs
- DNS-over-HTTPS configuration

**Impact:** BKP can evade basic anti-bot detection. Current is easily identifiable.

---

### F. Logging Configuration
**Advantage: YES (BKP only has this)**

**Current:**
```python
logging.basicConfig(level=logging.INFO)
# All libraries log at INFO level
```

**BKP:**
```python
_root_logger.setLevel(logging.INFO)
# Explicitly silence noisy libraries:
for _lib_name in ["selenium", "urllib3", "undetected_chromedriver", ...]:
    logging.getLogger(_lib_name).setLevel(logging.WARNING)
# Much cleaner console output
```

**Impact:** BKP has better signal-to-noise in logs.

---

### G. Click Continuation Robustness (Donation)
**Advantage: YES (BKP is more robust)**

**Current (line 1099-1115):**
```python
def click_continue_donation(driver, auto_close=False):
    continue_submit = WebDriverWait(driver, 10).until(...)
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", continue_submit)
    time.sleep(0.3)
    driver.execute_script("arguments[0].click();", continue_submit)
    return True
```

**BKP (line 1797-1850):**
```python
def click_continue_donation(driver, auto_close=False):
    continue_submit = WebDriverWait(driver, 10, poll_frequency=0.1).until(...)
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", continue_submit)
    
    # VERIFY button is not disabled before clicking
    WebDriverWait(driver, 2, poll_frequency=0.05).until(
        lambda d: not d.execute_script(
            "return !!arguments[0].disabled || arguments[0].getAttribute('disabled') !== null || arguments[0].getAttribute('aria-disabled') === 'true';",
            continue_submit
        )
    )
    
    time.sleep(0.2)
    driver.execute_script("arguments[0].click();", continue_submit)
    
    # Wait for Current Booking popup to appear
    try:
        WebDriverWait(driver, 6, poll_frequency=0.1).until(
            lambda d: d.execute_script("return !!document.getElementById('curr');")
        )
        logging.info("✅ Current Booking popup appeared after Continue.")
    except TimeoutException:
        logging.warning("Current Booking popup not visible immediately...")
    return True
```

**Impact:** BKP verifies button is enabled and waits for confirmation popup. Current just clicks and hopes.

---

## 5. WHAT IS MORE ROBUST IN CURRENT CODE AND WHY

### Simplicity as a Feature

**Areas where current is actually more reliable:**

| Area | Current | BKP | Why Current Wins |
|------|---------|-----|------------------|
| **Fewer dependencies** | No config.py needed | Requires config.py + stealth_browser.py | Current more self-contained |
| **Fewer failure points** | Simpler browser init (fewer options) | 15+ Chrome options + CDP calls | Fewer options = fewer places to break |
| **No Google Sheets** | Excel only | Can read Google Sheets OR Excel | Google Sheets adds failure mode |
| **No file locking** | Direct file access | Uses filelock library | Less dependency on external lib |
| **Smaller memory footprint** | Basic logging | Full logging setup + silence rules | Current uses less RAM |

**Verdict:** Current is more "robust" in the sense of being simpler and having fewer dependencies. But this is **negative robustness** – it achieves stability by cutting features, not by improving them.

---

## 6. RISK POINTS WITH EXACT REFERENCES

### CRITICAL RISKS (Current Code)

| Risk | Location | Severity | Why |
|------|----------|----------|-----|
| **False payment success** | Lines 1046-1095 (select_bank_and_pay) | 🔴 CRITICAL | Text-based detection only; no visual verification |
| **No status tracking** | Line 1482 (run_booking) | 🔴 CRITICAL | No record of which bookings succeeded; can't resume |
| **Browser too easily detected** | Lines 1154-1220 (perform_login) | 🔴 CRITICAL | No stealth features; predictable fingerprint |
| **Current Booking timeout too short** | Line 720 | 🟠 HIGH | 1s timeout may click before popup settles |
| **No Angular state verification** | Line 1068-1097 (fill_donation_form) | 🟠 HIGH | Form fill may fail silently if model doesn't update |

### MEDIUM RISKS (Current Code)

| Risk | Location | Severity | Why |
|------|----------|----------|-----|
| **Quota buffer logic backwards** | Lines 1130-1145 | 🟠 HIGH | extra_delay calculation favors fast quota |
| **No screenshot diagnostics** | Lines 413, 1505 | 🟡 MEDIUM | Hard to debug failures without screenshots |
| **No driver health check** | Line 1505 (finally block) | 🟡 MEDIUM | Could crash trying to screenshot dead driver |
| **Manual input on every failure** | Line 1115 | 🟡 MEDIUM | Not suitable for fully automated runs |

---

## 7. FINAL CONCLUSION: IS CURRENT CODE MORE ROBUST THAN BKP?

### Direct Answer: **NO. BKP is significantly more robust.**

### Summary:

| Dimension | Current | BKP | Winner |
|-----------|---------|-----|--------|
| **Anti-bot evasion** | ❌ None | ✅ Advanced | BKP |
| **Payment verification** | ⚠️ Text only | ✅ Visual + Text | BKP |
| **Status persistence** | ❌ None | ✅ Atomic Excel | BKP |
| **Diagnostics** | ⚠️ Basic | ✅ Comprehensive | BKP |
| **Timing accuracy** | ❌ No tracking | ✅ Perf counters | BKP |
| **Error handling** | ⚠️ Logs only | ✅ Screenshots + logs | BKP |
| **Form state safety** | ❌ Fire and forget | ✅ Verify + retry | BKP |
| **Browser timeouts** | ❌ Risky short | ✅ Conservative long | BKP |
| **Code complexity** | ✅ Simple | ❌ Complex | Current |
| **Maintenance burden** | ✅ Light | ❌ Heavy | Current |

### Trade-off Analysis:

**BKP Wins Because:**
1. ✅ Visual payment verification (no false positives)
2. ✅ Stealth browser fingerprinting (harder to detect/block)
3. ✅ Atomic Excel tracking (can resume, no data loss)
4. ✅ Comprehensive debugging (screenshots at every failure)
5. ✅ Angular form state verification (no silent fails)
6. ✅ Conservative timeouts (lower click-miss risk)
7. ✅ Performance metrics (can identify bottlenecks)

**Current Wins Because:**
1. ✅ Simpler codebase (fewer dependencies)
2. ✅ Faster startup (no fingerprinting)
3. ✅ Smaller memory footprint
4. ✅ Easier to maintain
5. ✅ No external config file required

### Robustness Verdict:

**If the goal is to reliably complete bookings:**
- **BKP is MORE robust** because it has safeguards against false positives, detection, and silent failures.

**If the goal is to maintain simple, dependency-light code:**
- **Current is MORE robust** because it has fewer failure points.

**For production use with concurrent workers and financial transactions, BKP's robustness far outweighs the added complexity.**

---

## Recommendations (Read-Only Analysis Only)

No changes recommended per requirements. This analysis is for evaluation purposes only.

**For future reference:**
- If current code is experiencing false-positive payment confirmations → adopt BKP's visual screenshot verification
- If current code is being blocked by anti-bot systems → adopt BKP's fingerprinting + stealth JS injection
- If tracking/audit of bookings is needed → adopt BKP's atomic Excel status updates
- If debugging failures is taking too long → adopt BKP's screenshot + group logging strategy

