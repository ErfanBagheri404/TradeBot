"""
Test main.py logic on the EUR/USD 5min dataset.
Same output format as main.py.
Run:  py test_real.py
"""
from datetime import datetime
from main import (
    analyzeSR,
    findSignals,
    select_trades,
    build_trade,
    candleHighLow,
)
import openpyxl

# ---------- load Excel ----------
wb = openpyxl.load_workbook("datasets/candlestick_eur_5_min.xlsx", read_only=True)
ws = wb.active
candles = []
for i, row in enumerate(ws.iter_rows(values_only=True)):
    if i == 0:
        continue
    o, h, l, c = row[1], row[2], row[3], row[4]
    vol = row[5] or 0
    ts = row[0]
    candles.append((float(o), float(h), float(l), float(c), vol, datetime.fromtimestamp(ts)))
wb.close()

# ---------- candle preview ----------
for i in range(min(10, len(candles))):
    print(f"Candle {i+1}: Open: {candles[i][0]}, High: {candles[i][1]}, Low: {candles[i][2]}, Close: {candles[i][3]}, Volume: {candles[i][4]}, Timestamp: {candles[i][5]}")
print(f"... ({len(candles)} candles total, 5min)")

high, low, lowestHigh, highestHigh = candleHighLow(candles)
print(f"Highest: {high}, Lowest: {low}")
print(f"Lowest High: {lowestHigh}, Highest High: {highestHigh}")

# ---------- channels ----------
zones, raw = analyzeSR(candles)

print("Channels (k=3+5):")
for hi, lo, score, body_mid in zones:
    print(f"  {lo} - {hi}  score={score}  body_mid={body_mid}")
for k, (resC, supC) in raw.items():
    print(f"\nResistance channels (k={k}):")
    for hi, lo, score, body_mid in resC:
        print(f"  {lo} - {hi}  score={score}  body_mid={body_mid}")
    print(f"Support channels (k={k}):")
    for hi, lo, score, body_mid in supC:
        print(f"  {lo} - {hi}  score={score}  body_mid={body_mid}")

# ---------- signals ----------
longTrades, shortTrades = findSignals(candles, zones)
print(f"\nRaw: {len(longTrades)} long + {len(shortTrades)} short signals")

# ---------- trades ----------
trades = [
    build_trade(candles, d, entry, tps, idx, ch_w, i + 1)
    for i, (d, entry, tps, idx, ch_w) in enumerate(select_trades(longTrades, shortTrades))
]

print(f"\nTrades: {len(trades)}")
for t in trades:
    print(f"\n  #{t['id']} {t['direction']}  entry_candle={t['entry_candle']}  entry={t['entry']:.4f}  sl={t['sl']:.4f}  risk={t['risk']:.4f}")
    print(f"    TP1(x0.618)={t['tps'][0]['price']:.4f}  TP2(x1.618)={t['tps'][1]['price']:.4f}  TP3(x2.618)={t['tps'][2]['price']:.4f}")
    for p in t["parts"]:
        print(f"    Part {p['tp_level']}: tp={p['tp']:.4f}  {p['hit']}  exit={p['exit']}  candle={p['exit_candle']}  profit={'+' if p['profit']>0 else ''}{p['profit']:.4f}")
    print(f"    TOTAL PROFIT: {'+' if t['total_profit']>0 else ''}{t['total_profit']:.4f}")
print(f"\nSUM: {'+' if sum(t['total_profit'] for t in trades)>0 else ''}{sum(t['total_profit'] for t in trades):.4f}")
