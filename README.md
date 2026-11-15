# Tirupati Srivani Booking Automation System

An automated, high-precision booking orchestrator for Tirumala Tirupati Devasthanams (TTD) Srivani Trust darshan bookings.

---

## 📁 Directory Structure

```
daily_srivani_new/
│
├── 🚀 Core Application
│   ├── launcher.py              # Main multi-account scheduler & worker launcher
│   ├── gui.py                   # PyQt graphical control dashboard
│   ├── booking_utils.py         # Automation engine, ONNX RapidOCR & payment flow
│   ├── worker.py                # Standalone child worker process per family
│   ├── check_status.py          # Quick CLI status check & database sync
│   ├── record_success.py        # Automated Excel success logger
│   └── sync_db_to_excel.py      # PostgreSQL <-> Excel bidirectional synchronizer
│
├── 📊 Data & Configuration
│   ├── pilgrims_details.xlsx    # Active pilgrim roster mapped by Family Group
│   ├── user_details.xlsx        # TTD login accounts (email, password, status)
│   ├── successful_bookings.xlsx # Permanent Excel log of all successful bookings
│   └── timing_config.json       # Slot timing and schedule target configuration
│
├── ⚙️ Environment & Setup
│   ├── requirements.txt         # Python dependencies
│   └── setup.bat                # Automated 1-click dependency installer
│
├── 🗄️ database/                 # Database schemas & DB connection scripts
│   ├── postgres_schema.sql      # PostgreSQL DDL table definitions
│   ├── db_connect_example.py    # Database query sample script
│   └── test_db.py               # Database connectivity verification test
│
├── 📚 docs/                     # Analysis, documentation & HAR captures
│   ├── CODE_REVIEW_REPORT.md    # Code audit and latency optimization report
│   ├── advance_booking.md       # TTD booking network protocol breakdown
│   ├── payment.har              # Payment gateway transaction network trace
│   ├── advance_booking_har      # Booking API payload sample
│   ├── app.js                   # TTD Angular frontend client script (reference)
│   └── quota.json               # Quota response JSON structure
│
├── 🧪 testing/                  # OCR test scripts & validation data
│   ├── bulk_ocr_test.py         # Batch OCR benchmark test
│   ├── ocr_testing.py           # Single-image OCR diagnostic script
│   ├── captcha_results.xlsx     # OCR test accuracy records
│   ├── samples/                 # Sample CAPTCHA images for tuning
│   └── debug_ocr/               # OpenCV image pre-processing intermediate filters
│
├── 📦 archive/                  # Legacy and superseded backup scripts
│   ├── bkp/                     # Historical backup copies
│   ├── bakup.py                 # Deprecated monolithic automation
│   ├── booking_utils_old.py     # Previous revision of booking_utils
│   ├── normal_chrome_workers.py # Legacy non-undetected browser worker
│   ├── testing_behaviour.py     # Legacy behavioural test runner
│   ├── ocr_service.py           # Deprecated external FastAPI OCR service
│   ├── quota_poll.py            # Old quota poller
│   ├── system_cleanup.py        # Old process cleanup utility
│   └── auto_click/              # Deprecated browser extension
│
├── 📝 logs/                     # Detailed runtime logs per worker and account
├── 📸 screenshots/              # Step screenshots (CAPTCHA, Confirm, Gateway)
├── 🗂️ sessions/                 # Isolated Chrome user-data profiles
└── 🔒 ready/                    # Process coordination locks (Pay-Now locks)
```

---

## ⚡ Quick Start

### 1. Initial Setup
Run the setup batch file to install all dependencies:
```cmd
setup.bat
```

### 2. Launch Control Panel (GUI)
Start the graphical dashboard to manage accounts, pilgrims, timing, and monitoring:
```cmd
py gui.py
```

### 3. Run Automation Directly
Run the orchestrator directly from the terminal:
```cmd
py launcher.py
```

### 4. Check Current Status
Verify database connectivity, active accounts, and today's bookings:
```cmd
py check_status.py
```

# ticket

