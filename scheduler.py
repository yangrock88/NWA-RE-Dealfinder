"""
Auto-update scheduler for the NWA Real Estate Deal Finder.

Modes:
  python scheduler.py             # runs once, then loops every 6 hours
  python scheduler.py --once      # single run, then exit
  python scheduler.py --interval 120  # loop every 120 minutes
  python scheduler.py --register  # register Windows Task Scheduler job

The scheduler:
  1. Scrapes all configured sources
  2. Compares against data/latest.json (last run's results)
  3. Fires Windows notification if new deals appeared
  4. Writes updated data/latest.json + deals_report.html
"""
import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("data/scheduler.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("scheduler")

# ── Paths ──────────────────────────────────────────────────────────────────────
HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
SNAPSHOT_PATH = DATA_DIR / "latest.json"
REPORT_PATH = HERE / "deals_report.html"

DATA_DIR.mkdir(exist_ok=True)

_GIT = r"C:\Program Files\Git\cmd\git.exe"


# ── Git auto-publish ────────────────────────────────────────────────────────────────────────

def _push_report(report_path: Path) -> None:
    """Commit the updated dashboard to git and push to GitHub Pages.
    Runs silently; a failure here never interrupts the main pipeline."""
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run([_GIT, "add", str(report_path)],
                       cwd=HERE, capture_output=True, timeout=15)
        result = subprocess.run(
            [_GIT, "commit", "-m", f"Dashboard refresh — {ts}"],
            cwd=HERE, capture_output=True, text=True, timeout=15,
        )
        if "nothing to commit" in (result.stdout + result.stderr).lower():
            log.debug("Git: dashboard unchanged, skipping push")
            return
        subprocess.run([_GIT, "push"],
                       cwd=HERE, capture_output=True, timeout=30)
        log.info("Dashboard pushed to GitHub Pages (%s)", ts)
    except Exception as exc:
        log.debug("Git push skipped: %s", exc)


# ── Snapshot helpers ────────────────────────────────────────────────────────────────────────

def _load_snapshot() -> dict:
    if SNAPSHOT_PATH.exists():
        try:
            return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"listings": [], "run_ts": None}


def _save_snapshot(results: dict) -> None:
    snapshot = {
        "listings": results.get("all_listings", []),
        "run_ts": datetime.now().isoformat(),
        "area_median_ppqft": results.get("area_median_ppqft"),
        "deal_count": len(results.get("deals", [])),
    }
    SNAPSHOT_PATH.write_text(
        json.dumps(snapshot, indent=2, default=str),
        encoding="utf-8",
    )


def _find_new_deals(prev_snapshot: dict, current_results: dict) -> list[dict]:
    """Return deals that are new since the last snapshot."""
    prev_addrs = {
        l.get("address", "").lower().strip()
        for l in prev_snapshot.get("listings", [])
        if l.get("is_deal")
    }
    return [
        l for l in current_results.get("deals", [])
        if l.get("address", "").lower().strip() not in prev_addrs
    ]


# ── One full scrape + report cycle ────────────────────────────────────────────

def run_once(report_path: str = str(REPORT_PATH), open_browser: bool = False) -> dict:
    """
    Full pipeline: scrape → analyze → compare → notify → report.
    Returns the analysis results dict.
    """
    log.info("=" * 60)
    log.info("Starting scrape run at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    t0 = time.time()

    # ── 1. Zillow market data (optional, fast) ─────────────────────────────────
    area_median_override = None
    try:
        from sources.zillow_csv import get_area_median_price_per_sqft
        area_median_override = get_area_median_price_per_sqft()
    except Exception as exc:
        log.debug("Zillow CSV skipped: %s", exc)

    # ── 2. Scrape active listings ──────────────────────────────────────────────
    active: list[dict] = []

    sources = {
        "craigslist": "sources.craigslist",
        "homepath":   "sources.homepath",
        "hud":        "sources.hud",
        "auction":    "sources.auction",
    }
    for name, module_path in sources.items():
        try:
            import importlib
            mod = importlib.import_module(module_path)
            batch = mod.fetch_listings()
            log.info("%-12s  %d listings", name, len(batch))
            active.extend(batch)
        except Exception as exc:
            log.warning("Source %s failed: %s", name, exc)

    # Deduplicate by address
    seen: set[str] = set()
    deduped = []
    for l in active:
        key = l.get("address", "").lower().strip()
        if not key or key not in seen:
            if key:
                seen.add(key)
            deduped.append(l)

    # ── 3. Analyze ─────────────────────────────────────────────────────────────
    from analysis import analyze, compute_area_median
    results = analyze(deduped, [])

    # Override median with Zillow data if available
    if area_median_override and area_median_override > 0:
        log.info("Using Zillow market data: $%.0f/sqft", area_median_override)
        # Re-score with updated median
        from analysis import score_listing
        rescored = [score_listing(l, area_median_override) for l in deduped]
        rescored.sort(key=lambda x: x["deal_score"], reverse=True)
        results["deals"] = [l for l in rescored if l["is_deal"]]
        results["regular"] = [l for l in rescored if not l["is_deal"]]
        results["all_listings"] = rescored
        results["area_median_ppqft"] = area_median_override

    # ── 4. Compare with previous snapshot ─────────────────────────────────────
    prev = _load_snapshot()
    new_deals = _find_new_deals(prev, results)
    new_addrs = {l.get("address", "").lower() for l in new_deals}

    if new_deals:
        log.info("NEW DEALS FOUND: %d", len(new_deals))
        for d in new_deals:
            log.info("  + %s — $%s", d.get("address","?"),
                     f"{d['price']:,.0f}" if d.get("price") else "N/A")
    else:
        log.info("No new deals vs last run.")

    # ── 5. Save snapshot ───────────────────────────────────────────────────────
    _save_snapshot(results)

    # ── 6. Notify ──────────────────────────────────────────────────────────────
    try:
        from notifier import notify_new_deals, notify_run_complete
        if new_deals:
            notify_new_deals(new_deals)
        else:
            notify_run_complete(len(deduped), len(results.get("deals", [])))
    except Exception as exc:
        log.debug("Notification skipped: %s", exc)

    # ── 7. Generate report ─────────────────────────────────────────────────────
    from report import generate
    out = generate(results, report_path, new_addresses=new_addrs)

    # ── 8. Push updated dashboard to GitHub Pages ─────────────────────────────
    _push_report(out)

    elapsed = time.time() - t0
    log.info("Run complete in %.1fs | %d listings | %d deals | report: %s",
             elapsed, len(deduped), len(results.get("deals",[])), out)

    if open_browser:
        try:
            subprocess.run(["cmd", "/c", "start", "", str(out.resolve())], check=False)
        except Exception:
            pass

    return results


# ── Windows Task Scheduler registration ───────────────────────────────────────

def register_task(interval_hours: int = 6) -> None:
    """Register this script as a Windows Task Scheduler job."""
    python_exe = sys.executable
    script = str(HERE / "scheduler.py")
    task_name = "NWARealEstateDealFinder"

    # Create a trigger every interval_hours
    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <TimeTrigger>
      <Repetition>
        <Interval>PT{interval_hours}H</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>{script} --once</Arguments>
      <WorkingDirectory>{HERE}</WorkingDirectory>
    </Exec>
  </Actions>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <WakeToRun>false</WakeToRun>
    <Enabled>true</Enabled>
    <Hidden>true</Hidden>
  </Settings>
</Task>"""

    xml_path = DATA_DIR / "task.xml"
    xml_path.write_text(xml, encoding="utf-16")

    result = subprocess.run(
        ["schtasks", "/create", "/tn", task_name, "/xml", str(xml_path), "/f"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        log.info("Windows Task Scheduler job registered: '%s' (every %dh)", task_name, interval_hours)
        log.info("To delete:  schtasks /delete /tn %s /f", task_name)
    else:
        log.error("Task registration failed: %s", result.stderr)
        log.info("You may need to run this as Administrator.")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(description="NWA Deal Finder — auto-update scheduler")
    p.add_argument("--once", action="store_true", help="Run once then exit")
    p.add_argument("--interval", type=int, default=360, help="Loop interval in minutes (default 360 = 6h)")
    p.add_argument("--register", action="store_true", help="Register Windows Task Scheduler job")
    p.add_argument("--no-browser", action="store_true", help="Don't auto-open report")
    args = p.parse_args()

    if args.register:
        register_task(interval_hours=max(1, args.interval // 60))
        return

    open_browser = not args.no_browser

    if args.once:
        run_once(open_browser=open_browser)
        return

    # ── Continuous loop ────────────────────────────────────────────────────────
    log.info("NWA Deal Finder daemon started (interval: %d min)", args.interval)
    log.info("Press Ctrl+C to stop.")
    while True:
        try:
            run_once(open_browser=open_browser)
            open_browser = False   # only open browser on first run
        except KeyboardInterrupt:
            log.info("Stopped.")
            break
        except Exception as exc:
            log.error("Run failed: %s — will retry next interval.", exc)

        log.info("Sleeping %d min until next run...", args.interval)
        try:
            time.sleep(args.interval * 60)
        except KeyboardInterrupt:
            log.info("Stopped.")
            break


if __name__ == "__main__":
    main()
