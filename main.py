from collections import Counter, OrderedDict
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
    resistancePoints = []  # (price, candle_index) pairs
    supportPoints = []
    for i in range(k, len(candles) - k):
        leftMax  = max(candles[i-j][1] for j in range(1, k+1))
        rightMax = max(candles[i+j][1] for j in range(1, k+1))
        leftMin  = min(candles[i-j][2] for j in range(1, k+1))
        rightMin = min(candles[i+j][2] for j in range(1, k+1))
        if(candles[i][1] > leftMax and candles[i][1] > rightMax):
            resistancePoints.append((candles[i][1], i))  # price + index
        if(candles[i][2] < leftMin and candles[i][2] < rightMin):
            supportPoints.append((candles[i][2], i))
    return (resistancePoints, supportPoints)


def mergeChannels(channels, closeWidth, maxWidth=None):
    # merge channels that overlap or sit within closeWidth of each other
    # loop until no more merges — a merged zone may newly touch a third zone
    # maxWidth: refuse a merge if the resulting zone would be wider than this
    # (stops chaining: A touches B, C touches AB, D touches ABC -> huge zone)
    if maxWidth is None:
        maxWidth = closeWidth * 4  # natural channel ~2.6p, 4x = ~5.4p ceiling
    channels = list(channels)
    while True:
        out = []
        used = set()
        did_merge = False
        for i, (hi, lo, score, body_mid) in enumerate(channels):
            if i in used:
                continue
            for j, (hi2, lo2, score2, body_mid2) in enumerate(channels):
                if j <= i or j in used:
                    continue
                # overlapping or close: zone A [lo,hi], zone B [lo2,hi2]
                # overlap if lo <= hi2 and lo2 <= hi; close if gap between edges <= closeWidth
                overlap = lo <= hi2 and lo2 <= hi
                close_gap = max(0, max(lo, lo2) - min(hi, hi2))
                new_hi, new_lo = max(hi, hi2), min(lo, lo2)
                # reject if the resulting zone would be wider than maxWidth
                if new_hi - new_lo > maxWidth:
                    continue
                if overlap or close_gap <= closeWidth:
                    hi, lo = new_hi, new_lo
                    score += score2
                    used.add(j)
                    did_merge = True
            out.append((hi, lo, score, body_mid))
        channels = out
        if not did_merge:
            return channels


def buildChannels(points, closeWidth, candles=None, maxWidth=None):
    # points are (price, candle_index) pairs, total = candle count for weighting
    total = len(candles) if candles is not None else len(points)
    # maxWidth: cap the group width so pivots can't chain into a huge zone
    if maxWidth is None:
        maxWidth = closeWidth * 4
    # weight: 0.2 for oldest pivot, 1.0 for newest
    def pivot_weight(candle_idx):
        return 0.2 + 0.8 * (candle_idx / total) if total > 0 else 1.0
    channels = []
    used = set()  # pivots already grouped, skip them
    for idx, (p, p_idx) in enumerate(points):  # idx = position in list, p = pivot price, p_idx = candle number
        if idx in used:
            continue
        low = p  # bottom of this new group
        high = p  # top of this new group
        score = pivot_weight(p_idx)  # weighted freshness score, not raw count
        for j, (q, q_idx) in enumerate(points): # j is position, q is price. Goes through every pivot again and checks if it belongs in this new group.
            if j in used:
                continue
            # distance from q to the group edges, 0 if inside
            width = q - high if q > high else low - q if q < low else 0
            if width > closeWidth:  # too far, leave it out
                continue
            new_high, new_low = max(high, q), min(low, q)
            if new_high - new_low > maxWidth:  # would balloon the group, leave it out
                continue
            low, high = new_low, new_high  # stretch the group
            score += pivot_weight(q_idx)  # add freshness-weighted value
            used.add(j)  # mark as grouped
        body_mid = None  # avg body center of candles in this zone
        # body center = (open + close) / 2, keep only those inside the zone
        mids = [(c[0] + c[3]) / 2 for c in candles if low <= (c[0] + c[3]) / 2 <= high] if candles is not None else []
        if mids:
            body_mid = sum(mids) / len(mids)  # average of those centers
        channels.append((high, low, score, body_mid))
    channels.sort(key=lambda c: c[2], reverse=True)  # highest score first
    return [c for c in channels if c[0] - c[1] > closeWidth]  # drop flat ones


def resistanceSupportCounter(resistancePoints, supportPoints):
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


def analyzeSR(candles, ks=(3, 5)):
    # returns merged zones + the unmerged per-k/per-side channels for visual check
    bodies = sorted(abs(c[3] - c[0]) for c in candles)  # all body sizes sorted
    n = len(bodies)
    closeWidth = bodies[n // 2] if n % 2 == 1 else (bodies[n // 2 - 1] + bodies[n // 2]) / 2  # median body = grouping size
    raw = {}   # k -> (resChannels, supChannels) unmerged
    zones = []
    for k in ks:
        resistancePoints, supportPoints = candleSupportResistance(candles, k)
        resChannels = buildChannels(resistancePoints, closeWidth, candles)
        supChannels = buildChannels(supportPoints, closeWidth, candles)
        raw[k] = (resChannels, supChannels)
        zones += mergeChannels(resChannels + supChannels, closeWidth)  # res+sup merged per k
    zones = mergeChannels(zones, closeWidth)  # merge across k too
    zones.sort(key=lambda c: c[2], reverse=True)
    return zones[:4], raw  # top 4 merged zones + unmerged channels for inspection


def findSignals(candles, zones):
    longTrades = []
    shortTrades = []
    for i in range(len(candles)):
        for high, low, score, body_mid in zones:
            if(candles[i][2] < low and candles[i][3] > low and candles[i][0] > low):
                entry = high
                channel_width =  high - low
                longTrades.append(("BUY", entry, 0.618, i, channel_width))
                longTrades.append(("BUY", entry, 1.618, i, channel_width))
                longTrades.append(("BUY", entry, 2.618, i, channel_width))
                
            if(candles[i][1] > high and candles[i][3] < high and candles[i][0] < high):
                entry = low
                channel_width = high - low
                shortTrades.append(("SELL", entry, 0.618, i, channel_width))
                shortTrades.append(("SELL", entry, 1.618, i, channel_width))
                shortTrades.append(("SELL", entry, 2.618, i, channel_width))
    return longTrades, shortTrades


def simulate_trade(candles, direction, entry, tps, start, ch_w, sl_pct=1.2):
    sl = entry - (ch_w * sl_pct / 100) if direction == "BUY" else entry + (ch_w * sl_pct / 100)
    sl_dist = abs(entry - sl)
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
            if sl_hit:
                p["closed"] = True
                p["exit"] = sl
                p["exit_candle"] = j
                p["hit"] = f"SL {p['tp_level']} HIT"
            elif tp_hit:
                p["closed"] = True
                p["exit"] = p["tp"]
                p["exit_candle"] = j
                p["hit"] = f"TP {p['tp_level']} HIT"
        if all(p["closed"] for p in parts):
            break
    last_close = candles[-1][3]
    last_idx = len(candles) - 1
    for p in parts:
        if not p["closed"]:
            p["closed"] = True
            p["exit"] = last_close
            p["exit_candle"] = last_idx
            p["hit"] = "NO HIT"
    for p in parts:
        if p["hit"].startswith("TP"):
            p["profit"] = abs(p["tp"] - entry)
        elif p["hit"].startswith("SL"):
            p["profit"] = -sl_dist
        else:
            if direction == "BUY":
                p["profit"] = last_close - entry
            else:
                p["profit"] = entry - last_close
    return sl, parts


def select_trades(longTrades, shortTrades, fibo_pos=0.5):
    # fibo_pos slides each TP inside its own gap: 0 = base, 1 = full fibo
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
            tp1_fibo = 1.618 + fibo_pos  # 1.618-2.618
            tp2_fibo = 0.618 + fibo_pos  # 0.618-1.618
            tp3_fibo = 0 + fibo_pos  # 0-0.618
            tps = [
                (tp1_fibo, entry + ch_w * tp1_fibo if d == "BUY" else entry - ch_w * tp1_fibo),
                (tp2_fibo, entry + ch_w * tp2_fibo if d == "BUY" else entry - ch_w * tp2_fibo),
                (tp3_fibo, entry + ch_w * tp3_fibo if d == "BUY" else entry - ch_w * tp3_fibo),
            ]
            result.append((d, entry, tps, idx, ch_w))
            count += 1
    return result


def build_trade(candles, direction, entry, tps, idx, ch_w, trade_id):
    sl, parts = simulate_trade(candles, direction, entry, tps, idx, ch_w)
    risk = abs(entry - sl)
    return {
        "id": trade_id,
        "direction": direction,
        "entry_candle": idx,
        "entry": entry,
        "sl": sl,
        "risk": risk,
        "tps": [
            {"level": 1, "fibo": tps[0][0], "price": tps[0][1]},
            {"level": 2, "fibo": tps[1][0], "price": tps[1][1]},
            {"level": 3, "fibo": tps[2][0], "price": tps[2][1]},
        ],
        "parts": [
            {
                "tp_level": p["tp_level"],
                "tp": p["tp"],
                "exit": p["exit"],
                "exit_candle": p["exit_candle"],
                "hit": p["hit"],
                "profit": p["profit"],
            }
            for p in parts
        ],
        "total_profit": sum(p["profit"] for p in parts),
    }


if __name__ == "__main__":
    randomCandles = generateCandles(100, 60)

    for i in range(min(10, len(randomCandles))):
        print(f"Candle {i+1}: Open: {randomCandles[i][0]}, High: {randomCandles[i][1]}, Low: {randomCandles[i][2]}, Close: {randomCandles[i][3]}, Volume: {randomCandles[i][4]}, Timestamp: {randomCandles[i][5]}")
    print(f"... ({len(randomCandles)} candles total, 1m)")

    high, low, lowestHigh, highestHigh = candleHighLow(randomCandles)
    print(f"Highest: {high}, Lowest: {low}")
    print(f"Lowest High: {lowestHigh}, Highest High: {highestHigh}")

    zones, raw = analyzeSR(randomCandles)

    print("Channels (k=3+5, res+sup):")
    for hi, lo, score, body_mid in zones:
        print(f"  {lo} - {hi}  score={score}  body_mid={body_mid}")
    for k, (resC, supC) in raw.items():
        print(f"\nResistance channels (k={k}):")
        for hi, lo, score, body_mid in resC:
            print(f"  {lo} - {hi}  score={score}  body_mid={body_mid}")
        print(f"Support channels (k={k}):")
        for hi, lo, score, body_mid in supC:
            print(f"  {lo} - {hi}  score={score}  body_mid={body_mid}")

    longTrades, shortTrades = findSignals(randomCandles, zones)
    print(f"\nRaw: {len(longTrades)} long + {len(shortTrades)} short signals")

    trades = [
        build_trade(randomCandles, d, entry, tps, idx, ch_w, i + 1)
        for i, (d, entry, tps, idx, ch_w) in enumerate(select_trades(longTrades, shortTrades))
    ]

    print(f"\nTrades: {len(trades)}")
    for t in trades:
        print(f"\n  #{t['id']} {t['direction']}  entry_candle={t['entry_candle']}  entry={t['entry']}  sl={t['sl']}  risk={t['risk']}")
        print(f"    TP1(x{t['tps'][0]['fibo']})={t['tps'][0]['price']}  TP2(x{t['tps'][1]['fibo']})={t['tps'][1]['price']}  TP3(x{t['tps'][2]['fibo']})={t['tps'][2]['price']}")
        for p in t["parts"]:
            print(f"    Part {p['tp_level']}: tp={p['tp']}  {p['hit']}  exit={p['exit']}  candle={p['exit_candle']}  profit={'+' if p['profit']>0 else ''}{p['profit']}")
        print(f"    TOTAL PROFIT: {'+' if t['total_profit']>0 else ''}{t['total_profit']}")
    print(f"\nSUM: {'+' if sum(t['total_profit'] for t in trades)>0 else ''}{sum(t['total_profit'] for t in trades)}")
