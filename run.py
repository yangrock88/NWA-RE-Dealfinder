"""
Quick-run entry point — delegates to scheduler.run_once().

Usage:
    uv run python run.py                   # run once, open report
    uv run python run.py --no-browser      # run once, don't open browser
    uv run python run.py --source homepath # single-source debug run

For auto-scheduling:
    uv run python scheduler.py             # runs every 6h in a loop
    uv run python scheduler.py --once      # one run + exit
    uv run python scheduler.py --register  # add to Windows Task Scheduler
"""
import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("run")


def _single_source(name: str) -> None:
    """Debug: run only one source and print results."""
    import importlib
    mod = importlib.import_module(f"sources.{name}")
    results = mod.fetch_listings()
    for r in results:
        addr = r.get("address", "?")
        price = r.get("price")
        sqft = r.get("sqft")
        ppqft = r.get("price_per_sqft")
        print(f"  {addr:<60} | ${price:,.0f}" if price else f"  {addr}")
        if sqft:
            print(f"    {r.get('beds','-')}bd / {r.get('baths','-')}ba / {sqft:,.0f}sqft / ${ppqft:.0f}/sqft" if ppqft else "")
    print(f"\n{len(results)} listings from {name}")


def main() -> None:
    p = argparse.ArgumentParser(description="NWA Deal Finder — one-shot run")
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--source", choices=["craigslist","homepath","hud","auction","zillow"], default=None,
                   help="Debug: run only one source")
    p.add_argument("--output", default="deals_report.html")
    args = p.parse_args()

    if args.source:
        _single_source(args.source)
        return

    from scheduler import run_once
    run_once(report_path=args.output, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
