import requests
import datetime
import pandas as pd

def get_klines(symbol, interval, start_time, end_time):
    url = "https://api.binance.com/api/v3/klines"
    limit = 1000  # максимум, который разрешает Binance
    klines = []
    while start_time < end_time:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time,
            "limit": limit
        }
        response = requests.get(url, params=params)
        data = response.json()
        if not data:
            break
        klines.extend(data)
        last_open_time = data[-1][0]
        start_time = last_open_time + 1
    return klines

def get_all_candles(symbol, interval, start_time_ms, end_time_ms):
    url = "https://api.binance.com/api/v3/klines"
    all_candles = []
    limit = 1000
    while start_time_ms < end_time_ms:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time_ms,
            "endTime": end_time_ms,
            "limit": limit
        }
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        candles = resp.json()
        if not candles:
            break
        all_candles.extend(candles)
        last_ts = candles[-1][0]
        start_time_ms = last_ts + 1
        if len(candles) < limit:
            break
    return all_candles

def get_fear_greed_history(limit=0):
    url = "https://api.alternative.me/fng/"
    params = {"limit": limit, "format": "json", "date_format": "world"}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json().get("data", [])

    result = {}
    for d in data:
        ts = d["timestamp"]
        if "-" in ts:  # если это дата, а не Unix timestamp
            try:
                dt = datetime.datetime.strptime(ts, "%d-%m-%Y")
            except ValueError:
                continue  # пропустить некорректную дату
        else:
            dt = datetime.datetime.fromtimestamp(int(ts), datetime.UTC)
        date_str = dt.strftime("%d.%m.%Y")
        result[date_str] = int(d["value"])
    return result


def main():
    symbol = input("Введите торговую пару (например, BTCUSDT): ").strip().upper()
    from_date = input("Дата с (DD.MM.YYYY): ").strip()
    to_date = input("Дата по (DD.MM.YYYY, Enter = вчера): ").strip()
    from_dt = datetime.datetime.strptime(from_date, "%d.%m.%Y")
    percent_str = input("Введите порог движения цены для SIGNAL в % (например, 5): ").strip()
    threshold = float(percent_str) / 100

    if to_date == "":
        to_dt = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)
        print(f"[i] Используется вчерашняя дата: {to_dt.strftime('%d.%m.%Y')}")
    else:
        to_dt = datetime.datetime.strptime(to_date, "%d.%m.%Y")

    # Генерация имени файла
    from_date_str = from_dt.strftime("%d%m%Y")
    to_date_str = to_dt.strftime("%d.%m.%Y")
    filename = f"{symbol}{from_date_str}_{to_date_str}.xlsx"

    # Получение временных меток
    start_ms = int(from_dt.timestamp() * 1000)
    end_ms = int(to_dt.timestamp() * 1000)

    # Получение данных свечей
    candles = get_klines(symbol, '1d', start_ms, end_ms)

    # Получение данных индекса страха и жадности
    fng_map = get_fear_greed_history()

    rows = []
    for c in candles:
        open_price = float(c[1])
        high_price = float(c[2])
        low_price = float(c[3])
        close_price = float(c[4])
        ts = c[0]
        date = datetime.datetime.fromtimestamp(ts / 1000, datetime.UTC).strftime('%d.%m.%Y')
        fng = fng_map.get(date, None)

        direction = "bullish" if close_price > open_price else "bearish"
        signal = "Signal" if direction == "bearish" and (
                    (open_price - low_price) / open_price) > threshold else "noSignal"

        rows.append({
            "date": date,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "direction": direction,
            "Signal": signal,
            "fear_greed": fng
        })

    df = pd.DataFrame(rows)
    df.to_excel(filename, index=False)
    print(f"\n✅ Сохранено {len(df)} строк в файл {filename}")

if __name__ == "__main__":
    main()
