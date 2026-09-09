"""Entry=20 test for the single-SL (derived from TP1) system.
BUY and SELL, entry forced to 20, walked over random candles around 20."""
from test_orders import generateCandles, simulate_trade

UNIT = 20 * 0.012  # 1.2% TP scale; SL = unit * 0.618

def make_tps(direction):
    sign = 1 if direction == "BUY" else -1
    return [
        (0.618, 20 + sign * UNIT * 0.618),
        (1.618, 20 + sign * UNIT * 1.618),
        (2.618, 20 + sign * UNIT * 2.618),
    ]

print(f"entry=20.00  unit(1.2%)={UNIT:.4f}  SL distance=TP1 distance={UNIT*0.618:.4f}")
for d in ("BUY", "SELL"):
    tps = make_tps(d)
    sl, parts = simulate_trade(generateCandles(50, 60, 19.9, 20.1), d, 20.0, tps, 10)
    print(f"\n{d} sample:  sl={sl:.4f}  tp1={tps[0][1]:.4f}  tp2={tps[1][1]:.4f}  tp3={tps[2][1]:.4f}")
    for p in parts:
        print(f"  Part {p['tp_level']}: {p['hit']}  exit={p['exit']}  candle={p['exit_candle']}  profit={'+' if p['profit']>0 else ''}{p['profit']}")

print("\n=== 100 runs per direction ===")
for d in ("BUY", "SELL"):
    tps = make_tps(d)
    hits = {"TP1": 0, "TP2": 0, "TP3": 0, "SL1": 0, "SL2": 0, "SL3": 0, "NOHIT": 0}
    total = 0.0
    for _ in range(100):
        sl, parts = simulate_trade(generateCandles(50, 60, 19.9, 20.1), d, 20.0, tps, 10)
        for p in parts:
            h = p["hit"]
            if h.startswith("TP"):
                hits["TP" + h.split()[1][:1]] += 1
            elif h.startswith("SL"):
                hits["SL" + h.split()[1][:1]] += 1
            else:
                hits["NOHIT"] += 1
        total += sum(p["profit"] for p in parts)
    print(f"\n{d}:  total_profit(100 trades)={total:+.4f}  mean={total/100:+.4f}")
    print(f"  TP hits: {hits['TP1']}/{hits['TP2']}/{hits['TP3']}   SL hits: {hits['SL1']}/{hits['SL2']}/{hits['SL3']}   no-hit: {hits['NOHIT']}")
