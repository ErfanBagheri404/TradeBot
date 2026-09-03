import pandas as pd
import mplfinance as mpf
import random
from datetime import datetime

def generate_candles(n=200):
    candles = []
    base = random.randint(1700000000, 1700014400)
    base -= base % 60
    tf = random.choice([60, 180, 300, 900, 1800])
    price = random.uniform(20, 25)
    offset = random.uniform(0, 0.05)
    for i in range(n):
        o = price
        h = random.uniform(o, o + offset * o)
        l = random.uniform(o - offset * o, o)
        c = random.uniform(l, h)
        v = random.randint(1000, 3000)
        t = datetime.fromtimestamp(base + i * tf)
        candles.append((o, h, l, c, v, t))
        price = c
    return candles

candles = generate_candles(200)
rows = [{'Open':c[0],'High':c[1],'Low':c[2],'Close':c[3],'Volume':c[4],'Date':c[5]} for c in candles]
df = pd.DataFrame(rows).set_index('Date')
N = len(df)

def find_pivots(candles, k=3):
    highs, lows = {}, {}
    for i in range(k, len(candles)-k):
        if candles[i][1] > max(candles[i-j][1] for j in range(1, k+1)) and \
           candles[i][1] > max(candles[i+j][1] for j in range(1, k+1)):
            highs[i] = candles[i][1]
        if candles[i][2] < min(candles[i-j][2] for j in range(1, k+1)) and \
           candles[i][2] < min(candles[i+j][2] for j in range(1, k+1)):
            lows[i] = candles[i][2]
    return highs, lows

def make_scatter(pos_dict, val_dict, marker, color):
    s = pd.Series([float('nan')]*N, index=df.index, dtype='float64')
    for i, v in pos_dict.items():
        s.iloc[i] = v
    return mpf.make_addplot(s, type='scatter', markersize=80, marker=marker, color=color)

ph, pl = find_pivots(candles, k=3)
mc = mpf.make_marketcolors(up='lime', down='red', wick='inherit', edge='inherit')
style = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=True)

ap1 = make_scatter(ph, ph, 'v', 'red')
ap2 = make_scatter(pl, pl, '^', 'lime')
mpf.plot(df, type='candle', volume=True, style=style, addplot=[ap1, ap2],
    figsize=(18, 8),
    title='CHART 1 — Pivots (k=3): red H=swing high, lime L=swing low',
    savefig='chart_1_pivots.png')
print("CHART 1 done")

def find_channels(candles, k=3):
    highs, lows = find_pivots(candles, k)
    all_pivots = list(highs.values()) + list(lows.values())
    if not all_pivots:
        return []
    cwidth = (max(c[1] for c in candles) - min(c[2] for c in candles)) * 0.05
    used = set()
    channels = []
    for idx, p in enumerate(all_pivots):
        if idx in used:
            continue
        lo, hi, count = p, p, 0
        for j, q in enumerate(all_pivots):
            if j in used:
                continue
            wdth = q - hi if q > hi else lo - q if q < lo else 0
            if wdth <= cwidth:
                lo, hi = min(lo, q), max(hi, q)
                count += 1
                used.add(j)
        if count >= 2:
            channels.append((hi, lo, count))
    channels.sort(key=lambda x: x[2], reverse=True)
    return channels[:6]

channels = find_channels(candles, k=3)
hlines2 = dict(hlines=[], colors=[], linestyle='--', linewidths=1.5)
for hi, lo, _ in channels:
    hlines2['hlines'] += [hi, lo]
    hlines2['colors'] += ['red', 'lime']

mpf.plot(df, type='candle', volume=True, style=style, hlines=hlines2,
    figsize=(18, 8),
    title=f'CHART 2 — {len(channels)} Channel Zones',
    savefig='chart_2_channels.png')
print(f"CHART 2 done — {len(channels)} channels")

def count_touches(candles, hi, lo):
    return sum(1 for c in candles if (lo <= c[1] <= hi) or (lo <= c[2] <= hi))

hlines3 = dict(hlines=[], colors=[], linestyle='--', linewidths=[])
for hi, lo, pc in channels:
    touches = count_touches(candles, hi, lo)
    strength = pc * 20 + touches
    lw = max(1.0, strength / 25)
    hlines3['hlines'] += [hi, lo]
    hlines3['colors'] += ['red', 'lime']
    hlines3['linewidths'] += [lw, lw]
    print(f"  {lo:.2f}-{hi:.2f}  pivots={pc}  touches={touches}  strength={strength}")

mpf.plot(df, type='candle', volume=True, style=style, hlines=hlines3,
    figsize=(18, 8), title='CHART 3 — Strength Scored (thicker=stronger)',
    savefig='chart_3_strength.png')
print("CHART 3 done")

up_idx, dn_idx, up_p, dn_p = [], [], [], []
for i in range(1, len(candles)):
    curr, prev = candles[i][3], candles[i-1][3]
    in_ch = any(lo <= curr <= hi for hi, lo, _ in channels)
    if in_ch:
        continue
    for hi, lo, _ in channels:
        if prev <= hi and curr > hi:
            up_idx.append(i); up_p.append(candles[i][2])
        if prev >= lo and curr < lo:
            dn_idx.append(i); dn_p.append(candles[i][1])

addplots = []
if up_idx:
    s = pd.Series([float('nan')]*N, index=df.index, dtype='float64')
    for idx, price in zip(up_idx, up_p):
        s.iloc[idx] = price
    addplots.append(mpf.make_addplot(s, type='scatter', markersize=120, marker='^', color='lime'))
if dn_idx:
    s = pd.Series([float('nan')]*N, index=df.index, dtype='float64')
    for idx, price in zip(dn_idx, dn_p):
        s.iloc[idx] = price
    addplots.append(mpf.make_addplot(s, type='scatter', markersize=120, marker='v', color='red'))

mpf.plot(df, type='candle', volume=True, style=style, hlines=hlines3,
    addplot=addplots, figsize=(18, 8),
    title=f'CHART 4 — Breakouts ({len(up_idx)} resistance, {len(dn_idx)} support broken)',
    savefig='chart_4_breakouts.png')
print(f"CHART 4 done — {len(up_idx)} resistance breaks, {len(dn_idx)} support breaks")
