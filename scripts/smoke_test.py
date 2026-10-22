"""
RevPilot AI — Smoke Test Script
Verifies health, database connectivity, and core business endpoints against any running instance.
Usage:
    python scripts/smoke_test.py --base-url http://127.0.0.1:8000
"""

import sys
import argparse
import urllib.request
import json

def run_smoke_test(base_url: str):
    base_url = base_url.rstrip("/")
    print(f"=== Running RevPilot AI Smoke Test against: {base_url} ===")
    
    endpoints = [
        ("/api/health", "Health & DB Connectivity"),
        ("/api/dashboard/metrics", "Dashboard Live Metrics"),
        ("/api/deals", "Deals Pipeline & Risk Index"),
        ("/api/conversations", "Intelligence Inbox Conversations"),
        ("/api/routing/rules", "Explainable Routing Rules"),
        ("/api/actions", "Prioritized Action Queue"),
        ("/api/findings", "Dynamic Findings & Evidence Report"),
    ]
    
    passed = 0
    failed = 0
    
    for path, description in endpoints:
        url = f"{base_url}{path}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RevPilot-SmokeTest/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                status_code = resp.getcode()
                raw_body = resp.read().decode("utf-8")
                data = json.loads(raw_body)
                
                if status_code == 200:
                    print(f" [PASS] {description} ({path}) -> HTTP 200")
                    if path == "/api/health":
                        db_status = data.get("database")
                        print(f"        DB Status: {db_status} | Version: {data.get('app_version')}")
                        if db_status != "connected":
                            print(f" [FAIL] Database connectivity reported as: {db_status}")
                            failed += 1
                            continue
                    passed += 1
                else:
                    print(f" [FAIL] {description} ({path}) -> HTTP {status_code}")
                    failed += 1
        except Exception as e:
            print(f" [FAIL] {description} ({path}) -> Error: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"Smoke Test Summary: {passed} passed, {failed} failed")
    print("=" * 50)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("ALL SMOKE CHECKS PASSED SUCCESSFULLY.")
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RevPilot AI Smoke Test")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL of target instance")
    args = parser.parse_args()
    run_smoke_test(args.base_url)
