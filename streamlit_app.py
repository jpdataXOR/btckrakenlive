import streamlit as st
import requests
import pandas as pd
import time
import plotly.graph_objects as go
from pytz import timezone
import streamlit.components.v1 as components

# Convert UTC time to AEST
def convert_to_aest(utc_time):
    aest = timezone("Australia/Sydney")
    return utc_time.astimezone(aest)

# Fetch OHLC Data with Rate Limit Handling
def fetch_ohlc_data(interval, retries=3, backoff_factor=5):
    url = f"https://api.kraken.com/0/public/OHLC?pair=BTCUSD&interval={interval}"
    attempt = 0
    
    while attempt < retries:
        response = requests.get(url)
        try:
            data = response.json()
            
            # Check for API Rate Limit Errors
            if "error" in data and data["error"]:
                error_msg = data["error"][0]
                
                if "EAPI:Rate limit exceeded" in error_msg:
                    wait_time = backoff_factor * (2 ** attempt)  # Exponential backoff
                    st.warning(f"⚠ Rate Limit Exceeded! Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    attempt += 1
                    continue  # Retry
                
                return None, f"⚠ Kraken API Error: {error_msg}"

            if "result" not in data:
                return None, "⚠ API Response Missing 'result' Key!"

            # Extract OHLC data
            ohlc_data = data["result"].get("XXBTZUSD", [])
            if not ohlc_data:
                return None, "⚠ No Data Available from API!"

            # Convert to DataFrame
            df = pd.DataFrame(ohlc_data, columns=["Timestamp", "Open", "High", "Low", "Close", "Vwap", "Volume", "Trades"])
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], unit="s", utc=True)
            df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
            df.dropna(subset=["Close"], inplace=True)
            df["Timestamp"] = df["Timestamp"].apply(convert_to_aest)

            return df, None  # No error

        except Exception as e:
            return None, f"⚠ Exception: {str(e)}"

    return None, "⚠ Maximum Retry Attempts Reached!"

# Streamlit UI setup
st.set_page_config(page_title="Live Bitcoin Price", layout="wide")

# Title
st.title("📈 Live Bitcoin Price from Kraken")

# UI Controls (Compact layout with 4 columns)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("**⏳ Refresh Interval:**")
    refresh_rate = st.radio(
        "Choose refresh rate:", 
        [15, 30, 900, 3600],  # Removed 5s, added 15s as default
        format_func=lambda x: f"{x} sec" if x < 60 else f"{x//60} min", 
        horizontal=True,
        index=0  # Default: 15 seconds
    )

with col2:
    st.markdown("**🕒 Chart Interval:**")
    ohlc_interval = st.radio(
        "Choose OHLC interval:", 
        [1, 15, 60], 
        format_func=lambda x: f"{x} min", 
        horizontal=True,
        index=1  # Default: 15 minutes
    )

with col3:
    st.markdown("**⏳ Next Refresh In:**")
    countdown_placeholder = st.empty()

with col4:
    latest_price_placeholder = st.empty()
    latest_time_placeholder = st.empty()

# Initialize session state
if "price_history" not in st.session_state:
    st.session_state.price_history = pd.DataFrame(columns=["Timestamp", "Close"])

# Chart & Debug placeholders
placeholder_chart = st.empty()
placeholder_debug = st.empty()

# Main loop
while True:
    # Fetch latest data with rate-limit handling
    new_data, error_message = fetch_ohlc_data(ohlc_interval)

    if error_message:
        debug_message = error_message  # Show API error
    elif new_data is None or new_data.empty:
        debug_message = "**⚠ No new data received!**"
    else:
        # Update session history
        st.session_state.price_history = new_data.copy()
        
        # Latest price and timestamp
        latest_row = new_data.iloc[-1]
        latest_price = latest_row["Close"]
        latest_time = latest_row["Timestamp"]
        debug_message = f"📌 **Debug:** Latest Data → {latest_row.to_dict()}"

    # Display latest price in the 4th column
    with latest_price_placeholder:
        st.markdown(
            f"<h2 style='text-align: center; color: green;'>${latest_price:,.2f}</h2>" if new_data is not None else "<h2 style='text-align: center; color: red;'>No Data</h2>",
            unsafe_allow_html=True,
        )

    with latest_time_placeholder:
        st.markdown(
            f"<h3 style='text-align: center;'>🕒 {latest_time.strftime('%Y-%m-%d %H:%M:%S')}</h3>" if new_data is not None else "<h3 style='text-align: center;'>No Time</h3>",
            unsafe_allow_html=True,
        )

    # Create step chart
    with placeholder_chart.container():
        fig = go.Figure()

        if new_data is not None and not new_data.empty:
            # Step line for Close prices
            fig.add_trace(
                go.Scatter(
                    x=new_data["Timestamp"],
                    y=new_data["Close"],
                    mode="lines",
                    line=dict(shape="hv", color="black", width=2),  # Step line
                    name="Price",
                )
            )

            # Latest price dot with label
            fig.add_trace(
                go.Scatter(
                    x=[latest_time],
                    y=[latest_price],
                    mode="markers+text",
                    marker=dict(size=10, color="red"),
                    name="Latest",
                    text=[f"${latest_price:,.2f}"],
                    textposition="top center",
                )
            )

        # Layout
        fig.update_layout(
            title="Live Bitcoin Price",
            xaxis_title="Time (AEST)",
            yaxis_title="Price (USD)",
            template="plotly_dark",
            showlegend=False,
        )

        # Plot chart
        st.plotly_chart(fig, use_container_width=True)

    # Show debug message below chart
    with placeholder_debug.container():
        st.markdown(debug_message)

    # Update countdown timer
    for remaining in range(refresh_rate, 0, -1):
        countdown_placeholder.markdown(f"**{remaining} sec**", unsafe_allow_html=True)
        time.sleep(1)

    # Update browser tab title
    if new_data is not None:
        components.html(f"""
            <script>
                document.title = 'Live Bitcoin Price: ${latest_price:,.2f}';
            </script>
        """, height=0)
