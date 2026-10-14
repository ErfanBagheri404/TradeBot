"""
EUR/USD 15min — same output format as main.py
Run:  py test_eur_15min.py
"""
from datetime import datetime
from main import (
    analyzeSR,
    findSignals,
    select_trades,
    build_trade,
    candleHighLow,
)
from data_loader import load_candles

candles = load_candles("15min")

# ---------- candle preview ----------
for i in range(min(10, len(candles))):
    print(f"Candle {i+1}: Open: {candles[i][0]}, High: {candles[i][1]}, Low: {candles[i][2]}, Close: {candles[i][3]}, Volume: {candles[i][4]}, Timestamp: {candles[i][5]}")
print(f"... ({len(candles)} candles total, 15min)")

high, low, lowestHigh, highestHigh = candleHighLow(candles)
print(f"Highest: {high}, Lowest: {low}")
print(f"Lowest High: {lowestHigh}, Highest High: {highestHigh}")

# ---------- channels ----------
zones, raw = analyzeSR(candles)

print("15min Channels (k=3+5, sup+res):")
for hi, lo, score, body_mid in zones:
    print(f"  {lo:.6f} - {hi:.6f}  score={score} body_mid={body_mid}")

for k, (resC, supC) in raw.items():
    print(f"\n15min Resistance channels (k={k}):")
    for hi, lo, score, body_mid in resC:
        print(f"  {lo:.6f} - {hi:.6f}  score={score} body_mid={body_mid}")
    print(f"15min Support channels (k={k}):")
    for hi, lo, score, body_mid in supC:
        print(f"  {lo:.6f} - {hi:.6f}  score={score} body_mid={body_mid}")

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
    print(f"\n  #{t['id']} {t['direction']}  entry_candle={t['entry_candle']}  entry={t['entry']:.10f}  sl={t['sl']:.10f}  risk={t['risk']:.10f}")
    print(f"    TP1(x{t['tps'][0]['fibo']})={t['tps'][0]['price']:.10f}  TP2(x{t['tps'][1]['fibo']})={t['tps'][1]['price']:.10f}  TP3(x{t['tps'][2]['fibo']})={t['tps'][2]['price']:.10f}")
    for p in t["parts"]:
        print(f"    Part {p['tp_level']}: tp={p['tp']:.10f}  {p['hit']}  exit={p['exit']}  candle={p['exit_candle']}  profit={'+' if p['profit']>0 else ''}{p['profit']:.10f}")
    print(f"    TOTAL PROFIT: {'+' if t['total_profit']>0 else ''}{t['total_profit']:.10f}")
print(f"\nSUM: {'+' if sum(t['total_profit'] for t in trades)>0 else ''}{sum(t['total_profit'] for t in trades):.10f}")
