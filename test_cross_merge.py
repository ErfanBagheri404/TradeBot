"""
test_cross_merge.py — check if res and sup zones overlap each other
Run:  py test_cross_merge.py
"""
from data_loader import load_candles
from main import analyzeSR, mergeChannels

def overlaps_or_close(cs, cw):
    bad=[]
    for i in range(len(cs)):
        for j in range(i+1,len(cs)):
            hi,lo=cs[i][0],cs[i][1]; hi2,lo2=cs[j][0],cs[j][1]
            if (lo<=hi2 and lo2<=hi) or max(0,max(lo,lo2)-min(hi,hi2))<=cw:
                bad.append((i,j))
    return bad

for tf in ["3min", "5min", "15min", "30min"]:
    try:
        candles = load_candles(tf, limit=6000)
    except Exception as e:
        print(f"{tf}: SKIP {type(e).__name__}")
        continue
    bodies = sorted(abs(c[3] - c[0]) for c in candles)
    n = len(bodies)
    cw = bodies[n // 2] if n % 2 == 1 else (bodies[n // 2 - 1] + bodies[n // 2]) / 2

    zones = analyzeSR(candles)
    bad = overlaps_or_close(zones, cw)
    print(f"{tf:6s} zones={len(zones)}  leftover mergeable pairs={len(bad)}")
    if bad:
        print(f"        {bad}")
    print()
