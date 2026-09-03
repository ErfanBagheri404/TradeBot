# How to Calculate and Draw Support/Resistance Channel Width

## What is a Channel Width?

The channel width is the **vertical price difference** between the channel's `high` and `low`:

```
width = high - low
```

Example: Resistance channel with `high=23.6909, low=23.5844`
- Width = 23.6909 - 23.5844 = **0.1066** price units

---

## How to Draw on Paper

### Step 1: Draw All 50 Candles
For each candle in `candle_data`:
- **X-axis** = candle index (0 to 49)
- **Y-axis** = price
- Draw a vertical line from `low` to `high` (the wick)
- Draw a box from `open` to `close` (the body)
  - Green if `close > open` (bullish)
  - Red if `close < open` (bearish)

### Step 2: Draw Channels as Horizontal Bands
Each channel has a `high` and `low` price. Draw it as a **horizontal band** (two parallel lines):

```
Channel high price ──────────────────────
                   │  shaded region     │
Channel low price  ──────────────────────
```

- The **top line** is at the `high` price
- The **bottom line** is at the `low` price
- **Shade the area** between them
- The band spans from the **first** `pivot_candle` index to the **last** `pivot_candle` index

**Example:**
```json
{
  "high": 23.6909,
  "low": 23.5844,
  "width": 0.1066,
  "pivots": 4,
  "pivot_candles": [4, 10, 13, 22]
}
```
→ Draw the band from candle #4 to candle #22, between prices 23.5844 and 23.6909.

### Step 3: Mark Pivot Points
At each candle index in `pivot_candles`, put a **dot** on the channel edge:
- **Resistance channel**: dot at `high` price (the high of that candle touches the channel top)
- **Support channel**: dot at `low` price (the low of that candle touches the channel bottom)

---

## Width Meaning for Orders

The channel width also determines **order box widths** via Fibo multipliers:

| Order | Fibo Multiplier | Box Width (candles) |
|-------|----------------|-------------------|
| Order 1 | 0.618 | 50 × 0.618 = **30** candles |
| Order 2 | 1.618 | 50 × 1.618 = **80** candles |
| Order 3 | 2.618 | 50 × 2.618 = **130** candles |

Each order's box extends horizontally from the `entry_candle` to the right by the box width number of candles.

---

## Risk/Stop Loss

Risk = **1.2% of entry price** (percentage).

- **BUY**: SL = entry × (1 - 0.012) — SL is **below** entry
- **SELL**: SL = entry × (1 + 0.012) — SL is **above** entry

The SL line runs parallel to the entry line at the SL price.

---

## Take Profit (TP)

Each of the 3 orders uses a different Fibo risk:reward multiplier:

| TP | Calculation |
|----|------------|
| TP (×0.618) | entry ± risk × 0.618 |
| TP (×1.618) | entry ± risk × 1.618 |
| TP (×2.618) | entry ± risk × 2.618 |

(Use + for BUY, − for SELL)

---

## Files

| File | Purpose |
|------|---------|
| `main.py` | Candle generation, channel detection, signal finding |
| `test_orders.py` | Standalone test: 1m + 5m independent verification |
| `viewer.py` | Chart visualization with matplotlib |
| `results.json` | Output from `test_orders.py` — all candle data, channels, orders |

## Running

```bash
py test_orders.py    # generates results.json with all data for both timeframes
py viewer.py         # generates chart PNGs (requires viewer.py changes for current logic)
```
