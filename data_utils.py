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

    # Original function logic remains for compatibility
    stock_data.reverse()
    result_string = ''.join(['U' if stock_data[i]["close"] >= stock_data[i - 1]["close"] else 'D'
                             for i in range(1, len(stock_data))])

    index_dict = {}
    # Fixed to always use pattern length of 6
    length = 6
    string_to_match = result_string[:length]
    matches = [match.start() for match in re.finditer(string_to_match, result_string)]
    if len(matches) > 2:
        for matched_index in matches[1:]:
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

def generate_future_projections_from_point(stock_data, start_idx, future_points=10, num_lines=1):
    """
    Generate projections starting from a specific point in the price history.
    Always uses exactly 6 data points for pattern matching.
    
    Args:
        stock_data: Full price history data
        start_idx: Index in stock_data to start the projection from
        future_points: Number of points to project into the future
        num_lines: Number of projection lines to generate
    
    Returns:
        List of projection dictionaries
    """
    if not stock_data or start_idx >= len(stock_data):
        return []
    
    # Fixed pattern length of 6
    PATTERN_LENGTH = 6
    
    # Check if we have enough data for a 6-point pattern
    if start_idx < PATTERN_LENGTH:
        return []  # Not enough historical data for a 6-point pattern
    
    # Get data up to the starting point (we'll search for patterns in this data)
    data_subset = stock_data[:start_idx+1]
    
    # Create pattern string (U for up, D for down)
    # Always use exactly 6 points before the start_idx
    pattern_data = data_subset[-PATTERN_LENGTH-1:]
    
    result_string = ''.join(['U' if pattern_data[i+1]["close"] >= pattern_data[i]["close"] else 'D'
                            for i in range(len(pattern_data)-1)])
    
    # Find pattern matches in the full dataset - always using exactly 6 points
    index_dict = {}
    if len(result_string) >= PATTERN_LENGTH:
        string_to_match = result_string[-PATTERN_LENGTH:]
        # Create a string to search in (excluding the current pattern)
        search_string = ''.join(['U' if stock_data[i]["close"] >= stock_data[i-1]["close"] else 'D'
                                for i in range(1, len(stock_data)-PATTERN_LENGTH)])
        
        matches = [match.start() for match in re.finditer(string_to_match, search_string)]
        if len(matches) > 1:
            for matched_index in matches:
                if matched_index not in index_dict and matched_index + PATTERN_LENGTH < start_idx:
                    index_dict[matched_index] = PATTERN_LENGTH
    
    # Get the specific point we're starting from
    start_point = stock_data[start_idx]
    start_close = start_point["close"]
    start_date = datetime.strptime(start_point["date"], "%d-%b-%Y %H:%M")
    
    # Generate projections
    future_projections = []
    for key in list(index_dict.keys())[:num_lines]:
        future_prices = [start_close]
        future_dates = [start_date]
        
        # Get price changes from historical pattern
        for i in range(future_points):
            pattern_idx = key + PATTERN_LENGTH + i
            if pattern_idx + 1 < len(stock_data):
                price_change = (stock_data[pattern_idx]["close"] - stock_data[pattern_idx+1]["close"]) / stock_data[pattern_idx+1]["close"]
                future_prices.append(future_prices[-1] * (1 + price_change))
                
                # Calculate future dates based on the interval between data points
                if i > 0:
                    # Determine the interval from the data
                    curr_date = datetime.strptime(stock_data[0]["date"], "%d-%b-%Y %H:%M")
                    next_date = datetime.strptime(stock_data[1]["date"], "%d-%b-%Y %H:%M")
                    delta = next_date - curr_date
                    future_dates.append(future_dates[-1] + delta)
                else:
                    # For the first projection point, use the interval from data if available
                    if start_idx + 1 < len(stock_data):
                        next_date = datetime.strptime(stock_data[start_idx+1]["date"], "%d-%b-%Y %H:%M")
                        future_dates.append(next_date)
                    else:
                        # Fallback to estimating interval
                        if len(stock_data) > 1:
                            date1 = datetime.strptime(stock_data[-2]["date"], "%d-%b-%Y %H:%M")
                            date2 = datetime.strptime(stock_data[-1]["date"], "%d-%b-%Y %H:%M")
                            interval_minutes = (date2 - date1).total_seconds() / 60
                            future_dates.append(future_dates[-1] + timedelta(minutes=interval_minutes))
                        else:
                            # Default to 60 minutes if we can't determine
                            future_dates.append(future_dates[-1] + timedelta(hours=1))
        
        # Format the projection data
        future_line = [{"date": future_dates[i].strftime("%d-%b-%Y %H:%M"), "close": future_prices[i]} for i in range(len(future_prices))]
        match_point = f"{start_idx}/{len(stock_data)}"
        
        # Include pattern length in the returned data
        future_projections.append({
            "label": f"Projection from point {match_point}", 
            "data": future_line,
            "pattern_length": PATTERN_LENGTH
        })
    
    return future_projections