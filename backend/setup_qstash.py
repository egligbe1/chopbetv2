"""
Configure Upstash QStash to TRIGGER the backend's scheduled jobs over HTTP so
the Render service can sleep between runs (free-tier hour budget).

Creates two schedules that POST to the secret-protected cron endpoints:
  - 07:00 UTC daily         -> /admin/cron/predictions   (generate predictions)
  - every 4h (0/4/8/.../20) -> /admin/cron/results        (check scores)

Each call wakes the backend, runs the job (endpoint returns 202 immediately and
works in the background), then the service idles back to sleep. Also removes the
old always-on /health keep-warm schedule (which kept the service awake 24/7).

Reads from env / .env:  QSTASH_TOKEN, CRON_SECRET, optional QSTASH_URL and
BACKEND_URL (default https://chopbetv2.onrender.com).

Usage:
    python setup_qstash.py            # create/reuse cron schedules, drop keep-warm
    python setup_qstash.py --list     # list current schedules
    python setup_qstash.py --delete   # remove the cron schedules this script manages
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

QSTASH_TOKEN = os.getenv("QSTASH_TOKEN")
QSTASH_BASE = os.getenv("QSTASH_URL", "https://qstash.upstash.io").rstrip("/")
CRON_SECRET = os.getenv("CRON_SECRET", "")
BACKEND_URL = os.getenv("BACKEND_URL", "https://chopbetv2.onrender.com").rstrip("/")

PREDICTIONS_URL = f"{BACKEND_URL}/admin/cron/predictions"
RESULTS_URL = f"{BACKEND_URL}/admin/cron/results"

# (destination, cron) — cron in UTC
SCHEDULES = [
    (PREDICTIONS_URL, "0 7 * * *"),            # 07:00 UTC daily
    (RESULTS_URL, "0 0,4,8,12,16,20 * * *"),   # every 4 hours
]


def _headers() -> dict:
    return {"Authorization": f"Bearer {QSTASH_TOKEN}"}


def list_schedules() -> list[dict]:
    r = requests.get(f"{QSTASH_BASE}/v2/schedules", headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def delete_schedule(schedule_id: str, label: str) -> None:
    r = requests.delete(f"{QSTASH_BASE}/v2/schedules/{schedule_id}", headers=_headers(), timeout=30)
    r.raise_for_status()
    print(f"  deleted {schedule_id} ({label})")


def create_schedule(destination: str, cron: str) -> None:
    r = requests.post(
        f"{QSTASH_BASE}/v2/schedules/{destination}",
        headers={
            **_headers(),
            "Upstash-Cron": cron,
            "Upstash-Method": "POST",
            # QStash forwards any Upstash-Forward-* header to the destination.
            "Upstash-Forward-X-Cron-Secret": CRON_SECRET,
            "Upstash-Retries": "2",
        },
        timeout=30,
    )
    r.raise_for_status()
    print(f"  created {cron}  ->  POST {destination}  (id={r.json().get('scheduleId','?')})")


def main() -> None:
    if not QSTASH_TOKEN:
        print("QSTASH_TOKEN is not set in the environment / .env. Aborting.")
        sys.exit(1)

    existing = list_schedules()

    if "--list" in sys.argv:
        for s in existing:
            print(f"  {s.get('scheduleId')}  {s.get('cron'):<20}  -> {s.get('destination')}")
        return

    managed = {PREDICTIONS_URL, RESULTS_URL}

    if "--delete" in sys.argv:
        for s in existing:
            if s.get("destination") in managed:
                delete_schedule(s["scheduleId"], s.get("destination"))
        print("Done.")
        return

    if not CRON_SECRET:
        print("CRON_SECRET is not set — the cron endpoints would reject QStash. Set it first. Aborting.")
        sys.exit(1)

    # Remove the old always-on keep-warm schedule (kept the service awake 24/7).
    for s in existing:
        dest = s.get("destination", "")
        if dest.endswith("/health"):
            delete_schedule(s["scheduleId"], "old keep-warm /health")

    # Create the cron trigger schedules (idempotent: skip if destination exists).
    existing_dests = {s.get("destination") for s in existing}
    for dest, cron in SCHEDULES:
        if dest in existing_dests:
            print(f"  schedule already exists for {dest} — leaving as-is")
            continue
        create_schedule(dest, cron)

    print("Done. Backend will now be woken by QStash only at run times and can sleep otherwise.")


if __name__ == "__main__":
    main()
