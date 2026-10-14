"""
diag_cap.py — are zones saturating the width cap?  Run:  py diag_cap.py
"""
import sys
from data_loader import load_candles
from main import analyzeSR, buildChannels, candleSupportResistance, mergeChannels

for tf in ["3min", "5min", "15min", "30min"]:
    candles = load_candles(tf, limit=6000)
    bodies = sorted(abs(c[3] - c[0]) for c in candles)
    n = len(bodies)
    cw = bodies[n // 2] if n % 2 == 1 else (bodies[n // 2 - 1] + bodies[n // 2]) / 2
    mw = cw * 4

    # raw channels with NO cap at all, to see natural widths
    rawall = []
    for k in (3, 5):
        rp, sp = candleSupportResistance(candles, k)
        for pts in (rp, sp):
            # maxWidth huge = uncapped
            rawall += buildChannels(pts, cw, candles, maxWidth=1e9)

    widths = sorted((h - l) * 10000 for h, l, s, b in rawall)
    zones, _ = analyzeSR(candles)
    zw = [(h - l) * 10000 for h, l, s, b in zones]
    atcap = sum(1 for w in zw if w > mw * 10000 * 0.95)
    print(f"{tf:6s} cw={cw*10000:.2f}p cap={mw*10000:.2f}p")
    print(f"       uncapped raw widths: n={len(widths)} min={widths[0]:.2f} med={widths[len(widths)//2]:.2f} max={widths[-1]:.2f}")
    print(f"       merged zones: {[round(w,2) for w in zw]}  at_cap={atcap}/{len(zw)}")
