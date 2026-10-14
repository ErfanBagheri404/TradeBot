"""
test_merge.py — mergeChannels across all cases + width cap + real data per timeframe
Run:  py test_merge.py
"""
from main import mergeChannels

CW = 0.0006          # test closeWidth
MW = CW * 4          # default maxWidth in mergeChannels = 0.0024

def z(lo, w=0.0005, score=1.0):
    return (lo + w, lo, score, lo + w / 2)

cases = {
    "1 B inside A":      (z(1.08950), z(1.08970, 0.0003)),
    "2 A inside B":      (z(1.08970, 0.0003), z(1.08950)),
    "3 B crosses A top": (z(1.08950), z(1.08980)),
    "4 B crosses A bot": (z(1.08950), z(1.08920)),
    "5 gap 0.5p < CW":   (z(1.08950), z(1.09050, 0.0004)),
    "6 gap 15p > CW":    (z(1.08950), z(1.09150)),
}

print("=== synthetic cases ===")
ok = True
expect = {"1": "MERGED", "2": "MERGED", "3": "MERGED", "4": "MERGED", "5": "MERGED", "6": "SEPARATE"}
for label, pair in cases.items():
    out = mergeChannels(list(pair), CW)
    verdict = "MERGED" if len(out) == 1 else "SEPARATE"
    good = verdict == expect[label[0]]
    ok &= good
    print(f"  {label:20s} -> {verdict:8s} {'ok' if good else 'FAIL'}  ({len(out)} ch)")

print("\n=== chain within cap: 3 touching zones -> 1 ===")
chain = [z(1.08900), z(1.08940), z(1.08960)]  # gaps 0 and 0, total w=0.0011
out = mergeChannels(chain, CW)
good = len(out) == 1
ok &= good
print(f"  {len(out)} channel(s), w={(out[0][0]-out[0][1])*10000:.2f}p {'ok' if good else 'FAIL'}")

print("\n=== cap stops the chain: 5 zones stepping 0.5p, cap 4x CW ===")
# each zone 5p wide? no: 0.0005 = 5 pips. stepping 0.0005. cap 0.0024 -> max 4 zones
stepped = [z(1.08950 + 0.0005 * i) for i in range(5)]
out = mergeChannels(stepped, CW)
widths = [round((h - l) * 10000, 2) for h, l, s, b in out]
good = len(out) == 2 and all(w <= MW * 10000 + 1e-6 for w in widths)
ok &= good
print(f"  {len(out)} channel(s) widths={widths}p (cap {MW*10000:.2f}p) {'ok' if good else 'FAIL'}")

print("\n=== score + body_mid ===")
a, b = z(1.08950, 0.0005, 2.0), z(1.08990, 0.0005, 3.0)
out = mergeChannels([a, b], CW)[0]
good = abs(out[2] - 5.0) < 1e-9
ok &= good
print(f"  score {out[2]} (expect 5.0)  body_mid {out[3]:.6f} {'ok' if good else 'FAIL'}")

print("\n=== real data per timeframe ===")
from data_loader import load_candles
from main import analyzeSR

def leftovers(cs, cw, mw):
    bad = []
    for i in range(len(cs)):
        for j in range(i + 1, len(cs)):
            hi, lo = cs[i][0], cs[i][1]
            hi2, lo2 = cs[j][0], cs[j][1]
            overlap = lo <= hi2 and lo2 <= hi
            gap = max(0, max(lo, lo2) - min(hi, hi2))
            if overlap or gap <= cw:
                w = max(hi, hi2) - min(lo, lo2)
                if w <= mw:  # mergeable AND under cap = should have merged
                    bad.append((i, j, round(gap, 8), round(w, 8)))
    return bad

for tf in ["3min", "5min", "15min", "30min"]:
    try:
        candles = load_candles(tf, limit=6000)
    except Exception as e:
        print(f"  {tf:6s} SKIP ({type(e).__name__})")
        continue
    bodies = sorted(abs(c[3] - c[0]) for c in candles)
    n = len(bodies)
    cw = bodies[n // 2] if n % 2 == 1 else (bodies[n // 2 - 1] + bodies[n // 2]) / 2
    zones, raw = analyzeSR(candles)
    bad = leftovers(zones, cw, cw * 4)
    widths = [round((h - l) * 10000, 2) for h, l, s, b in zones]
    ok &= not bad
    print(f"  {tf:6s} zones={len(zones)} widths={widths}p cw={cw*10000:.2f}p leftover={len(bad)} {'ok' if not bad else 'FAIL'}")
    if bad:
        print(f"          {bad}")

print("\nALL PASS" if ok else "\nFAILURES ABOVE")
