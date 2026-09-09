"""
Standalone test: verify orders work the same on 1m and 5m timeframes independently.

Generates 50 x 1m candles and 50 x 5m candles SEPARATELY (unrelated data).
Finds support/resistance channels on each independently.
Runs the SAME signal + order logic on each.
Both must produce the same KIND of output (entry/sl/tp/win/loss structure).

Run:  py test_orders.py
Output: results.json written every run
"""
from collections import Counter
import random
import json
from datetime import datetime


def readableTime(timestamp):
    return datetime.fromtimestamp(timestamp)


def generateCandles(count, timeframe, startPrice=20, endPrice=25, offsetRange=0.05):
    candles = []
    baseStamp = random.randint(1700000000, 1700014400)
    baseStamp = baseStamp - (baseStamp % 60)
    currentPrice = random.uniform(startPrice, endPrice)
    offset = random.uniform(0, offsetRange)
    for i in range(count):
        openPrice = currentPrice
        highPrice = random.uniform(openPrice, openPrice + (offset * openPrice))
        lowPrice = random.uniform(openPrice - (offset * openPrice), openPrice)
        closePrice = random.uniform(lowPrice, highPrice)
        volume = random.randint(1000, 3000)
        timestamp = readableTime(baseStamp + (i * timeframe))
        candles.append((openPrice, highPrice, lowPrice, closePrice, volume, timestamp))
        currentPrice = closePrice
    return candles


def candleSupportResistance(candles, k):
    resistancePoints = []
    supportPoints = []

    for i in range(k, len(candles) - k):
        leftMax  = max(candles[i-j][1] for j in range(1, k+1))
        rightMax = max(candles[i+j][1] for j in range(1, k+1))
        leftMin  = min(candles[i-j][2] for j in range(1, k+1))
        rightMin = min(candles[i+j][2] for j in range(1, k+1))

        if(candles[i][1] > leftMax and candles[i][1] > rightMax):
            resistancePoints.append((candles[i][1], i))

        if(candles[i][2] < leftMin and candles[i][2] < rightMin):
            supportPoints.append((candles[i][2], i))

    return (resistancePoints, supportPoints)


def buildChannels(points, closeWidth):
    """points = list of (price, candle_idx). Returns (high, low, count, [idx...])."""
    channels = []
    used = set()
    for idx, (p, p_idx) in enumerate(points):
        if idx in used:
            continue
        low = p
        high = p
        count = 0
        member_idx = []
        for j, (q, q_idx) in enumerate(points):
            if j in used:
                continue
            width = q - high if q > high else low - q if q < low else 0
            if width <= closeWidth:
                low = min(low, q)
                high = max(high, q)
                count += 1
                member_idx.append(q_idx)
                used.add(j)
        channels.append((high, low, count, member_idx))

    channels.sort(key=lambda c: c[2], reverse=True)
    return [c for c in channels if c[2] >= 2][:4]


def analyzeSR(candles, k=2, widthPercent=0.08):
    resistancePoints, supportPoints = candleSupportResistance(candles, k)
    closeWidth = (max(c[1] for c in candles) - min(c[2] for c in candles)) * widthPercent
    resChannels = buildChannels(resistancePoints, closeWidth)
    supChannels = buildChannels(supportPoints, closeWidth)
    return resChannels, supChannels


def findSignals(candles, resChannels, supChannels):
    """Signals carry direction, entry, fibo, candle, channel width — no SL.
    The single SL is derived later from the first TP."""
    longTrades = []
    shortTrades = []
    for i in range(len(candles)):
        for high, low, count, _ in supChannels:
            if(candles[i][2] < low and candles[i][3] > low and candles[i][0] > low):
                entry = high
                channel_width = high - low
                longTrades.append(("BUY", entry, 0.618, i, channel_width))
                longTrades.append(("BUY", entry, 1.618, i, channel_width))
                longTrades.append(("BUY", entry, 2.618, i, channel_width))

        for high, low, count, _ in resChannels:
            if(candles[i][1] > high and candles[i][3] < high and candles[i][0] < high):
                entry = low
                channel_width = high - low
                shortTrades.append(("SELL", entry, 0.618, i, channel_width))
                shortTrades.append(("SELL", entry, 1.618, i, channel_width))
                shortTrades.append(("SELL", entry, 2.618, i, channel_width))

    return longTrades, shortTrades


def select_trades(longTrades, shortTrades, risk_pct=1.2):
    """3 trades per direction, each from a different signal candle.
    Builds base risk (1.2% of entry) and the 3 fibo TPs here."""
    from collections import OrderedDict

    result = []
    for label, raw in [("BUY", longTrades), ("SELL", shortTrades)]:
        sigs = OrderedDict()
        for t in raw:
            sig_idx = t[3]
            if sig_idx not in sigs:
                sigs[sig_idx] = t

        count = 0
        for sig_idx, (d, entry, fibo, idx, ch_w) in sigs.items():
            if count >= 3:
                break
            risk = entry * risk_pct / 100
            tps = [
                (0.618, entry + risk * 0.618 if d == "BUY" else entry - risk * 0.618),
                (1.618, entry + risk * 1.618 if d == "BUY" else entry - risk * 1.618),
                (2.618, entry + risk * 2.618 if d == "BUY" else entry - risk * 2.618),
            ]
            result.append((d, entry, risk, tps, idx))
            count += 1

    return result


def simulate_trade(candles, direction, entry, risk, tps, start):
    """
    Walk candles forward from start. A trade has 3 parts (TP1, TP2, TP3),
    each 1/3 of the position. ONE SL for all parts, calculated from the
    first TP: SL distance = TP1 distance. Returns (sl, parts).
    """
    sl_dist = abs(tps[0][1] - entry)  # SL sits exactly as far as TP1
    sl = round(entry - sl_dist, 4) if direction == "BUY" else round(entry + sl_dist, 4)
    parts = [
        {"tp_level": 1, "fibo": tps[0][0], "tp": tps[0][1], "closed": False, "exit": None, "exit_candle": None, "hit": None},
        {"tp_level": 2, "fibo": tps[1][0], "tp": tps[1][1], "closed": False, "exit": None, "exit_candle": None, "hit": None},
        {"tp_level": 3, "fibo": tps[2][0], "tp": tps[2][1], "closed": False, "exit": None, "exit_candle": None, "hit": None},
    ]

    for j in range(start + 1, len(candles)):
        high, low = candles[j][1], candles[j][2]
        for p in parts:
            if p["closed"]:
                continue
            sl_hit = low <= sl if direction == "BUY" else high >= sl
            tp_hit = high >= p["tp"] if direction == "BUY" else low <= p["tp"]
            if sl_hit:  # same-candle tie: SL wins (pessimistic)
                p["closed"] = True
                p["exit"] = sl
                p["exit_candle"] = j
                p["hit"] = f"SL {p['tp_level']} HIT"
            elif tp_hit:
                p["closed"] = True
                p["exit"] = round(p["tp"], 4)
                p["exit_candle"] = j
                p["hit"] = f"TP {p['tp_level']} HIT"
        if all(p["closed"] for p in parts):
            break

    # Parts never hit: mark-to-market at the last candle's close
    last_close = candles[-1][3]
    last_idx = len(candles) - 1
    for p in parts:
        if not p["closed"]:
            p["closed"] = True
            p["exit"] = round(last_close, 4)
            p["exit_candle"] = last_idx
            p["hit"] = "NO HIT"

    # Profit per part: win = risk * fibo, loss = -sl_dist (single SL), no-hit = mark-to-market
    for p in parts:
        if p["hit"].startswith("TP"):
            p["profit"] = round(risk * p["fibo"], 4)
        elif p["hit"].startswith("SL"):
            p["profit"] = round(-sl_dist, 4)  # every part exits at the single SL
        else:  # NO HIT — unrealized, measured from entry to last close
            if direction == "BUY":
                p["profit"] = round(last_close - entry, 4)
            else:
                p["profit"] = round(entry - last_close, 4)

    return sl, parts


def build_trade(candles, direction, entry, risk, tps, idx, trade_id):
    """Run one trade through simulate_trade and pack the result dict.
    All trade calculation lives here — callers only print."""
    sl, parts = simulate_trade(candles, direction, entry, risk, tps, idx)
    return {
        "id": trade_id,
        "direction": direction,
        "entry_candle": idx,
        "entry": round(entry, 4),
        "sl": round(sl, 4),
        "risk": round(risk, 4),
        "tps": [
            {"level": 1, "fibo": 0.618, "price": round(tps[0][1], 4)},
            {"level": 2, "fibo": 1.618, "price": round(tps[1][1], 4)},
            {"level": 3, "fibo": 2.618, "price": round(tps[2][1], 4)},
        ],
        "parts": [
            {
                "tp_level": p["tp_level"],
                "tp": round(p["tp"], 4),
                "exit": p["exit"],
                "exit_candle": p["exit_candle"],
                "hit": p["hit"],
                "profit": p["profit"],
            }
            for p in parts
        ],
        "total_profit": round(sum(p["profit"] for p in parts), 4),
    }


def run_timeframe(label, timeframe):
    """Generate 50 candles of one timeframe, analyze, produce trades + results."""
    candles = generateCandles(50, timeframe)
    resChannels, supChannels = analyzeSR(candles)

    longTrades, shortTrades = findSignals(candles, resChannels, supChannels)
    selected = select_trades(longTrades, shortTrades)

    trades = [
        build_trade(candles, d, entry, risk, tps, idx, i + 1)
        for i, (d, entry, risk, tps, idx) in enumerate(selected)
    ]

    return {
        "timeframe": label,
        "candles": 50,
        "candle_data": [
            {
                "idx": i,
                "open": round(c[0], 4),
                "high": round(c[1], 4),
                "low": round(c[2], 4),
                "close": round(c[3], 4),
                "volume": c[4],
                "time": str(c[5]),
            }
            for i, c in enumerate(candles)
        ],
        "channels": {
            "resistance": [
                {
                    "high": round(h, 4),
                    "low": round(l, 4),
                    "width": round(h - l, 4),
                    "pivots": c,
                    "pivot_candles": idxs,
                }
                for h, l, c, idxs in resChannels
            ],
            "support": [
                {
                    "high": round(h, 4),
                    "low": round(l, 4),
                    "width": round(h - l, 4),
                    "pivots": c,
                    "pivot_candles": idxs,
                }
                for h, l, c, idxs in supChannels
            ],
        },
        "trades": trades,
        "total_profit": round(sum(t["total_profit"] for t in trades), 4),
    }


if __name__ == "__main__":
    random.seed()  # different data every run

    one_min = run_timeframe("1m", 60)    # 50 x 1m candles
    five_min = run_timeframe("5m", 300)  # 50 x 5m candles

    results = {
        "run_timestamp": datetime.now().isoformat(),
        "timeframes": [one_min, five_min],
    }

    with open("results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Console summary
    for tf in results["timeframes"]:
        print(f"\n=== {tf['timeframe']} — {tf['candles']} candles ===")
        print(f"Resistance channels: {len(tf['channels']['resistance'])}")
        for ch in tf["channels"]["resistance"]:
            print(f"  {ch['low']:.4f} - {ch['high']:.4f} width={ch['width']:.4f} pivots={ch['pivots']} candles={ch['pivot_candles']}")
        print(f"Support channels: {len(tf['channels']['support'])}")
        for ch in tf["channels"]["support"]:
            print(f"  {ch['low']:.4f} - {ch['high']:.4f} width={ch['width']:.4f} pivots={ch['pivots']} candles={ch['pivot_candles']}")
        print(f"Trades: {len(tf['trades'])}")
        for t in tf["trades"]:
            print(f"\n  #{t['id']} {t['direction']}  entry_candle={t['entry_candle']}  entry={t['entry']:.4f}  sl={t['sl']:.4f}  risk(base 1.2%)={t['risk']:.4f}")
            print(f"    TP1(x0.618)={t['tps'][0]['price']:.4f}  TP2(x1.618)={t['tps'][1]['price']:.4f}  TP3(x2.618)={t['tps'][2]['price']:.4f}")
            for p in t["parts"]:
                exit_str = f"candle={p['exit_candle']}" if p['exit_candle'] else "none"
                print(f"    Part {p['tp_level']}: tp={p['tp']:.4f}  {p['hit']}  exit={p['exit']}  {exit_str}  profit={'+' if p['profit']>0 else ''}{p['profit']:.4f}")
            print(f"    TOTAL PROFIT: {'+' if t['total_profit']>0 else ''}{t['total_profit']:.4f}")
        print(f"\n  SUM: {'+' if tf['total_profit']>0 else ''}{tf['total_profit']:.4f}")

    print("\nSaved to results.json")
