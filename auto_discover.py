"""Background auto-discover daemon.

Reads a queue of scrape jobs from auto_discover_queue.json, runs them
sequentially via lib.discover_and_draft, writes status + log files that
the portal can poll.

Survives portal restart. Stop with: SIGTERM to PID, or portal Stop button.

Spawned by lib.start_auto_discover() as detached subprocess.
"""
import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).parent
sys.path.insert(0, str(SKILL_DIR))
import lib

# Re-use same path constants from lib
QUEUE_FILE = lib.AUTO_DISCOVER_QUEUE_FILE
LOG_FILE = lib.AUTO_DISCOVER_LOG_FILE
STATUS_FILE = lib.AUTO_DISCOVER_STATUS_FILE
PID_FILE = lib.AUTO_DISCOVER_PID_FILE


def log(msg):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{stamp}] {msg}\n")


def update_status(**kwargs):
    status = {}
    if STATUS_FILE.exists():
        try:
            status = json.loads(STATUS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            status = {}
    status.update(kwargs)
    status["updated_at"] = datetime.now().isoformat()
    tmp = STATUS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(status, indent=2))
    tmp.replace(STATUS_FILE)


def cleanup_and_exit(*_):
    log("Received SIGTERM, exiting.")
    update_status(running=False, current_job=None, finished_reason="killed")
    PID_FILE.unlink(missing_ok=True)
    sys.exit(0)


def main():
    signal.signal(signal.SIGTERM, cleanup_and_exit)
    signal.signal(signal.SIGINT, cleanup_and_exit)

    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))

    if not QUEUE_FILE.exists():
        log("No queue file. Exiting.")
        PID_FILE.unlink(missing_ok=True)
        return

    try:
        queue = json.loads(QUEUE_FILE.read_text())
    except (json.JSONDecodeError, OSError) as e:
        log(f"Failed to read queue: {e}")
        PID_FILE.unlink(missing_ok=True)
        return

    apify, gemini = lib.load_env()
    if not apify or not gemini:
        log("Missing APIFY_TOKEN or GEMINI_API_KEY in .env. Exiting.")
        PID_FILE.unlink(missing_ok=True)
        return

    total_jobs = len(queue)
    log(f"Starting auto-discover: {total_jobs} jobs queued")
    update_status(
        running=True,
        started_at=datetime.now().isoformat(),
        total_jobs=total_jobs,
        completed_jobs=0,
        total_inserted=0,
        total_skipped=0,
    )

    grand_inserted = 0
    grand_skipped = 0

    for i, job in enumerate(queue):
        niche = job.get("niche")
        area = job.get("area")
        count = int(job.get("count", 100))
        mode = job.get("mode", "text")

        label = f"{niche} | {area} | {count} | {mode}"
        log(f"Job {i + 1}/{total_jobs}: {label}")
        update_status(
            current_job=label,
            current_job_index=i,
            current_progress="Scraping Google Maps...",
        )

        try:
            def scrape_cb(done, total, elapsed, status):
                update_status(
                    current_progress=f"🛰️ Apify: {done}/{total or '?'} | {elapsed}s | {status}"
                )

            def draft_cb(j, total, name):
                update_status(
                    current_progress=f"✍️ Drafting {j + 1}/{total}: {name[:30]}"
                )

            inserted, skipped = lib.discover_and_draft(
                niche, area, count, mode, apify, gemini,
                progress_callback=draft_cb,
                scrape_progress_callback=scrape_cb,
            )
            grand_inserted += inserted
            grand_skipped += skipped
            log(f"  ✅ {inserted} inserted, {skipped} skipped (dup)")
            update_status(
                completed_jobs=i + 1,
                total_inserted=grand_inserted,
                total_skipped=grand_skipped,
            )
        except Exception as e:
            log(f"  ❌ FAILED: {type(e).__name__}: {str(e)[:200]}")
            update_status(last_error=str(e)[:300])

        # 30 sec gap between jobs (Gemini quota relief)
        if i < total_jobs - 1:
            log(f"  Sleeping 30s before next job...")
            for _ in range(30):
                time.sleep(1)

    log(f"All {total_jobs} jobs done. Grand total: {grand_inserted} new leads, {grand_skipped} dups.")
    update_status(
        running=False,
        current_job=None,
        current_progress="✅ All jobs done",
        finished_at=datetime.now().isoformat(),
        finished_reason="completed",
    )
    PID_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
