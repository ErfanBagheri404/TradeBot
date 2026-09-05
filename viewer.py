import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from main import randomCandles, resChannels, supChannels, trades


def to_df(candles):
    rows = []
    for c in candles:
        rows.append(dict(Date=c[5], Open=c[0], High=c[1], Low=c[2], Close=c[3], Volume=c[4]))
    df = pd.DataFrame(rows)
    df['Date'] = pd.to_datetime(df['Date'])
    return df.set_index('Date')


BOX_BASE = 50  # base candle span for Fibo horizontal widths


def trade_zoom(picked, candles, context=40):
    xl_list = []
    xr_list = []
    prices = []
    for t in picked:
        box3 = int(BOX_BASE * 2.618)
        xl_list.append(t["entry_candle"])
        xr_list.append(t["entry_candle"] + box3)
        prices.append(t["entry"])
        prices.append(t["sl"])
    xl = max(0, min(xl_list) - context)
    xr = min(len(candles), max(xr_list) + context)
    ymin = min(prices) - (max(prices) - min(prices) + 1) * 0.15
    ymax = max(prices) + (max(prices) - min(prices) + 1) * 0.15
    return xl, xr, ymin, ymax


def plot_trades(ax, trades_list):
    """
    Each trade: 1 entry line, 3 boxes (TP1/TP2/TP3) with different horizontal widths.
    Horizontal width = BOX_BASE x fibo candles.
    Exit markers: x = closed part (TP hit), o = stopped part (SL hit).
    """
    for t in trades_list:
        d = t["direction"]
        entry = t["entry"]
        sl = t["sl"]
        s = t["entry_candle"]
        buy = d == "BUY"
        color = '#2196F3' if buy else '#E53935'  # blue = long, red = short
        sl_distance = abs(sl - entry)
        sl_band = sl_distance * 0.15

        # Draw from widest to narrowest
        for i in range(len(t["tps"]) - 1, -1, -1):
            tp = t["tps"][i]
            fibo = tp["fibo"]
            box_width = int(BOX_BASE * fibo)
            shade = 0.08 + i * 0.06

            # Reward zone (thin band on profit side of entry)
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
                                       linestyle=':'))
            # TP line at this part's TP price
            ax.hlines(tp["price"], s, s + box_width, color=color, alpha=0.8, linewidth=1.0)

        # Entry line spans the widest box
        ax.hlines(entry, s, s + int(BOX_BASE * 2.618), color=color, linewidth=1.8)
        # Entry marker
        marker = '^' if buy else 'v'
        ax.plot([s], [entry], marker=marker, color=color, markersize=12)

        # Exit markers per part
        for p in t["parts"]:
            if p["hit"] == "NO HIT":
                continue
            xc = p["exit_candle"]
            yc = p["exit"]
            if p["hit"].startswith("TP"):
                ax.plot([xc], [yc], marker='x', color=color,
                        markersize=9, markeredgewidth=2)
            else:  # SL hit
                ax.plot([xc], [yc], marker='o', color='red',
                        markersize=7, markeredgewidth=1.5)


# ─── Setup ─────────────────────────────────────────────
style = mpf.make_marketcolors(up='green', down='red', edge='inherit', wick='inherit')
style = mpf.make_mpf_style(marketcolors=style, rc={'axes.grid': True, 'axes.grid.which': 'major'})

print(f"Trades to plot: {len(trades)}")
for t in trades:
    parts_str = " | ".join(f"P{p['tp_level']}: {p['hit']} @{p['exit_candle']}" for p in t["parts"])
    print(f"  #{t['id']} {t['direction']} entry={t['entry']:.4f} -> {parts_str}")

buy_trades  = [t for t in trades if t["direction"] == "BUY"]
sell_trades = [t for t in trades if t["direction"] == "SELL"]

df2 = to_df(randomCandles)
fig2, axes2 = mpf.plot(df2, type='candle', volume=True, style=style,
    returnfig=True, warn_too_much_data=10000, figsize=(16, 8),
    title=f'chart 2: ALL {len(randomCandles)} @ 1m - all trades')
n2 = len(df2); x2 = range(n2)
for hi, lo, cnt in resChannels: axes2[0].fill_between(x2, hi, lo, color='red', alpha=0.15)
for hi, lo, cnt in supChannels: axes2[0].fill_between(x2, hi, lo, color='green', alpha=0.15)
plot_trades(axes2[0], buy_trades + sell_trades)
fig2.savefig('chart_2.png', dpi=100, pad_inches=0.4); plt.close(fig2)

if buy_trades:
    df3 = to_df(randomCandles)
    fig3, axes3 = mpf.plot(df3, type='candle', volume=True, style=style,
        returnfig=True, warn_too_much_data=10000, figsize=(16, 8),
        title='chart 3: long trades only (zoomed)')
    for hi, lo, cnt in resChannels: axes3[0].fill_between(range(len(df3)), hi, lo, color='red', alpha=0.15)
    for hi, lo, cnt in supChannels: axes3[0].fill_between(range(len(df3)), hi, lo, color='green', alpha=0.15)
    plot_trades(axes3[0], buy_trades)
    xl, xr, ymin, ymax = trade_zoom(buy_trades, randomCandles)
    axes3[0].set_xlim(xl, xr); axes3[0].set_ylim(ymin, ymax)
    fig3.savefig('chart_3.png', dpi=100, pad_inches=0.4); plt.close(fig3)

if sell_trades:
    df4 = to_df(randomCandles)
    fig4, axes4 = mpf.plot(df4, type='candle', volume=True, style=style,
        returnfig=True, warn_too_much_data=10000, figsize=(16, 8),
        title='chart 4: short trades only (zoomed)')
    for hi, lo, cnt in resChannels: axes4[0].fill_between(range(len(df4)), hi, lo, color='red', alpha=0.15)
    for hi, lo, cnt in supChannels: axes4[0].fill_between(range(len(df4)), hi, lo, color='green', alpha=0.15)
    plot_trades(axes4[0], sell_trades)
    xl, xr, ymin, ymax = trade_zoom(sell_trades, randomCandles)
    axes4[0].set_xlim(xl, xr); axes4[0].set_ylim(ymin, ymax)
    fig4.savefig('chart_4.png', dpi=100, pad_inches=0.4); plt.close(fig4)

print("chart_2.png : 1m all + all trades")
if buy_trades: print("chart_3.png : long trades only (zoomed)")
if sell_trades: print("chart_4.png : short trades only (zoomed)")
