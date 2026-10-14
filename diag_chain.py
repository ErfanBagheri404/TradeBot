"""
diag_chain.py — trace which raw channels chain together into each merged zone
Run:  py diag_chain.py
"""
from data_loader import load_candles
from main import analyzeSR

candles = load_candles("5min", limit=6000)
zones, raw = analyzeSR(candles)

bodies = sorted(abs(c[3] - c[0]) for c in candles)
n = len(bodies)
cw = bodies[n // 2] if n % 2 == 1 else (bodies[n // 2 - 1] + bodies[n // 2]) / 2
print(f"closeWidth = {cw:.8f}  ({cw*10000:.2f} pips)\n")

# all raw channels from both k
allraw = []
for k, (resC, supC) in raw.items():
    for hi, lo, sc, bm in resC:
        allraw.append((k, "RES", lo, hi, sc))
    for hi, lo, sc, bm in supC:
        allraw.append((k, "SUP", lo, hi, sc))
allraw.sort(key=lambda x: x[2])

print("all raw channels sorted by low:")
for k, side, lo, hi, sc in allraw:
    print(f"  k={k} {side}  {lo:.6f} - {hi:.6f}  width={hi-lo:.8f} ({(hi-lo)*10000:.2f}p)  score={sc:.2f}")

print("\nmerged zones + width:")
for hi, lo, sc, bm in zones:
    print(f"  {lo:.6f} - {hi:.6f}  width={hi-lo:.8f} ({(hi-lo)*10000:.2f}p)  score={sc:.2f}  = {((hi-lo)/cw):.1f}x closeWidth")

# simulate greedy chain merge with trace
print("\nchain trace (greedy, edge-to-edge gap <= closeWidth):")
chans = [(lo, hi) for _, _, lo, hi, _ in allraw]
chans.sort()
used = [False]*len(chans)
for i in range(len(chans)):
    if used[i]:
        continue
    lo, hi = chans[i]
    used[i] = True
    members = [(chans[i], 0.0)]
    changed = True
    while changed:
        changed = False
        for j in range(len(chans)):
            if used[j]:
                continue
            lo2, hi2 = chans[j]
            gap = max(0, max(lo, lo2) - min(hi, hi2))
            if gap <= cw:
                members.append((chans[j], gap))
                lo, hi = min(lo, lo2), max(hi, hi2)
                used[j] = True
                changed = True
    if len(members) > 1:
        print(f"  zone {lo:.6f}-{hi:.6f} width={(hi-lo)*10000:.2f}p from {len(members)} channels:")
        for (mlo, mhi), g in members:
            print(f"      {mlo:.6f}-{mhi:.6f} ({(mhi-mlo)*10000:.2f}p)  gap_to_prev={g*10000:.2f}p")
