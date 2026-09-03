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


def findSignals(candles, resChannels, supChannels, risk=1.2):
    longTrades = []
    shortTrades = []
    for i in range(len(candles)):
        for high, low, count, _ in supChannels:
            if(candles[i][2] < low and candles[i][3] > low and candles[i][0] > low):
                entry = high
                channel_width = high - low
                sl = entry * (1 - risk/100)
                longTrades.append(("BUY", entry, sl, 0.618, i, channel_width))
                longTrades.append(("BUY", entry, sl, 1.618, i, channel_width))
                longTrades.append(("BUY", entry, sl, 2.618, i, channel_width))

        for high, low, count, _ in resChannels:
            if(candles[i][1] > high and candles[i][3] < high and candles[i][0] < high):
                entry = low
                channel_width = high - low
                sl = entry * (1 + risk/100)
                shortTrades.append(("SELL", entry, sl, 0.618, i, channel_width))
                shortTrades.append(("SELL", entry, sl, 1.618, i, channel_width))
                shortTrades.append(("SELL", entry, sl, 2.618, i, channel_width))

    return longTrades, shortTrades


def find_hit_candle(candles, direction, entry, sl, tp, start):
    """Scan candles forward from start. Return which hit first: 'tp' or 'sl'."""
    for j in range(start + 1, len(candles)):
        high, low = candles[j][1], candles[j][2]
        if direction == "BUY":
            if low <= sl:
                return "sl"
            if high >= tp:
                return "tp"
        else:  # SELL
            if high >= sl:
                return "sl"
            if low <= tp:
                return "tp"
    return "none"


def select_orders(longTrades, shortTrades):
    """Pick first BUY signal group + first SELL signal group = 3 buys + 3 sells."""
    orders = []

    # First BUY signal (all 3 fibos share same entry/candle)
    buys = [t for t in longTrades if t[0] == "BUY"]
    if buys:
        first_candle = buys[0][4]
        group = [t for t in buys if t[4] == first_candle]
        for direction, entry, sl, fibo, idx, ch_w in group:
            orders.append(("BUY", entry, sl, fibo, idx))

    sells = [t for t in shortTrades if t[0] == "SELL"]
    if sells:
        first_candle = sells[0][4]
        group = [t for t in sells if t[4] == first_candle]
        for direction, entry, sl, fibo, idx, ch_w in group:
            orders.append(("SELL", entry, sl, fibo, idx))

    return orders


def run_timeframe(label, timeframe):
    """Generate 50 candles of one timeframe, analyze, produce orders + results."""
    candles = generateCandles(50, timeframe)
    resChannels, supChannels = analyzeSR(candles)

    longTrades, shortTrades = findSignals(candles, resChannels, supChannels)
    selected = select_orders(longTrades, shortTrades)

    orders = []
    for direction, entry, sl, fibo, idx in selected:
        if direction == "BUY":
            risk = entry - sl
            tp = entry + risk * fibo
        else:
            risk = sl - entry
            tp = entry - risk * fibo
        result = find_hit_candle(candles, direction, entry, sl, tp, idx)
        profit = risk * fibo if result == "tp" else (-risk if result == "sl" else 0.0)
        orders.append({
            "id": len(orders) + 1,
            "direction": direction,
            "entry_candle": idx,
            "entry": round(entry, 4),
            "sl": round(sl, 4),
            "tp": round(tp, 4),
            "fibo": fibo,
            "result": "WIN" if result == "tp" else "LOSS" if result == "sl" else "NO HIT",
            "profit": round(profit, 4),
        })

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
        "orders": orders,
        "total_profit": round(sum(o["profit"] for o in orders), 4),
        "wins": sum(1 for o in orders if o["result"] == "WIN"),
        "losses": sum(1 for o in orders if o["result"] == "LOSS"),
        "no_hits": sum(1 for o in orders if o["result"] == "NO HIT"),
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
            print(f"  {ch['low']:.4f} - {ch['high']:.4f} pivots={ch['pivots']} candles={ch['pivot_candles']}")
        print(f"Support channels: {len(tf['channels']['support'])}")
        for ch in tf["channels"]["support"]:
            print(f"  {ch['low']: .4f} - {ch['high']: .4f} pivots={ch['pivots']} candles={ch['pivot_candles']}")
        print(f"Orders: {len(tf['orders'])}")
        for o in tf["orders"]:
            print(f"  #{o['id']} {o['direction']:4} entry={o['entry']:.4f} sl={o['sl']:.4f} "
                  f"tp={o['tp']:.4f} → {o['result']} ({'+' if o['profit']>0 else ''}{o['profit']:.4f})")
        print(f"Total: {tf['total_profit']:+.4f} | W:{tf['wins']} L:{tf['losses']} N:{tf['no_hits']}")

    print("\nSaved to results.json")
