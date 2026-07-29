# Scheduler Setup

The tool runs automatically via Windows Task Scheduler. This document covers the initial setup, how to check status, and how to change the schedule.

---

## How it was set up

During the first full run, `scheduler.py --register` created a Windows Task Scheduler job called `NWARealEstateDealFinder`. The job runs `scheduler.py --once` every six hours, starting from the time of registration.

The task definition is written to `data/task.xml` before being registered with `schtasks /create`. That XML file is gitignored because it contains the full path to your Python executable, which is environment-specific.

---

## Checking the current schedule

```
schtasks /query /tn NWARealEstateDealFinder
```

Output shows the task name, next run time, and status (`Ready` is normal). If status shows `Disabled` or `Running` when it shouldn't be, see the troubleshooting section below.

---

## Manual runs

**Run once and exit:**
```
uv run python scheduler.py --once
```

**Run in a loop (keeps terminal open, runs every 6 hours):**
```
uv run python scheduler.py
```

**Custom interval (every 3 hours):**
```
uv run python scheduler.py --interval 180
```

The `--no-browser` flag suppresses auto-opening the report:
```
uv run python scheduler.py --once --no-browser
```

---

## Changing the schedule

To re-register the task with a different interval (in minutes):
```
uv run python scheduler.py --register --interval 180
```

This overwrites the existing task. If you want to verify it registered correctly:
```
schtasks /query /tn NWARealEstateDealFinder
```

---

## Removing the task

```
schtasks /delete /tn NWARealEstateDealFinder /f
```

This stops the automatic runs but does not delete any files.

---

## Log file

Every run appends to `data/scheduler.log`. The format is:

```
HH:MM:SS [INFO] Starting scrape run at YYYY-MM-DD HH:MM:SS
HH:MM:SS [INFO] craigslist    1 listings
HH:MM:SS [INFO] homepath      60 listings
HH:MM:SS [INFO] NEW DEALS FOUND: 3
HH:MM:SS [INFO] Run complete in 98.3s | 61 listings | 60 deals
```

The log file grows without bound. If it gets large, just delete it — a new one is created on the next run.

---

## Notifications

When new deals appear (addresses present in the current run but not in `data/latest.json`), the notifier fires a Windows toast notification with the top new deal's address, price, and score. A two-tone beep also plays.

Notifications require the Windows notification service to be running. If you're not seeing them, check `Settings → System → Notifications` and make sure notifications are enabled.

---

## Troubleshooting

**Task shows `Running` but hasn't produced output in a long time:**
The scheduler process may have hung during a HomePath session. Kill the task:
```
schtasks /end /tn NWARealEstateDealFinder
```
Then run once manually to verify it completes:
```
uv run python scheduler.py --once
```

**Task shows `Disabled`:**
Enable it:
```
schtasks /change /tn NWARealEstateDealFinder /enable
```

**`uv` not found when the task runs:**
The task references the full path to your Python executable. If you reinstalled Python or uv, re-register the task:
```
uv run python scheduler.py --register
```

**HomePath returns 0 listings:**
HomePath occasionally has downtime or changes their DOM structure. Run the source in isolation to check:
```
uv run python run.py --source homepath
```
If it returns 0, try opening `https://homepath.fanniemae.com` in a browser to confirm the site is up and the search still works as expected.
