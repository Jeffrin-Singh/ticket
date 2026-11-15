"""
worker.py - one booking session for a single family.
Called by launcher.py with command-line arguments.
"""

import argparse
import os
import sys
import time

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

parser = argparse.ArgumentParser(description='Tirupati Balaji Booking Worker')
parser.add_argument('--email', required=True, help='Login email')
parser.add_argument('--password', required=True, help='Login password')
parser.add_argument('--group', required=True, help='Family group name')
parser.add_argument('--excel', default='pilgrims_details.xlsx', help='Excel file with pilgrim data')
parser.add_argument('--worker-id', type=int, default=0, help='Worker index for window positioning and profile isolation')
parser.add_argument('--browser', default='chromium', choices=['chrome', 'chromium'],
                    help='Browser to use: chromium (default) or chrome')
parser.add_argument('--auto-close', action='store_true', help='Close browser without manual prompt')
parser.add_argument('--show-browser', action='store_true', help='Show browser window visibly on screen instead of ghost off-screen mode')
from booking_utils import run_booking

def main(args):
    ready_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ready")
    os.makedirs(ready_dir, exist_ok=True)
    ready_file = os.path.join(ready_dir, f"{args.group}_{args.worker_id}.ready")
    if os.path.exists(ready_file):
        os.remove(ready_file)

    run_booking(args.email, args.password, args.group, args.excel,
                args.worker_id, args.browser, args.auto_close, ready_file)

if __name__ == '__main__':
    args = parser.parse_args()
    if getattr(args, 'show_browser', False):
        os.environ['SHOW_BROWSER'] = '1'

    cache_dir = os.environ.get('UNDETECTED_CHROMEDRIVER_CACHE_DIR')
    if not cache_dir:
        cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "undetected_cache", f"worker_{args.worker_id}")
        os.makedirs(cache_dir, exist_ok=True)
        os.environ['UNDETECTED_CHROMEDRIVER_CACHE_DIR'] = cache_dir

    print(f"🔧 Worker using cache dir: {os.environ['UNDETECTED_CHROMEDRIVER_CACHE_DIR']}")
    main(args)