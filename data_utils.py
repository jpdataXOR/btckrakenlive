import requests
import pandas as pd
from datetime import datetime, timedelta
import re

KRAKEN_API_URL = "https://api.kraken.com/0/public/OHLC"

def get_stock_data(pair="XXBTZUSD", interval=60):
    response = requests.get(KRAKEN_API_URL, params={"pair": pair, "interval": interval})
    data = response.json()

    if "error" in data and data["error"]:
        print("Kraken API Error:", data["error"])
        return []

    if "result" not in data or pair not in data["result"]:
        print("Invalid API response structure.")
        return []

    ohlc_data = data["result"][pair]
    stock_data = [{
        "date": datetime.utcfromtimestamp(item[0]).strftime("%d-%b-%Y %H:%M"),
        "close": float(item[4])  
    } for item in ohlc_data]

    return stock_data

def generate_future_projections(pair="XXBTZUSD", interval=60, future_points=10, num_lines=3):
    stock_data = get_stock_data(pair, interval)
    if not stock_data:
        return []

    stock_data.reverse()
    result_string = ''.join(['U' if stock_data[i]["close"] >= stock_data[i - 1]["close"] else 'D'
                             for i in range(1, len(stock_data))])

    index_dict = {}
    for length in range(8, 5, -1):
        string_to_match = result_string[:length]
        matches = [match.start() for match in re.finditer(string_to_match, result_string)]
        if len(matches) > 2:
            for matched_index in matches[1:]:
                if matched_index not in index_dict:
                    index_dict[matched_index] = length

    last_close = stock_data[0]["close"]
    last_date = datetime.strptime(stock_data[0]["date"], "%d-%b-%Y %H:%M")

    future_projections = []
    for key in list(index_dict.keys())[:num_lines]:
        pattern_length = index_dict[key]
        future_prices = [last_close]
        future_dates = [last_date]

        for i in range(future_points):
            if key + i + 1 < len(stock_data):
                price_change = (stock_data[key + i]["close"] - stock_data[key + i + 1]["close"]) / stock_data[key + i + 1]["close"]
                future_prices.append(future_prices[-1] * (1 + price_change))

                if interval == 60:
                    future_dates.append(future_dates[-1] + timedelta(hours=1))
                elif interval == 1440:
                    future_dates.append(future_dates[-1] + timedelta(days=1))
                else:
                    future_dates.append(future_dates[-1] + timedelta(minutes=interval))

        future_line = [{"date": future_dates[i].strftime("%d-%b-%Y %H:%M"), "close": future_prices[i]} for i in range(len(future_prices))]
        match_date = datetime.strptime(stock_data[key]["date"], "%d-%b-%Y %H:%M")
        future_projections.append({"label": f"Projection (Match: {match_date.strftime('%d-%b-%Y')})", "data": future_line})

    return future_projections
