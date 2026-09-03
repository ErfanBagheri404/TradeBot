import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from main import randomCandles, analyzeSR, findSignals


def to_df(candles):
    rows = []
    for c in candles:
        rows.append(dict(Date=c[5], Open=c[0], High=c[1], Low=c[2], Close=c[3], Volume=c[4]))
    df = pd.DataFrame(rows)
    df['Date'] = pd.to_datetime(df['Date'])
    return df.set_index('Date')


def aggregate(candles, target_timeframe, base_timeframe=60):
    group_size = target_timeframe // base_timeframe
    if group_size < 2:
        return candles
    out = []
    for g in range(0, len(candles) - len(candles) % group_size, group_size):
        grp = candles[g:g+group_size]
        out.append((grp[0][0], max(c[1] for c in grp), min(c[2] for c in grp),
                    grp[-1][3], sum(c[4] for c in grp), grp[0][5]))
    return out


SPAN = 150
LOOKAHEAD = 800
NUM_ORDERS = 3
BOX_BASE = 50  # base candle span for Fibo horizontal widths


def find_hit_candle(candles, direction, entry, sl, tp, start):
    """Scan candles forward from start. Return which hit first: 'tp' or 'sl'."""
    for j in range(start + 1, min(start + 2000, len(candles))):
        high, low = candles[j][1], candles[j][2]
        if direction == "BUY":
            if low <= sl:
                return "sl"
            if high >= tp:
                return "tp"
        else:  # SELL
            if high >= sl:
                return "sl"
            if low <= tp:
                return "tp"
    return "none"


def find_entry_touch(candles, direction, entry, search_from):
    limit = min(search_from + LOOKAHEAD, len(candles))
    for j in range(search_from, limit):
        if direction == "BUY" and candles[j][1] >= entry - 1e-9:
            return j
        if direction == "SELL" and candles[j][2] <= entry + 1e-9:
            return j
    return None


def pick_3_trades(raw_trades, candles, n=NUM_ORDERS):
    from collections import OrderedDict

    # Group by entry price (same channel = same entry line)
    sigs = OrderedDict()
    for t in raw_trades:
        entry_key = round(t[1], 2)
        sigs.setdefault(entry_key, []).append(t)

    picked = []
    last_end = -SPAN

    for entry_key, orders in sigs.items():
        if len(picked) >= n:
            break

        d = orders[0][0]
        entry = orders[0][1]
        sl = orders[0][2]
        ch_w = orders[0][5]

        # Find up to 3 different start candles for this entry
        # Each start candle must be after the previous trade's zone ends
        signal_indices = sorted(set(o[4] for o in orders))
        fibos = [0.618, 1.618, 2.618]

        for sig_idx in signal_indices:
            if len(picked) >= n:
                break
            s = find_entry_touch(candles, d, entry, sig_idx)
            if s is None:
                continue
            if s < last_end:
                continue
            picked.append((d, entry, sl, fibos, ch_w, s))
            max_box = int(BOX_BASE * fibos[-1])
            last_end = s + max_box

    return picked


def trade_zoom(picked, candles, context=40):
    xl_list = []
    xr_list = []
    prices = []
    for d, entry, sl, fibos, ch_w, s in picked:
        box3 = int(BOX_BASE * fibos[-1])
        xl_list.append(s)
        xr_list.append(s + box3)
        prices.append(entry)
    xl = max(0, min(xl_list) - context)
    xr = min(len(candles), max(xr_list) + context)
    # Tight zoom around entry — SL marker is small
    ymin = min(prices) - (max(prices) - min(prices) + 1) * 0.15
    ymax = max(prices) + (max(prices) - min(prices) + 1) * 0.15
    return xl, xr, ymin, ymax


def plot_trades(ax, picked, candles):
    """
    Each trade: 1 entry line, 3 boxes with different horizontal widths.
    Horizontal width = BOX_BASE × fibo candles.
    Vertical: entry line + thin SL marker below/above.
    """
    for d, entry, sl, fibos, ch_w, s in picked:
        buy = d == "BUY"
        color = '#2196F3' if buy else '#E53935'  # blue = long, red = short
        sl_distance = abs(sl - entry)
        sl_band = sl_distance * 0.15

        # Draw from widest to narrowest
        for i in range(len(fibos) - 1, -1, -1):
            fibo = fibos[i]
            box_width = int(BOX_BASE * fibo)
            shade = 0.08 + i * 0.06

            # Reward zone
            if buy:
                r_lo, r_hi = entry, entry + sl_band
            else:
                r_lo, r_hi = entry - sl_band, entry
            ax.add_patch(plt.Rectangle((s, r_lo), box_width, r_hi - r_lo,
                                       facecolor=color, alpha=shade,
                                       edgecolor=color, linewidth=1.2,
                                       linestyle='-' if i == 2 else '--'))

            # SL zone — same width as THIS order's reward box
            if buy:
                sl_lo, sl_hi = entry - sl_band, entry
            else:
                sl_lo, sl_hi = entry, entry + sl_band
            ax.add_patch(plt.Rectangle((s, sl_lo), box_width, sl_hi - sl_lo,
                                       facecolor='red', alpha=0.25 + i * 0.05,
                                       edgecolor='red', linewidth=1.0,
                                       linestyle='-' if i == 2 else '--'))

        # Entry line — spans widest box
        widest = int(BOX_BASE * fibos[-1])
        ax.plot([s, s + widest], [entry, entry], color=color, linewidth=2, alpha=0.8)
        marker = '^' if buy else 'v'
        ax.plot([s], [entry], marker=marker, color=color, markersize=12)


# ─── Setup ─────────────────────────────────────────────
FIVE_MIN = aggregate(randomCandles, 300)
LOOKBACK = len(FIVE_MIN) // 2
lookbackCandles = FIVE_MIN[:LOOKBACK]
resChannels, supChannels = analyzeSR(lookbackCandles)
print(f"Detected {len(resChannels)} resistance + {len(supChannels)} support channels on first {LOOKBACK} x 5m candles")

style = mpf.make_marketcolors(up='green', down='red', edge='inherit', wick='inherit')
style = mpf.make_mpf_style(marketcolors=style, rc={'axes.grid': True, 'axes.grid.which': 'major'})

longTrades, shortTrades = findSignals(randomCandles, resChannels, supChannels)
print(f"Raw signals: {len(longTrades)} long + {len(shortTrades)} short")


def dedupe(trades):
    seen = set()
    out = []
    for t in trades:
        key = (t[0], round(t[1], 4), t[3], t[4])
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


buy_all  = dedupe([t for t in longTrades if t[0] == "BUY"])
sell_all = dedupe([t for t in shortTrades if t[0] == "SELL"])

buy_picked  = pick_3_trades(buy_all, randomCandles, n=1)
sell_picked = pick_3_trades(sell_all, randomCandles, n=1)

print(f"Selected: {len(buy_picked)} long + {len(sell_picked)} short trades")
order_num = 1
for d, entry, sl, fibos, ch_w, s in buy_picked:
    for fibo in fibos:
        risk = entry - sl
        tp = entry + risk * fibo
        result = find_hit_candle(randomCandles, "BUY", entry, sl, tp, s)
        profit = risk * fibo if result == "tp" else -risk
        status = "WIN" if result == "tp" else "LOSS" if result == "sl" else "NO HIT"
        print(f"  #{order_num} BUY  entry={entry:.4f} sl={sl:.4f} TP(×{fibo})={tp:.4f} → {status} ({'+' if profit>0 else ''}{profit:.4f})")
        order_num += 1
order_num = 1
for d, entry, sl, fibos, ch_w, s in sell_picked:
    for fibo in fibos:
        risk = sl - entry
        tp = entry - risk * fibo
        result = find_hit_candle(randomCandles, "SELL", entry, sl, tp, s)
        profit = risk * fibo if result == "tp" else -risk
        status = "WIN" if result == "tp" else "LOSS" if result == "sl" else "NO HIT"
        print(f"  #{order_num} SELL entry={entry:.4f} sl={sl:.4f} TP(×{fibo})={tp:.4f} → {status} ({'+' if profit>0 else ''}{profit:.4f})")
        order_num += 1

df1 = to_df(lookbackCandles)
fig1, axes1 = mpf.plot(df1, type='candle', volume=True, style=style,
    returnfig=True, warn_too_much_data=10000, figsize=(16, 8),
    title=f'chart: first {LOOKBACK} @ 5m (channels detected here)')
n1 = len(df1); x1 = range(n1)
for hi, lo, _ in resChannels: axes1[0].fill_between(x1, hi, lo, color='red', alpha=0.15)
for hi, lo, _ in supChannels: axes1[0].fill_between(x1, hi, lo, color='green', alpha=0.15)
fig1.savefig('chart.png', dpi=100, pad_inches=0.4); plt.close(fig1)

df2 = to_df(randomCandles)
fig2, axes2 = mpf.plot(df2, type='candle', volume=True, style=style,
    returnfig=True, warn_too_much_data=10000, figsize=(16, 8),
    title=f'chart 2: ALL {len(randomCandles)} @ 1m - all trades')
n2 = len(df2); x2 = range(n2)
for hi, lo, _ in resChannels: axes2[0].fill_between(x2, hi, lo, color='red', alpha=0.15)
for hi, lo, _ in supChannels: axes2[0].fill_between(x2, hi, lo, color='green', alpha=0.15)
plot_trades(axes2[0], buy_picked + sell_picked, randomCandles)
fig2.savefig('chart_2.png', dpi=100, pad_inches=0.4); plt.close(fig2)

if buy_picked:
    df3 = to_df(randomCandles)
    fig3, axes3 = mpf.plot(df3, type='candle', volume=True, style=style,
        returnfig=True, warn_too_much_data=10000, figsize=(16, 8),
        title='chart 3: long trades only (zoomed)')
    plot_trades(axes3[0], buy_picked, randomCandles)
    xl, xr, ymin, ymax = trade_zoom(buy_picked, randomCandles)
    axes3[0].set_xlim(xl, xr); axes3[0].set_ylim(ymin, ymax)
    fig3.savefig('chart_3.png', dpi=100, pad_inches=0.4); plt.close(fig3)

if sell_picked:
    df4 = to_df(randomCandles)
    fig4, axes4 = mpf.plot(df4, type='candle', volume=True, style=style,
        returnfig=True, warn_too_much_data=10000, figsize=(16, 8),
        title='chart 4: short trades only (zoomed)')
    plot_trades(axes4[0], sell_picked, randomCandles)
    xl, xr, ymin, ymax = trade_zoom(sell_picked, randomCandles)
    axes4[0].set_xlim(xl, xr); axes4[0].set_ylim(ymin, ymax)
    fig4.savefig('chart_4.png', dpi=100, pad_inches=0.4); plt.close(fig4)

print("chart.png   : 5m lookback + channels")
print("chart_2.png : 1m all + all trades")
print("chart_3.png : 1m all + long trades (zoomed)")
print("chart_4.png : 1m all + short trades (zoomed)")
