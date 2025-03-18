import streamlit as st
import requests
import pandas as pd
import time
import plotly.graph_objects as go
from pytz import timezone
import streamlit.components.v1 as components

# Convert UTC time to Australian Eastern Standard Time (AEST)
def convert_to_aest(utc_time):
    aest = timezone("Australia/Sydney")
    return utc_time.astimezone(aest)

# Function to fetch OHLC data from Kraken
def fetch_ohlc_data(interval):
    url = f"https://api.kraken.com/0/public/OHLC?pair=BTCUSD&interval={interval}"
    response = requests.get(url)
    data = response.json()
    
    # Extract OHLC data
    ohlc_data = data["result"]["XXBTZUSD"]
    df = pd.DataFrame(ohlc_data, columns=["Timestamp", "Open", "High", "Low", "Close", "Vwap", "Volume", "Trades"])
    
    # Convert data types
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], unit="s", utc=True)
    df["Close"] = df["Close"].astype(float)  # Ensure Close is a float
    df["Timestamp"] = df["Timestamp"].apply(convert_to_aest)  # Convert to AEST
    
    return df

# Streamlit UI setup
st.set_page_config(page_title="Live Bitcoin Price", layout="wide")

# Title
st.title("📈 Live Bitcoin Price from Kraken")

# UI Controls (Compact layout)
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**⏳ Refresh Interval:**")
    refresh_rate = st.radio(
        "Choose refresh rate:", 
        [5, 30, 900, 3600], 
        format_func=lambda x: f"{x} sec" if x < 60 else f"{x//60} min", 
        horizontal=True,
        index=0  # Default: 5 seconds
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

# Initialize session state
if "price_history" not in st.session_state:
    st.session_state.price_history = pd.DataFrame(columns=["Timestamp", "Close"])

# Chart and data placeholders
placeholder_chart = st.empty()
placeholder_price = st.empty()
placeholder_table = st.empty()

# Main loop
while True:
    # Fetch latest data
    new_data = fetch_ohlc_data(ohlc_interval)
    
    # Update session history
    st.session_state.price_history = new_data.copy()
    
    # Latest price and timestamp
    latest_price = float(new_data["Close"].iloc[-1])
    latest_time = new_data["Timestamp"].iloc[-1]

    # Display latest price
    with placeholder_price.container():
        st.markdown(
            f"<h2 style='text-align: center;'>Latest Price: <span style='color: green;'>${latest_price:,.2f}</span></h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<h3 style='text-align: center;'>Time: {latest_time.strftime('%Y-%m-%d %H:%M:%S')}</h3>",
            unsafe_allow_html=True,
        )

    # Create step chart
    with placeholder_chart.container():
        fig = go.Figure()

        # Step line for Close prices
        fig.add_trace(
            go.Scatter(
                x=st.session_state.price_history["Timestamp"],
                y=st.session_state.price_history["Close"],
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

    # Live table
    with placeholder_table.container():
        st.markdown("### 🔥 Recent Prices")
        st.dataframe(
            st.session_state.price_history.sort_values("Timestamp", ascending=False).head(20),
            height=300,
        )

    # Update countdown timer
    for remaining in range(refresh_rate, 0, -1):
        countdown_placeholder.markdown(f"**{remaining} sec**", unsafe_allow_html=True)
        time.sleep(1)

    # Update browser tab title
    components.html(f"""
        <script>
            document.title = 'Live Bitcoin Price: ${latest_price:,.2f}';
        </script>
    """, height=0)
