"""
Create (or reuse) an Upstash QStash schedule that pings the Render app every
14 minutes so the free instance never idles into a cold start.

QStash calls GET https://chopbetv2.onrender.com/health on a cron. That endpoint
already exists and is public, so no backend changes or redeploy are needed.

Usage:
    python setup_qstash_keepwarm.py            # create/reuse the schedule
    python setup_qstash_keepwarm.py --delete   # remove the keep-warm schedule

Reads QSTASH_TOKEN (and optional QSTASH_URL) from the environment / .env.
Idempotent: if a schedule already targets the same URL, it is left in place.
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

QSTASH_TOKEN = os.getenv("QSTASH_TOKEN")
QSTASH_BASE = os.getenv("QSTASH_URL", "https://qstash.upstash.io").rstrip("/")
TARGET_URL = os.getenv("KEEPWARM_URL", "https://chopbetv2.onrender.com/health")
CRON = "*/14 * * * *"  # every 14 minutes


def _headers() -> dict:
    return {"Authorization": f"Bearer {QSTASH_TOKEN}"}


def list_schedules() -> list[dict]:
    resp = requests.get(f"{QSTASH_BASE}/v2/schedules", headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def find_existing(schedules: list[dict]) -> dict | None:
    for s in schedules:
        if s.get("destination") == TARGET_URL:
            return s
    return None


def create_schedule() -> None:
    # Destination URL goes in the path; QStash calls it with the method below.
    resp = requests.post(
        f"{QSTASH_BASE}/v2/schedules/{TARGET_URL}",
        headers={
            **_headers(),
            "Upstash-Cron": CRON,
            "Upstash-Method": "GET",
            # Don't hammer the app with retries if a single ping fails.
            "Upstash-Retries": "1",
        },
        timeout=30,
    )
    resp.raise_for_status()
    schedule_id = resp.json().get("scheduleId", "?")
    print(f"Created keep-warm schedule (id={schedule_id})")
    print(f"  {CRON}  ->  GET {TARGET_URL}")


def delete_schedules() -> None:
    existing = [s for s in list_schedules() if s.get("destination") == TARGET_URL]
    if not existing:
        print(f"No keep-warm schedule found for {TARGET_URL}.")
        return
    for s in existing:
        sid = s["scheduleId"]
        resp = requests.delete(f"{QSTASH_BASE}/v2/schedules/{sid}", headers=_headers(), timeout=30)
        resp.raise_for_status()
        print(f"Deleted schedule {sid} ({TARGET_URL})")


def main() -> None:
    if not QSTASH_TOKEN:
        print("QSTASH_TOKEN is not set in the environment / .env. Aborting.")
        sys.exit(1)

    if "--delete" in sys.argv:
        delete_schedules()
        return

    existing = find_existing(list_schedules())
    if existing:
        print(f"Keep-warm schedule already exists (id={existing['scheduleId']}, cron={existing.get('cron')}).")
        print("Nothing to do. Use --delete to remove it.")
        return

    create_schedule()


if __name__ == "__main__":
    main()
