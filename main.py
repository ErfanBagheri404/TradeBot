from collections import Counter
import random
from datetime import datetime


def readableTime(timestamp):
    return datetime.fromtimestamp(timestamp)


def candleHighLow(candles):
    max = candles[0][1]
    min = candles[0][2]
    lowestHigh = candles[0][1]
    highestHigh = candles[0][1]
    for candle in candles:
        if candle[1] > max:
            max = candle[1]
        if candle[2] < min:
            min = candle[2]
        if candle[1] < lowestHigh:
            lowestHigh = candle[1]
        if candle[1] > highestHigh:
            highestHigh = candle[1]
    return (max, min, lowestHigh, highestHigh)


def candleSupportResistance(candles, k):
    resistancePoints = []
    supportPoints = []

    for i in range(k, len(candles) - k):
        leftMax  = max(candles[i-j][1] for j in range(1, k+1))
        rightMax = max(candles[i+j][1] for j in range(1, k+1))
        leftMin  = min(candles[i-j][2] for j in range(1, k+1))
        rightMin = min(candles[i+j][2] for j in range(1, k+1))

        if(candles[i][1] > leftMax and candles[i][1] > rightMax):
            resistancePoints.append(candles[i][1])

        if(candles[i][2] < leftMin and candles[i][2] < rightMin):
            supportPoints.append(candles[i][2])

    return (resistancePoints, supportPoints)


def buildChannels(points, closeWidth):
    channels = []
    used = set()
    for idx, p in enumerate(points):
        if idx in used:
            continue
        low = p
        high = p
        count = 0
        for j, q in enumerate(points):
            if j in used:
                continue
            width = q - high if q > high else low - q if q < low else 0
            if width <= closeWidth:
                low = min(low, q)
                high = max(high, q)
                count += 1
                used.add(j)
        channels.append((high, low, count))

    def get_count(channel):
        return channel[2]
    channels.sort(key=get_count, reverse=True)
    return [c for c in channels if c[0] - c[1] > closeWidth][:4]


def resistanceSupportCounter(resistancePoints, supportPoints):
    for i in range(len(resistancePoints)):
        resistancePoints[i] = round(resistancePoints[i], 1)
    for i in range(len(supportPoints)):
        supportPoints[i] = round(supportPoints[i], 1)
    resistanceCount = Counter(resistancePoints)
    supportCount = Counter(supportPoints)
    return resistanceCount, supportCount


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

randomCandles = generateCandles(50, 60) # 1m candles > 5m candles = 5000 candles

def analyzeSR(candles, k=3, widthPercent=0.05):
    resistancePoints, supportPoints = candleSupportResistance(candles, k)
    closeWidth = (max(c[1] for c in candles) - min(c[2] for c in candles)) * widthPercent
    resChannels = buildChannels(resistancePoints, closeWidth)
    supChannels = buildChannels(supportPoints, closeWidth)
    return resChannels, supChannels

def findSignals(candles, resChannels, supChannels, risk=1.2):
    longTrades = []
    shortTrades = []
    for i in range(len(candles)):
        for high, low, count in supChannels:
            if(candles[i][2] < low and candles[i][3] > low and candles[i][0] > low):
                entry = high
                channel_width = high - low
                sl = entry * (1 - risk/100)
                longTrades.append(("BUY", entry, sl, 0.618, i, channel_width)) 
                longTrades.append(("BUY", entry, sl, 1.618, i, channel_width))
                longTrades.append(("BUY", entry, sl, 2.618, i, channel_width))

        for high, low, count in resChannels:
            if(candles[i][1] > high and candles[i][3] < high and candles[i][0] < high):
                entry = low
                channel_width = high - low
                sl = entry * (1 + risk/100)
                shortTrades.append(("SELL", entry, sl, 0.618, i, channel_width))
                shortTrades.append(("SELL", entry, sl, 1.618, i, channel_width))
                shortTrades.append(("SELL", entry, sl, 2.618, i, channel_width))

    return longTrades, shortTrades

for i in range(min(10, len(randomCandles))):
    print(f"Candle {i+1}: Open: {randomCandles[i][0]}, High: {randomCandles[i][1]}, Low: {randomCandles[i][2]}, Close: {randomCandles[i][3]}, Volume: {randomCandles[i][4]}, Timestamp: {randomCandles[i][5]}")
print(f"... ({len(randomCandles)} candles total, 1m)")

high, low, lowestHigh, highestHigh = candleHighLow(randomCandles)
print(f"Highest: {high}, Lowest: {low}")
print(f"Lowest High: {lowestHigh}, Highest High: {highestHigh}")


resChannels, supChannels = analyzeSR(randomCandles, 3)    
resChannels2, supChannels2 = analyzeSR(randomCandles, 5)  

print("Resistance channels (k=3):")
for hi, lo, count in resChannels:
    print(f"  {lo:.2f} - {hi:.2f}  pivots={count}")
print("Support channels (k=3):")
for hi, lo, count in supChannels:
    print(f"  {lo:.2f} - {hi:.2f}  pivots={count}")

print("Resistance channels (k=5):")
for hi, lo, count in resChannels2:
    print(f"  {lo:.2f} - {hi:.2f}  pivots={count}")
print("Support channels (k=5):")
for hi, lo, count in supChannels2:
    print(f"  {lo:.2f} - {hi:.2f}  pivots={count}")

longTrades, shortTrades = findSignals(randomCandles, resChannels, supChannels)
print(f"\nRaw: {len(longTrades)} long + {len(shortTrades)} short signals")


# ─── Trade simulation (same as test_orders.py) ───────────────────
from collections import OrderedDict

def simulate_trade(candles, direction, entry, sl, tps, start):
    """Walk candles forward. 3 parts (TP1/TP2/TP3), each exits at its TP or SL."""
    parts = [
        {"tp_level": 1, "fibo": tps[0][0], "tp": tps[0][1], "closed": False, "exit": None, "exit_candle": None, "hit": None},
        {"tp_level": 2, "fibo": tps[1][0], "tp": tps[1][1], "closed": False, "exit": None, "exit_candle": None, "hit": None},
        {"tp_level": 3, "fibo": tps[2][0], "tp": tps[2][1], "closed": False, "exit": None, "exit_candle": None, "hit": None},
    ]
    risk = abs(entry - sl)

    for j in range(start + 1, len(candles)):
        high, low = candles[j][1], candles[j][2]
        sl_hit = low <= sl if direction == "BUY" else high >= sl
        if sl_hit:
            for p in parts:
                if not p["closed"]:
                    p["closed"] = True
                    p["exit"] = round(sl, 4)
                    p["exit_candle"] = j
                    p["hit"] = f"SL {p['tp_level']} HIT"
            break
        for p in parts:
            if p["closed"]:
                continue
            tp_hit = high >= p["tp"] if direction == "BUY" else low <= p["tp"]
            if tp_hit:
                p["closed"] = True
                p["exit"] = round(p["tp"], 4)
                p["exit_candle"] = j
                p["hit"] = f"TP {p['tp_level']} HIT"

    last_close = candles[-1][3]
    last_idx = len(candles) - 1
    for p in parts:
        if not p["closed"]:
            p["closed"] = True
            p["exit"] = round(last_close, 4)
            p["exit_candle"] = last_idx
            p["hit"] = "NO HIT"

    for p in parts:
        if p["hit"].startswith("TP"):
            p["profit"] = round(risk * p["fibo"], 4)
        elif p["hit"].startswith("SL"):
            p["profit"] = round(-risk, 4)
        else:
            if direction == "BUY":
                p["profit"] = round(last_close - entry, 4)
            else:
                p["profit"] = round(entry - last_close, 4)

    return parts


def select_trades(longTrades, shortTrades):
    """3 trades per direction, each from a different signal candle."""
    result = []
    for label, raw in [("BUY", longTrades), ("SELL", shortTrades)]:
        sigs = OrderedDict()
        for t in raw:
            sig_idx = t[4]
            if sig_idx not in sigs:
                sigs[sig_idx] = t
        count = 0
        for sig_idx, (d, entry, sl, fibo, idx, ch_w) in sigs.items():
            if count >= 3:
                break
            tps = [
                (0.618, entry + (entry - sl) * 0.618 if d == "BUY" else entry - (sl - entry) * 0.618),
                (1.618, entry + (entry - sl) * 1.618 if d == "BUY" else entry - (sl - entry) * 1.618),
                (2.618, entry + (entry - sl) * 2.618 if d == "BUY" else entry - (sl - entry) * 2.618),
            ]
            result.append((d, entry, sl, tps, idx))
            count += 1
    return result


selected = select_trades(longTrades, shortTrades)

trades = []
for direction, entry, sl, tps, idx in selected:
    parts = simulate_trade(randomCandles, direction, entry, sl, tps, idx)
    risk = abs(entry - sl)
    trades.append({
        "id": len(trades) + 1,
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
    })


print(f"\nTrades: {len(trades)}")
for t in trades:
    print(f"\n  #{t['id']} {t['direction']}  entry_candle={t['entry_candle']}  entry={t['entry']:.4f}  sl={t['sl']:.4f}  risk={t['risk']:.4f}")
    print(f"    TP1(x0.618)={t['tps'][0]['price']:.4f}  TP2(x1.618)={t['tps'][1]['price']:.4f}  TP3(x2.618)={t['tps'][2]['price']:.4f}")
    for p in t["parts"]:
        print(f"    Part {p['tp_level']}: tp={p['tp']:.4f}  {p['hit']}  exit={p['exit']}  candle={p['exit_candle']}  profit={'+' if p['profit']>0 else ''}{p['profit']:.4f}")
    print(f"    TOTAL PROFIT: {'+' if t['total_profit']>0 else ''}{t['total_profit']:.4f}")
print(f"\nSUM: {'+' if sum(t['total_profit'] for t in trades)>0 else ''}{sum(t['total_profit'] for t in trades):.4f}")
