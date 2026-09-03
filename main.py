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
