"""
NWA Deal Finder – clean single-accent dashboard.
Design principle: one accent (indigo), one signal (emerald for deals),
everything else neutral gray. No rainbow. Sort order communicates priority.
"""
import html
import logging
import urllib.parse
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)


from report_assets import CSS as _CSS, JS as _JS


# ── Helpers ───────────────────────────────────────────────────────────────────
def _e(s) -> str:
    return html.escape(str(s) if s is not None else "")

def _nd(v, fmt=",.0f", pre="", suf="") -> str:
    if v is None or v == 0: return '<span class="no-r" style="font-style:normal">—</span>'
    return f"{pre}{v:{fmt}}{suf}"

def _data(lst: dict) -> str:
    price    = lst.get("price") or 0
    city_raw = (lst.get("city") or "").lower().replace("(rogers/bentonville area)", "").strip()
    return (
        f' data-price="{int(price)}"'
        f' data-beds="{lst.get("beds") or 0}"'
        f' data-baths="{lst.get("baths") or 0}"'
        f' data-sqft="{int(lst.get("sqft") or 0)}"'
        f' data-ppqft="{int(lst.get("price_per_sqft") or 0)}"'
        f' data-score="{lst.get("deal_score") or 0}"'
        f' data-discount="{lst.get("discount_pct") or 0}"'
        f' data-city="{_e(city_raw)}"'
        f' data-zip="{_e(lst.get("zip_code",""))}"'
        f' data-source="{_e(lst.get("source",""))}"'
        f' data-type="{_e(lst.get("listing_type",""))}"'
        f' data-is-new="{"1" if lst.get("_is_new") else "0"}"'
    )

def _hp_url(lst: dict) -> str:
    """Build the most specific HomePath URL available.
    Uses cleaned street address + city + state + ZIP for narrow results.
    Falls back to city-only if no street number detected."""
    import re
    addr_raw = (lst.get("address") or "").strip()
    city  = (lst.get("city") or "NWA").strip()
    state = lst.get("state") or "AR"
    zip_c = lst.get("zip_code") or ""

    # Strip extra spaces before commas (e.g. "Brimwood Street , Centerton" → "Brimwood Street, Centerton")
    addr_clean = re.sub(r"\s+,", ",", addr_raw).strip()

    # Extract street-only portion (before the first comma) if it starts with a house number
    street = addr_clean.split(",")[0].strip() if "," in addr_clean else addr_clean
    has_number = bool(re.match(r"^\d+\s+\w", street))

    if has_number:
        # Build a clean, specific address: "676 Brimwood Street, Centerton, AR 72719"
        parts = [street, city, f"{state} {zip_c}".strip()]
        search = ", ".join(p for p in parts if p)
    else:
        search = f"{city}, {state}, USA"

    return f"https://homepath.fanniemae.com/property-finder?address={urllib.parse.quote(search)}"

def _gm_url(lst: dict) -> str:
    full = ", ".join(filter(None, [
        lst.get("address",""), lst.get("city",""),
        f"{lst.get('state','AR')} {lst.get('zip_code','')}".strip()
    ]))
    return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(full)}"

def _disc(pct: float | None) -> str:
    if pct is None or pct <= 0:
        return '<span class="deal-sig hidden"></span>'
    arrow = "↓" if pct > 0 else ""
    return f'<span class="deal-sig">{arrow} {pct:.1f}% below market</span>'

def _tags(flags: list) -> str:
    # All tags are neutral gray — no rainbow
    return "".join(f'<span class="tag">{_e(f)}</span>' for f in (flags or []))

def _score_tag(score: float) -> str:
    cls = "s-hi" if score >= 60 else "s-mid" if score >= 42 else "s-lo"
    return f'<span class="score-tag {cls}">Score {score:.0f}</span>'


# ── Card ──────────────────────────────────────────────────────────────────────
def _card(lst: dict, is_new: bool = False) -> str:
    score = lst.get("deal_score", 0)
    addr  = _e((lst.get("address") or "Address unknown").strip())
    city  = _e(f"{lst.get('city','')}, {lst.get('state','AR')} {lst.get('zip_code','')}".strip())
    src   = _e((lst.get("source") or "").replace("_", " ").title())
    price = lst.get("price")
    beds  = lst.get("beds"); baths = lst.get("baths")
    sqft  = lst.get("sqft"); ppqft = lst.get("price_per_sqft")

    specs = []
    if beds:  specs.append(f"{beds:.0f} bed")
    if baths: specs.append(f"{baths:.0f} bath")
    if sqft:  specs.append(f"{sqft:,.0f} sqft")
    if ppqft: specs.append(f"${ppqft:.0f}/sqft")
    specs_html = ' <span class="dot">·</span> '.join(specs) if specs else '<span style="color:var(--t4)">No size data</span>'

    price_html = f"${price:,.0f}" if price else "—"
    hp  = _e(_hp_url(lst)); gm = _e(_gm_url(lst))
    new_tag = '<div class="card-new-tag">New This Run</div>' if is_new else ""

    return (
        f'<div class="card"{_data(lst)}>'
        f'{new_tag}'
        f'<div class="card-body">'
        f'<div class="card-head">'
        f'<div><div class="card-addr"><a href="{hp}" target="_blank">{addr}</a></div>'
        f'<div class="card-city">{city} &nbsp;·&nbsp; {src}</div></div>'
        f'{_score_tag(score)}'
        f'</div>'
        f'<div class="card-price">{price_html}</div>'
        f'<div class="card-specs">{specs_html}</div>'
        f'{_disc(lst.get("discount_pct"))}'
        f'<div class="tags">{_tags(lst.get("distress_flags",[]))}</div>'
        f'</div>'
        f'<div class="card-actions">'
        f'<a class="btn-p" href="{hp}" target="_blank">View on HomePath &rarr;</a>'
        f'<a class="btn-s" href="{gm}" target="_blank">Map &nearr;</a>'
        f'</div></div>'
    )


# ── Table row ─────────────────────────────────────────────────────────────────
def _row(lst: dict) -> str:
    score = lst.get("deal_score", 0)
    hp    = _e(_hp_url(lst));  gm = _e(_gm_url(lst))
    addr  = _e(lst.get("address") or "?")
    city  = _e(f"{lst.get('city','')}, {lst.get('state','AR')}")
    beds  = lst.get("beds"); baths = lst.get("baths")
    bb    = (f"{beds:.0f}bd/{baths:.0f}ba" if beds and baths else f"{beds:.0f}bd" if beds else "—")
    pct   = lst.get("discount_pct")
    disc_cell = (f'<span style="color:var(--go);font-weight:600">↓ {pct:.1f}%</span>'
                 if pct and pct > 0 else '<span style="color:var(--t4)">—</span>')
    return (
        f'<tr{_data(lst)}>'
        f'<td><a href="{hp}" target="_blank">{addr}</a><br>'
        f'<small style="color:var(--t3)">{city}</small></td>'
        f'<td class="tp">{_nd(lst.get("price"),",.0f","$")}</td>'
        f'<td>{bb}<br><small style="color:var(--t4)">{_nd(lst.get("sqft"),",.0f",suf=" sqft")}</small></td>'
        f'<td>{_nd(lst.get("price_per_sqft"),".0f","$","/sqft")}</td>'
        f'<td>{disc_cell}</td>'
        f'<td>{_nd(lst.get("dom"),"d",suf="d") if lst.get("dom") else "—"}</td>'
        f'<td><span style="font-weight:700;color:{"#065F46" if score>=60 else "#92400E" if score>=42 else "#991B1B"};background:{"#ECFDF5" if score>=60 else "#FFFBEB" if score>=42 else "#FEF2F2"};padding:.12rem .38rem;border-radius:4px;font-size:.72rem">{score:.0f}</span></td>'
        f'<td><a class="btn-s" style="font-size:.66rem;padding:.12rem .4rem" href="{gm}" target="_blank">Map</a></td>'
        f'</tr>'
    )

def _table(listings: list) -> str:
    if not listings:
        return '<p class="no-r" style="padding:.8rem 0">None.</p>'
    rows = "".join(_row(l) for l in listings)
    return (
        '<div class="tbl-wrap"><table>'
        '<thead><tr><th>Address</th><th>Price</th><th>Beds/Bath</th>'
        '<th>$/sqft</th><th>vs Market</th><th>DOM</th><th>Score</th><th></th></tr></thead>'
        f'<tbody id="tbl-body">{rows}</tbody></table></div>'
    )


# ── Filter panel ──────────────────────────────────────────────────────────────
def _filters() -> str:
    bd = "".join(f'<option value="{n}">{n}+</option>' for n in range(1, 6))
    ba = "".join(f'<option value="{n}">{n}+</option>' for n in range(1, 5))
    return (
        '<div class="filter-bar"><div class="filter-row">'
        '<div class="filter-label">Filters <span class="f-chip" id="f-badge" style="display:none"></span></div>'
        '<div class="fg"><label>City</label><select id="f-city" data-filter><option value="">All Cities</option></select></div>'
        '<div class="fg"><label>ZIP</label><select id="f-zip" data-filter><option value="">All ZIPs</option></select></div>'
        f'<div class="fg"><label>Beds</label><select id="f-beds" data-filter><option value="0">Any</option>{bd}</select></div>'
        f'<div class="fg"><label>Baths</label><select id="f-baths" data-filter><option value="0">Any</option>{ba}</select></div>'
        '<div class="fg"><label>Price ($)</label><div class="frange">'
        '<input id="f-pmin" type="number" placeholder="Min" data-filter min="0" step="25000">'
        '<span>–</span><input id="f-pmax" type="number" placeholder="Max" data-filter min="0" step="25000"></div></div>'
        '<div class="fg"><label>Sqft</label><div class="frange">'
        '<input id="f-smin" type="number" placeholder="Min" data-filter min="0" step="200">'
        '<span>–</span><input id="f-smax" type="number" placeholder="Max" data-filter min="0" step="200"></div></div>'
        '<div class="fg"><label>$/sqft</label><div class="frange">'
        '<input id="f-qmin" type="number" placeholder="Min" data-filter min="0" step="10">'
        '<span>–</span><input id="f-qmax" type="number" placeholder="Max" data-filter min="0" step="10"></div></div>'
        '<div class="fg"><label>Score ≥</label>'
        '<input id="f-score" type="number" value="0" min="0" max="100" data-filter style="width:58px"></div>'
        '<div class="fg"><label>Type</label><select id="f-type" data-filter>'
        '<option value="">All Types</option>'
        '<option value="fanniemae">Fannie Mae REO</option>'
        '<option value="foreclosure">Foreclosure</option>'
        '<option value="fsbo">FSBO / Owner</option>'
        '</select></div>'
        '<input type="hidden" id="f-new-only" value="">'
        '<button class="btn-clear" onclick="clearFilters()">Clear</button>'
        '<div id="filter-count" class="filter-count"></div>'
        '</div></div>'
    )


# ── Resources ─────────────────────────────────────────────────────────────────
_RES = [
    ("HUD Homestore",         "https://www.hudhomestore.gov/Home/Index.aspx",
     "Type 72712/72719/72758 — FHA foreclosures",         "FHA"),
    ("HomePath",              "https://homepath.fanniemae.com/",
     "Fannie Mae REO — search any NWA city",              "REO"),
    ("Auction.com",           "https://www.auction.com/reo/?state=AR&location=Bentonville%2C+AR&radius=25",
     "Foreclosure auctions — 25-mile radius",             "Auction"),
    ("Hubzu",                 "https://www.hubzu.com/search-results/reo?location=Bentonville%2C+AR",
     "Bank-owned online bidding",                         "REO"),
    ("Redfin",                "https://www.redfin.com/AR/Bentonville/",
     "Foreclosure / Short Sale / Price Drop filter",      "MLS"),
    ("Zillow Foreclosures",   "https://www.zillow.com/bentonville-ar/?searchQueryState=%7B%22filterState%22%3A%7B%22fore%22%3A%7B%22value%22%3Atrue%7D%7D%7D",
     "Pre-foreclosure + foreclosure filter",              "MLS"),
    ("Benton County Clerk",   "https://www.bentoncountyar.gov/offices/circuit-clerk/",
     "Active foreclosure filings — lis pendens",          "Public"),
    ("ACT DataScout",         "https://actdatascout.com/RealProperty/",
     "County assessor — tax delinquent / bank-owned",    "County"),
]


# ── Main entry point ──────────────────────────────────────────────────────────
def generate(results: dict, output_path: str = "deals_report.html",
             new_addresses: set | None = None) -> Path:
    ts      = datetime.now().strftime("%b %d, %Y %I:%M %p")
    median  = results.get("area_median_ppqft")
    deals   = results.get("deals", [])
    all_lst = results.get("all_listings", [])
    new_ad  = {a.lower() for a in (new_addresses or set())}

    for lst in all_lst:
        lst["_is_new"] = lst.get("address", "").lower() in new_ad

    med_str      = f"${median:,.0f}/sqft" if median else "N/A"
    below_count  = sum(1 for l in all_lst if (l.get("discount_pct") or 0) > 0)
    new_count    = sum(1 for l in all_lst if l.get("_is_new"))

    def stat(v, lbl, cls="", action=None):
        dq = f' data-q="{action}" onclick="quickFilter(\'{action}\')" ' if action else " "
        sc = f"scard click{' '+cls if cls else ''}" if action else f"scard{' '+cls if cls else ''}"
        title = ' title="Click to filter"' if action else ""
        return (f'<div class="{sc}"{dq}{title}>'
                f'<div class="scard-val{" "+cls if cls else ""}">{_e(str(v))}</div>'
                f'<div class="scard-lbl">{_e(lbl)}</div></div>')

    stats_html = (
        stat(len(all_lst),    "Total Listings") +
        stat(len(deals),      "Deals Flagged",      "accent", "deals") +
        stat(below_count,     "Below Market $/sqft","signal", "below") +
        stat(med_str,         "Zillow Market Median") +
        stat(new_count,       "New This Run",        "signal" if new_count else "", "new")
    )

    cards_html = (
        '<div class="cards" id="cards-cont">' +
        "".join(_card(l, l.get("_is_new", False)) for l in deals) +
        '</div>'
    ) if deals else (
        '<div style="padding:2.5rem;text-align:center;border:1px dashed var(--bdr);'
        'border-radius:var(--rl);background:var(--surface)">'
        '<p style="color:var(--t3)">No automated deals found — check manual research links below.</p>'
        '</div>'
    )

    res_cards = "".join(
        f'<div class="res-card"><div class="res-name"><a href="{_e(u)}" target="_blank">{_e(t)}</a></div>'
        f'<div class="res-desc">{_e(d)}</div><span class="res-type">{_e(r)}</span></div>'
        for t, u, d, r in _RES
    )

    try:
        from config import THRESHOLDS
        ratio = THRESHOLDS.get("underpriced_ratio", 0.82)
    except ImportError:
        ratio = 0.82
    thresh_psf = round((median or 0) * ratio)
    market_note = (
        f"Zillow ZHVI baseline: {med_str} (NWA ZIP average). "
        f"'Below market' flag = ${thresh_psf}/sqft or less ({ratio:.0%} of median)."
    ) if median else "Baseline: hardcoded 2025-Q1 NWA estimate — update NWA_MARKET in config.py."

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NWA Deal Finder</title>
<style>{_CSS}</style>
</head>
<body>
<span id="data-med" style="display:none">{median or 0}</span>
<script>window.NWA_RATIO = {ratio};</script>

<header class="app-header">
  <div class="brand">
    <div class="brand-mark">NWA</div>
    <div>
      <div class="brand-name">Real Estate Deal Finder</div>
      <div class="brand-sub">Centerton · Bentonville · Rogers · Bella Vista, AR</div>
    </div>
  </div>
  <div class="header-right">Updated {_e(ts)}</div>
</header>

<div class="stats-strip">{stats_html}</div>
<p class="hint">Click a stat to quick-filter &nbsp;·&nbsp; Use the filter bar below for custom queries</p>

{_filters()}

<div class="section">
  <div class="sec-head"><h2>Deals &amp; Distressed Sales &nbsp;({len(deals)})</h2></div>
  <p style="color:var(--t3);font-size:.79rem;margin-bottom:1rem;margin-top:-.3rem">
    Fannie Mae REO · Foreclosures · FSBO. Sorted by deal score.
    <strong>View on HomePath</strong> opens that city's listings &nbsp;·&nbsp; <strong>Map</strong> shows the exact address.
  </p>
  {cards_html}
</div>

<hr class="div">

<div class="section">
  <div class="sec-head"><h2>All Scraped Listings &nbsp;({len(all_lst)})</h2></div>
  <p style="color:var(--t3);font-size:.77rem;margin-bottom:.8rem">{_e(market_note)}</p>
  {_table(all_lst)}
</div>

<hr class="div">

<div class="section">
  <div class="sec-head"><h2>Manual Research &nbsp;· Foreclosures &amp; Off-Market</h2></div>
  <p style="color:var(--t3);font-size:.78rem;margin-bottom:.9rem">
    MLS sites block automation — use these links directly for the widest inventory.
  </p>
  <div class="res-grid">{res_cards}</div>
</div>

<footer class="app-footer">
  Sources: HomePath (Fannie Mae REO) &nbsp;·&nbsp; Zillow ZHVI (live market median) &nbsp;·&nbsp;
  Craigslist FSBO &nbsp;·&nbsp; HUD Homestore (manual). &nbsp;·&nbsp;
  Deal Score is a heuristic — verify all listings before making offers.
</footer>

{_JS}
</body>
</html>"""

    out = Path(output_path)
    out.write_text(doc, encoding="utf-8")
    log.info("Report -> %s  (%d deals, %d total)", out.resolve(), len(deals), len(all_lst))
    return out
