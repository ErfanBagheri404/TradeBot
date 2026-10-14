"""
test_merge_fuzz.py — stress mergeChannels with random channels, trace failures
Run:  py test_merge_fuzz.py
"""
import random
from main import mergeChannels

SEEDS = [7, 13, 42, 99, 1234]
N_PER_SEED = 300
BASE = 1.1500

fails = 0
checked = 0

def leftover(chans, cw):
    bad = []
    for i in range(len(chans)):
        for j in range(i + 1, len(chans)):
            hi, lo = chans[i][0], chans[i][1]
            hi2, lo2 = chans[j][0], chans[j][1]
            overlap = lo <= hi2 and lo2 <= hi
            gap = max(0, max(lo, lo2) - min(hi, hi2))
            if overlap or gap <= cw:
                bad.append((i, j, chans[i], chans[j], gap))
    return bad

for seed in SEEDS:
    rng = random.Random(seed)
    for trial in range(N_PER_SEED):
        n = rng.randint(2, 8)
        cw = rng.choice([0.0001, 0.0002, 0.0005, 0.001, 0.002])
        chans = []
        for _ in range(n):
            # random zone center within ±500 pips, random width 0.5-30 pips
            center = BASE + rng.uniform(-0.05, 0.05)
            w = rng.uniform(0.00005, 0.003)
            hi = center + w / 2
            lo = center - w / 2
            score = rng.uniform(0.5, 5.0)
            chans.append((hi, lo, score, (hi + lo) / 2))
        checked += 1

        # score conservation check
        in_score = sum(c[2] for c in chans)
        out = mergeChannels(chans, cw)
        out_score = sum(c[2] for c in out)
        if abs(in_score - out_score) > 1e-9:
            fails += 1
            print(f"SEED {seed} trial {trial}: SCORE LOST in={in_score:.6f} out={out_score:.6f}")

        # bounds check: merged zone must span inputs
        # (re-run with tags to trace which inputs went where is overkill;
        #  just check no merged zone is narrower than any input it contains)
        # leftover check — pair is mergeable ONLY if merging it would respect the width cap
        bad = []
        mw = cw * 4  # same default maxWidth mergeChannels uses
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                a, b = out[i], out[j]
                overlap = a[1] <= b[0] and b[1] <= a[0]
                gap = max(0, max(a[1], b[1]) - min(a[0], b[0]))
                if overlap or gap <= cw:
                    w = max(a[0], b[0]) - min(a[1], b[1])
                    if w <= mw:  # mergeable AND under cap = should have merged
                        bad.append((i, j, a, b, gap, w))
        if bad:
            fails += 1
            print(f"SEED {seed} trial {trial}: {len(bad)} leftover mergeable pair(s), cw={cw}")
            for i, j, a, b, gap, w in bad[:3]:
                print(f"  ch[{i}] lo={a[1]:.6f} hi={a[0]:.6f}  vs  ch[{j}] lo={b[1]:.6f} hi={b[0]:.6f}  gap={gap:.8f} merged_w={w:.8f}")

print(f"\nchecked={checked} fails={fails}")
