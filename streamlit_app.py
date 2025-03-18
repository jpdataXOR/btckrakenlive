import streamlit as st
import requests
import pandas as pd
import time
import plotly.graph_objects as go
import streamlit.components.v1 as components

# Kraken API for OHLC data
KRAKEN_OHLC_URL = "https://api.kraken.com/0/public/OHLC"
PAIR = "BTCUSD"
INTERVAL = 1  # 1-minute OHLC data

# Streamlit UI setup
st.set_page_config(page_title="Live Bitcoin OHLC", layout="wide")
st.title("Live Bitcoin OHLC Close Prices (Step Chart)")
st.markdown("Streaming OHLC data via Kraken API.")

# Debug Status
status_placeholder = st.empty()
chart_placeholder = st.empty()
price_placeholder = st.empty()

refresh_rate = 2  # Fetch data every 2 seconds
max_data_points = 50  # Keep last 50 points to reduce memory load

# Initialize session state for OHLC history
if "ohlc_data" not in st.session_state:
    st.session_state.ohlc_data = pd.DataFrame(columns=["Time", "Close"])

# Function to fetch OHLC data
def fetch_ohlc_data():
    try:
        params = {"pair": PAIR, "interval": INTERVAL}
        response = requests.get(KRAKEN_OHLC_URL, params=params, timeout=5)  # Add timeout for reliability
        response.raise_for_status()  # Raise exception for HTTP errors

        data = response.json()
        ohlc = data.get("result", {}).get("XXBTZUSD", [])
        
        if not ohlc:
            return None  # No data received, return None

        # Convert to DataFrame and get close prices
        df = pd.DataFrame(ohlc, columns=["Time", "Open", "High", "Low", "Close", "Vwap", "Volume", "Trades"])
        df["Time"] = pd.to_datetime(df["Time"], unit="s")
        df["Close"] = df["Close"].astype(float)
        return df[["Time", "Close"]]
    
    except requests.exceptions.RequestException as e:
        status_placeholder.error(f"⚠️ API Error: {e}")
        return None  # Return None on error

# Main loop
while True:
    status_placeholder.text("🔄 Fetching latest OHLC data...")
    
    new_data = fetch_ohlc_data()
    
    if new_data is not None and not new_data.equals(st.session_state.ohlc_data.tail(len(new_data))):
        # Merge new data, avoid duplicates
        st.session_state.ohlc_data = pd.concat([st.session_state.ohlc_data, new_data]).drop_duplicates(subset="Time")

        # Keep last N data points
        st.session_state.ohlc_data = st.session_state.ohlc_data.tail(max_data_points)

        # Get latest price
        latest_time = st.session_state.ohlc_data["Time"].iloc[-1]
        latest_price = st.session_state.ohlc_data["Close"].iloc[-1]

        # Update latest price display
        with price_placeholder.container():
            st.markdown(f"<h2 style='text-align: center;'>Latest Close: <span style='color: green;'>${latest_price:,.2f}</span></h2>",
                        unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: center;'>Time: {latest_time}</h3>", unsafe_allow_html=True)

        # Update step chart
        with chart_placeholder.container():
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=st.session_state.ohlc_data["Time"],
                y=st.session_state.ohlc_data["Close"],
                mode="lines+markers",
                line=dict(shape="hv", color="black", width=2),
                marker=dict(size=8, color="black"),
                name="OHLC Close"
            ))

            fig.update_layout(
                title="Bitcoin OHLC Close Price (Step Chart)",
                xaxis_title="Time",
                yaxis_title="Price (USD)",
                template="plotly_dark",
                showlegend=False
            )

            st.plotly_chart(fig, use_container_width=True)

        # Update browser tab title dynamically
        components.html(f"""
            <script>
                document.title = 'BTC/USD: ${latest_price:,.2f}';
            </script>
        """, height=0)

        status_placeholder.text("✅ Data updated successfully!")

    else:
        status_placeholder.text("⚠️ No new data. Waiting for next fetch...")

    time.sleep(refresh_rate)  # Avoid excessive API calls
