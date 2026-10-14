"""
test_kmarge.py — what happens if we merge k=3 and k=5 zones
Run:  py test_kmarge.py
"""
from data_loader import load_candles
from main import analyzeSR, mergeChannels, findSignals, select_trades, build_trade

for tf in ["5min", "15min", "30min"]:
    try:
        candles = load_candles(tf, limit=6000)
    except Exception as e:
        print(f"{tf}: SKIP {type(e).__name__}")
        continue

    z3 = analyzeSR(candles, 3)
    z5 = analyzeSR(candles, 5)

    bodies = sorted(abs(c[3] - c[0]) for c in candles)
    n = len(bodies)
    cw = bodies[n // 2] if n % 2 == 1 else (bodies[n // 2 - 1] + bodies[n // 2]) / 2

    km = mergeChannels(list(z3) + list(z5), cw)   # both k, merged
    km.sort(key=lambda c: c[2], reverse=True)

    print(f"=== {tf} ===")
    print(f"  k=3 only: {len(z3)} zones   k=5 only: {len(z5)} zones   merged both: {len(km)} zones")

    # signals using merged zones
    lng, sht = findSignals(candles, km)
    print(f"  signals with merged k: {len(lng)} long + {len(sht)} short")
    trades = [build_trade(candles, d, e, t, i, w, x + 1)
              for x, (d, e, t, i, w) in enumerate(select_trades(lng, sht))]
    tot = sum(t["total_profit"] for t in trades)
    print(f"  trades: {len(trades)}   SUM: {'+' if tot > 0 else ''}{tot}")

    print("  merged zones:")
    for hi, lo, score, bm in km:
        print(f"    {lo:.6f} - {hi:.6f}  score={score}  body_mid={bm}")
    print()
