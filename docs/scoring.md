# Deal Scoring

The deal score is a single number that summarizes how interesting a listing is as a potential buying opportunity. It is purely heuristic — a starting point for research, not a financial recommendation.

---

## Score components

The score adds up contributions from four sources:

**1. Price discount vs. area median (0–45 points)**

If the listing has a valid $/sqft figure and the area median is known, the discount percentage is computed:

```
discount_pct = (1 - listing_ppqft / area_median_ppqft) * 100
```

A positive discount means the listing is priced below median. The point contribution is:

```
discount_points = min(discount_pct * 1.5, 45)
```

This caps at 45 points regardless of how far below median the listing is. A 30% discount yields 45 points; a 10% discount yields 15.

**2. Listing type (25 points for distressed types)**

Any listing classified as `fanniemae_reo`, `hud_foreclosure`, `foreclosure`, `foreclosure_auction`, or `short_sale` receives 25 points. HUD foreclosures get an additional 5 points (for 30 total) on the assumption that government-appraised properties tend to move quickly and may leave less room for negotiation.

**3. Days on market (0–15 points)**

When DOM is available: `min(dom / 10, 15)`. A listing sitting for 150 days earns the full 15 points. This component is null for HomePath and Craigslist.

**4. Distress flag count (2 points each)**

Each unique distress keyword found in the listing text adds 2 points. The keyword list is in `config.DISTRESS_KEYWORDS`. A HomePath REO listing typically gets 5–6 keyword hits ("foreclosure", "reo", "bank-owned", "fannie mae", "as-is"), contributing 10–12 points.

---

## Score tiers and card colors

| Score range | Color | Typical profile |
|---|---|---|
| 60 and above | Green | Fannie Mae REO priced 15%+ below $/sqft median |
| 42–59 | Yellow | REO or foreclosure at or near market rate |
| Below 42 | Red | Distressed sale type but priced above market |

The majority of HomePath listings in a hot market like NWA land in the yellow and red tiers because prices are set at or above current appraised value. Green listings are genuinely unusual and worth looking at first.

---

## What the score does not capture

The score cannot account for:
- Property condition (HomePath is as-is; a high-score property could need $80,000 in repairs)
- HOA fees, which can materially change the effective cost
- Lot size or school district quality
- Flood zone, zoning restrictions, or easements
- Competition — how many other buyers are already bidding

Always pull the full property disclosure and get an inspection before drawing conclusions from the score.

---

## Adjusting score behavior

The discount threshold and DOM cutoff are set in `config.py`:

```python
THRESHOLDS = {
    "underpriced_ratio": 0.82,  # flag if $/sqft < 82% of median
    "dom_high": 45,             # flag high-DOM listings after this many days
    "min_price_per_sqft": 30,   # filter out bad data below this value
    "max_price": 750_000,       # skip listings above this price
    "min_price": 40_000,        # skip placeholder listings below this
}
```

Lowering `underpriced_ratio` to 0.70 would only flag listings 30% below median instead of 18%. Raising it to 0.95 would flag anything 5% below median, which in a volatile market generates a lot of noise.
