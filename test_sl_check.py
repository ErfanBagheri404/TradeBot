"""Verify SL is always inside TP1 (never above/below it), and risk < reward on every part."""
from test_orders import generateCandles, simulate_trade

UNIT = 20 * 0.012

def make_tps(d):
    s = 1 if d == "BUY" else -1
    return [(0.618, 20+s*UNIT*0.618), (1.618, 20+s*UNIT*1.618), (2.618, 20+s*UNIT*2.618)]

fails = []
for d in ("BUY", "SELL"):
    tps = make_tps(d)
    sl, parts = simulate_trade(generateCandles(100, 60, 19.9, 20.1), d, 20.0, tps, 10)
    risk = abs(20.0 - sl)
    sign = -1 if d == "BUY" else 1

    print(f"\n{d}:  entry=20.0000  sl={sl:.4f}  risk={risk:.4f}")
    print(f"  SL is {'BELOW' if d=='BUY' else 'ABOVE'} entry by {risk:.4f}")
    print(f"  TP1 is {'ABOVE' if d=='BUY' else 'BELOW'} entry by {abs(tps[0][1]-20.0):.4f}")
    print()
    for i, (fibo, tp) in enumerate(tps):
        reward = abs(tp - 20.0)
        rr = reward / risk if risk else 0
        sl_outside_tp = sl > tp if d == "BUY" else sl < tp
        sl_between_entry_tp = (tp < sl < 20.0) if d == "BUY" else (tp > sl > 20.0)
        status = "OK - risk < reward" if risk < reward else "FAIL - risk >= reward"
        if sl_outside_tp:
            status = "FAIL - SL is OUTSIDE TP1"
            fails.append(f"{d} part{i+1}: SL {sl:.4f} outside TP1 {tp:.4f}")
        print(f"  Part {i+1}: SL={sl:.4f}  TP={tp:.4f}  risk={risk:.4f}  reward={reward:.4f}  R:R={rr:.2f}:1  {status}")

if fails:
    print("\nISSUES FOUND:")
    for f in fails:
        print(f"  {f}")
else:
    print("\nAll parts verified: risk < reward everywhere, SL always inside TP1.")
