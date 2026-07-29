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

# ── Design tokens ─────────────────────────────────────────────────────────────
_CSS = """
:root {
  /* Surfaces */
  --bg:      #F9FAFB;
  --surface: #FFFFFF;
  --surface2:#F3F4F6;

  /* Borders */
  --bdr:  #E5E7EB;
  --bdr2: #D1D5DB;

  /* Text scale */
  --t1: #111827;   /* primary */
  --t2: #374151;   /* secondary */
  --t3: #6B7280;   /* muted */
  --t4: #9CA3AF;   /* faint */

  /* One accent — indigo */
  --ink:    #4F46E5;
  --ink-h:  #4338CA;
  --ink-bg: #EEF2FF;
  --ink-bd: #C7D2FE;

  /* One signal — emerald (below-market deals ONLY) */
  --go:    #059669;
  --go-bg: #ECFDF5;
  --go-bd: #A7F3D0;

  /* Shadows */
  --s1: 0 1px 2px rgba(0,0,0,.05);
  --s2: 0 1px 3px rgba(0,0,0,.1), 0 1px 2px rgba(0,0,0,.06);
  --s3: 0 4px 6px rgba(0,0,0,.07), 0 2px 4px rgba(0,0,0,.06);
  --s4: 0 10px 15px rgba(0,0,0,.1), 0 4px 6px rgba(0,0,0,.05);

  --r:  8px;
  --rl: 12px;
  --rs: 5px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, system-ui, sans-serif;
  background: var(--bg); color: var(--t1); font-size: 14px; line-height: 1.5;
}
a { color: var(--ink); text-decoration: none; }
a:hover { color: var(--ink-h); text-decoration: underline; }

/* ── App header ─────────────────────────────────────────────────────────── */
.app-header {
  background: var(--surface); border-bottom: 1px solid var(--bdr);
  padding: .875rem 2rem; display: flex; align-items: center;
  justify-content: space-between; position: sticky; top: 0;
  z-index: 300; box-shadow: var(--s1);
}
.brand { display: flex; align-items: center; gap: .625rem; }
.brand-mark {
  width: 32px; height: 32px; background: var(--ink); border-radius: 7px;
  display: grid; place-items: center; color: #fff;
  font-size: .7rem; font-weight: 800; letter-spacing: .04em; flex-shrink: 0;
}
.brand-name  { font-size: .95rem; font-weight: 700; color: var(--t1); letter-spacing: -.01em; }
.brand-sub   { font-size: .71rem; color: var(--t3); }
.header-right{ font-size: .73rem; color: var(--t4); }

/* ── Stats strip ─────────────────────────────────────────────────────────── */
.stats-strip {
  background: var(--surface); border-bottom: 1px solid var(--bdr);
  padding: .875rem 2rem; display: flex; flex-wrap: wrap; gap: .5rem;
}
.scard {
  display: flex; flex-direction: column;
  padding: .6rem .875rem; border: 1px solid var(--bdr);
  border-radius: var(--r); min-width: 105px;
  background: var(--surface); transition: all .15s; cursor: default;
}
.scard.click { cursor: pointer; }
.scard.click:hover {
  border-color: var(--ink); background: var(--ink-bg);
  box-shadow: 0 0 0 3px rgba(79,70,229,.12); transform: translateY(-1px);
}
.scard.active-f {
  border-color: var(--ink) !important; background: var(--ink-bg) !important;
  box-shadow: 0 0 0 3px rgba(79,70,229,.15) !important;
}
.scard-val { font-size: 1.3rem; font-weight: 700; color: var(--t1); line-height: 1.2; }
.scard-val.accent { color: var(--ink); }
.scard-val.signal { color: var(--go); }
.scard-lbl {
  font-size: .64rem; color: var(--t3); margin-top: .15rem;
  text-transform: uppercase; letter-spacing: .06em; font-weight: 500;
}
.hint { font-size: .68rem; color: var(--t4); padding: .2rem 2rem .3rem;
  background: var(--surface); border-bottom: 1px solid var(--bdr); }

/* ── Filter bar ──────────────────────────────────────────────────────────── */
.filter-bar {
  background: var(--surface); border-bottom: 1px solid var(--bdr);
  padding: .55rem 2rem; position: sticky; top: 57px;
  z-index: 200; box-shadow: var(--s1);
}
.filter-row { display: flex; flex-wrap: wrap; align-items: flex-end; gap: .5rem; }
.filter-label {
  font-size: .65rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .09em; color: var(--ink); align-self: flex-end;
  padding-bottom: .38rem; display: flex; align-items: center; gap: .3rem;
}
.f-chip {
  display: inline-block; background: var(--ink); color: #fff;
  font-size: .58rem; font-weight: 700; padding: .1rem .35rem; border-radius: 999px;
}
.fg { display: flex; flex-direction: column; gap: .15rem; }
.fg label {
  font-size: .6rem; font-weight: 600; color: var(--t4);
  text-transform: uppercase; letter-spacing: .05em;
}
.fg select, .fg input[type=number] {
  background: var(--bg); border: 1px solid var(--bdr2); color: var(--t1);
  border-radius: var(--rs); padding: .27rem .45rem; font-size: .79rem;
  outline: none; transition: border-color .15s, box-shadow .15s; font-family: inherit;
}
.fg select:focus, .fg input[type=number]:focus {
  border-color: var(--ink); box-shadow: 0 0 0 2px var(--ink-bg);
}
.frange { display: flex; align-items: center; gap: .25rem; }
.frange span { color: var(--t4); font-size: .78rem; }
.frange input { width: 70px; }
.btn-clear {
  align-self: flex-end; padding: .28rem .7rem; background: transparent;
  border: 1px solid var(--bdr2); color: var(--t3); border-radius: var(--rs);
  cursor: pointer; font-size: .76rem; font-family: inherit; transition: all .15s;
}
.btn-clear:hover { border-color: var(--t2); color: var(--t2); }
.filter-count { font-size: .72rem; color: var(--t4); align-self: flex-end;
  padding-bottom: .35rem; white-space: nowrap; }

/* ── Section ─────────────────────────────────────────────────────────────── */
.section { padding: 1.5rem 2rem; }
.sec-head {
  display: flex; align-items: center; gap: .75rem; margin-bottom: 1rem;
}
.sec-head h2 {
  font-size: .77rem; font-weight: 600; color: var(--t3);
  text-transform: uppercase; letter-spacing: .07em; white-space: nowrap;
}
.sec-head::after { content: ''; flex: 1; height: 1px; background: var(--bdr); }
hr.div { border: none; border-top: 1px solid var(--bdr); margin: 0 2rem; }

/* ── Deal cards ──────────────────────────────────────────────────────────── */
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1rem; }

.card {
  background: var(--surface); border: 1px solid var(--bdr);
  border-radius: var(--rl); box-shadow: var(--s1);
  display: flex; flex-direction: column; overflow: hidden;
  transition: box-shadow .2s, border-color .2s, transform .2s;
}
.card:hover { box-shadow: var(--s4); border-color: var(--ink); transform: translateY(-2px); }

.card-new-tag {
  background: var(--go); color: #fff; font-size: .61rem; font-weight: 700;
  text-align: center; padding: .2rem; letter-spacing: .1em; text-transform: uppercase;
}
.card-body  { padding: 1.1rem; flex: 1; display: flex; flex-direction: column; gap: .6rem; }
.card-head  { display: flex; justify-content: space-between; align-items: flex-start; gap: .5rem; }
.card-addr  { font-size: .87rem; font-weight: 600; color: var(--t1); line-height: 1.3; flex: 1; }
.card-addr a { color: var(--t1); }
.card-addr a:hover { color: var(--ink); text-decoration: underline; }
.card-city  { font-size: .71rem; color: var(--t3); margin-top: .1rem; }
.score-tag  {
  flex-shrink: 0; font-size: .67rem; font-weight: 600;
  padding: .18rem .4rem; border-radius: 4px;
  background: var(--surface2); color: var(--t3);
  border: 1px solid var(--bdr); white-space: nowrap;
}
/* score tiers: green ≥ 60, yellow ≥ 42, red < 42 */
.score-tag.s-hi  { background:#ECFDF5; color:#065F46; border-color:#A7F3D0; }
.score-tag.s-mid { background:#FFFBEB; color:#92400E; border-color:#FDE68A; }
.score-tag.s-lo  { background:#FEF2F2; color:#991B1B; border-color:#FECACA; }
.card-price { font-size: 1.5rem; font-weight: 800; color: var(--t1); letter-spacing: -.03em; line-height: 1; }
.card-specs { font-size: .76rem; color: var(--t3); display: flex; flex-wrap: wrap; gap: 0 .4rem; }
.card-specs .dot { color: var(--t4); }

/* deal signal — shown only when below market */
.deal-sig {
  display: inline-flex; align-items: center; gap: .2rem;
  font-size: .73rem; font-weight: 600; color: var(--go);
  background: var(--go-bg); border: 1px solid var(--go-bd);
  padding: .18rem .5rem; border-radius: 999px; width: fit-content;
}
.deal-sig.hidden { display: none; }

/* tags — all neutral, no rainbow */
.tags { display: flex; flex-wrap: wrap; gap: .25rem; }
.tag {
  font-size: .63rem; font-weight: 500; padding: .12rem .38rem;
  border-radius: 4px; background: var(--surface2);
  color: var(--t3); border: 1px solid var(--bdr);
}

.card-actions {
  display: flex; gap: .5rem; padding: .75rem 1.1rem;
  border-top: 1px solid var(--bdr); background: var(--surface2);
}
.btn-p {
  flex: 1; text-align: center; padding: .4rem .6rem;
  background: var(--ink); color: #fff; border-radius: var(--rs);
  font-size: .77rem; font-weight: 600; transition: background .15s;
  text-decoration: none !important; font-family: inherit;
}
.btn-p:hover { background: var(--ink-h); color: #fff; text-decoration: none !important; }
.btn-s {
  padding: .4rem .65rem; background: var(--surface); color: var(--t3);
  border: 1px solid var(--bdr2); border-radius: var(--rs); font-size: .77rem;
  font-weight: 500; transition: all .15s; text-decoration: none !important; white-space: nowrap;
}
.btn-s:hover { color: var(--t1); border-color: var(--t2); background: var(--surface2); text-decoration: none !important; }

/* ── Table ───────────────────────────────────────────────────────────────── */
.tbl-wrap { border-radius: var(--r); border: 1px solid var(--bdr); overflow-x: auto; box-shadow: var(--s1); }
table { width: 100%; border-collapse: collapse; font-size: .79rem; }
thead th {
  background: var(--surface2); padding: .5rem .875rem; color: var(--t3);
  font-weight: 600; text-align: left; white-space: nowrap;
  border-bottom: 1px solid var(--bdr);
}
tbody td { padding: .48rem .875rem; border-bottom: 1px solid var(--bdr); vertical-align: middle; }
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover td { background: #F9FAFB; }
.tp { font-weight: 700; }.ts { font-weight: 700; color: var(--ink); }
.no-r { color: var(--t3); font-style: italic; padding: 1rem 0; }

/* ── Resource grid ───────────────────────────────────────────────────────── */
.res-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: .75rem; }
.res-card {
  background: var(--surface); border: 1px solid var(--bdr); border-radius: var(--r);
  padding: .875rem 1rem; transition: box-shadow .15s, border-color .15s;
}
.res-card:hover { box-shadow: var(--s3); border-color: var(--bdr2); }
.res-name  { font-size: .85rem; font-weight: 600; }
.res-desc  { font-size: .73rem; color: var(--t3); margin-top: .2rem; }
.res-type  {
  display: inline-block; font-size: .65rem; font-weight: 500; margin-top: .4rem;
  background: var(--ink-bg); color: var(--ink); padding: .1rem .38rem; border-radius: 3px;
}

/* ── Footer ──────────────────────────────────────────────────────────────── */
.app-footer {
  padding: 1rem 2rem; color: var(--t4); font-size: .71rem;
  border-top: 1px solid var(--bdr); background: var(--surface);
}
"""

# ── JavaScript (unchanged logic, only class names updated) ────────────────────
_JS = """<script>
(function(){
  var MED = parseFloat((document.getElementById('data-med')||{}).textContent||'0');
  function $id(id){return document.getElementById(id);}
  function val(id){return ($id(id)||{}).value||'';}
  function num(id){return parseFloat(val(id))||0;}

  function readF(){
    return{city:val('f-city').toLowerCase(),beds:num('f-beds'),baths:num('f-baths'),
      pmin:num('f-pmin'),pmax:num('f-pmax')||Infinity,
      smin:num('f-smin'),smax:num('f-smax')||Infinity,
      qmin:num('f-qmin'),qmax:num('f-qmax')||Infinity,
      score:num('f-score'),type:val('f-type').toLowerCase(),zip:val('f-zip').trim(),
      newOnly:!!($id('f-new-only')&&$id('f-new-only').value==='1'),};
  }

  function ok(el,f){
    var d=el.dataset, p=function(n){return parseFloat(d[n])||0;};
    if(f.city  && !(d.city||'').includes(f.city)) return false;
    if(f.zip   && d.zip!==f.zip) return false;
    if(f.beds  && p('beds') <f.beds)  return false;
    if(f.baths && p('baths')<f.baths) return false;
    if(p('price')<f.pmin || p('price')>f.pmax) return false;
    if(f.smin && (!p('sqft') || p('sqft')<f.smin)) return false;
    if(p('sqft')  && p('sqft') >f.smax) return false;
    if(f.qmin && (!p('ppqft')|| p('ppqft')<f.qmin)) return false;
    if(p('ppqft') && p('ppqft')>f.qmax) return false;
    if(p('score')<f.score) return false;
    if(f.type && f.type!=='all' && !(d.type||'').includes(f.type)) return false;
    if(f.newOnly && d.isNew!=='1') return false;
    return true;
  }

  window.applyFilters = function(){
    var f=readF(), shown=0, total=0;
    document.querySelectorAll('[data-price]').forEach(function(el){
      var m=ok(el,f); el.style.display=m?'':'none'; if(m)shown++; total++;
    });
    var c=$id('filter-count');
    if(c) c.textContent = shown===total ? total+' listing'+(total===1?'':'s') : shown+' of '+total+' shown';
    var active = [f.city,f.beds,f.baths,f.pmin,(f.pmax<Infinity?1:0),
      f.smin,(f.smax<Infinity?1:0),f.qmin,(f.qmax<Infinity?1:0),
      f.score,(f.type&&f.type!=='all'?1:0),f.zip,(f.newOnly?1:0)].filter(Boolean).length;
    var b=$id('f-badge'); if(b){b.textContent=active||''; b.style.display=active?'inline':'none';}
    ['cards-cont','tbl-body'].forEach(function(cid){
      var ct=$id(cid); if(!ct) return;
      var hv=Array.from(ct.querySelectorAll('[data-price]')).some(function(e){return e.style.display!=='none';});
      var ph=ct.querySelector('.no-r');
      if(!hv){
        if(!ph){ph=document.createElement('p');ph.className='no-r';ph.textContent='No listings match — adjust your filters.';ct.appendChild(ph);}
        ph.style.display='';
      } else if(ph) ph.style.display='none';
    });
  };

  window.clearFilters = function(){
    ['f-city','f-type','f-zip','f-new-only'].forEach(function(id){var e=$id(id);if(e)e.value='';});
    ['f-beds','f-baths','f-score'].forEach(function(id){var e=$id(id);if(e)e.value='0';});
    ['f-pmin','f-pmax','f-smin','f-smax','f-qmin','f-qmax'].forEach(function(id){var e=$id(id);if(e)e.value='';});
    document.querySelectorAll('.scard.active-f').forEach(function(e){e.classList.remove('active-f');});
    applyFilters();
  };

  window.quickFilter = function(action){
    /* Toggle: clicking an already-active stat un-filters it */
    var btn = document.querySelector('[data-q="'+action+'"]');
    var wasActive = btn && btn.classList.contains('active-f');
    clearFilters(); /* always resets all filters + removes all active-f */
    if (!wasActive) {
      if(action==='deals')  $id('f-score').value='20';
      else if(action==='below'){ $id('f-qmax').value=Math.round(MED*0.82||165); }
      else if(action==='new'){ var n=$id('f-new-only'); if(n)n.value='1'; }
      var b2=document.querySelector('[data-q="'+action+'"]'); if(b2)b2.classList.add('active-f');
    }
    /* if wasActive, clearFilters() already removed the filter — just fall through */
    applyFilters();
  };

  /* populate city + zip dropdowns */
  var cities=new Set(), zips=new Set();
  document.querySelectorAll('[data-price]').forEach(function(el){
    var c=el.dataset.city, z=el.dataset.zip;
    if(c&&c.length>1&&!c.includes('nwa'))cities.add(c);
    if(z&&z.length===5)zips.add(z);
  });
  var cs=$id('f-city');
  if(cs)[...cities].sort().forEach(function(c){
    var o=document.createElement('option');o.value=c;
    o.textContent=c.charAt(0).toUpperCase()+c.slice(1); cs.appendChild(o);
  });
  var zs=$id('f-zip');
  if(zs)[...zips].sort().forEach(function(z){
    var o=document.createElement('option');o.value=z;o.textContent=z; zs.appendChild(o);
  });

  document.querySelectorAll('[data-filter]').forEach(function(el){
    el.addEventListener('input', applyFilters); el.addEventListener('change', applyFilters);
  });
  applyFilters();
})();
</script>"""

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

    thresh_psf = round((median or 0) * 0.82)
    market_note = (
        f"Zillow ZHVI baseline: {med_str} (NWA ZIP average). "
        f"'Below market' flag = ${thresh_psf}/sqft or less (82% of median)."
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
  Auto-refreshes every 6h via Windows Task Scheduler. &nbsp;·&nbsp;
  Deal Score is a heuristic — verify all listings before making offers.
</footer>

{_JS}
</body>
</html>"""

    out = Path(output_path)
    out.write_text(doc, encoding="utf-8")
    log.info("Report → %s  (%d deals, %d total)", out.resolve(), len(deals), len(all_lst))
    return out


try:
    from config import THRESHOLDS
    AREA_MED_THRESH = THRESHOLDS.get("underpriced_ratio", 0.82)
except ImportError:
    AREA_MED_THRESH = 0.82
