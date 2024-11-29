import streamlit as st
import requests
import pandas as pd
import time
import plotly.graph_objects as go
from pytz import timezone
import streamlit.components.v1 as components

# Function to fetch live trade data from Kraken
def fetch_trade_data():
    url = "https://api.kraken.com/0/public/Trades?pair=BTCUSD"
    response = requests.get(url)
    data = response.json()
    trades = data["result"]["XXBTZUSD"]
    
    # Parse trades into a DataFrame
    trade_data = pd.DataFrame(
        [[float(trade[0]), trade[2]] for trade in trades],
        columns=["Price", "Timestamp"]
    )
    trade_data["Timestamp"] = pd.to_datetime(trade_data["Timestamp"], unit="s", utc=True)
    return trade_data

# Convert UTC time to Australian Eastern Standard Time (AEST)
def convert_to_aest(utc_time):
    aest = timezone("Australia/Sydney")
    return utc_time.astimezone(aest)

# Streamlit UI setup
st.set_page_config(page_title="Live Bitcoin Prices", layout="wide")

# Title and description
st.title("Live Bitcoin Prices")
st.markdown("Real-time Bitcoin trade data from Kraken, updated live.")

# Initialize session state for price history
if "price_history" not in st.session_state:
    st.session_state.price_history = pd.DataFrame(columns=["Price", "Timestamp"])

# Real-time update loop
placeholder_chart = st.empty()  # Placeholder for the chart
placeholder_price = st.empty()  # Placeholder for the latest price and time
placeholder_table = st.empty()  # Placeholder for the live table
refresh_rate = 2  # Refresh interval in seconds

# Main loop
while True:
    # Fetch the latest data
    new_data = fetch_trade_data()
    new_data["Timestamp"] = new_data["Timestamp"].apply(convert_to_aest)  # Convert to AEST
    st.session_state.price_history = pd.concat(
        [st.session_state.price_history, new_data], ignore_index=True
    ).drop_duplicates(subset="Timestamp")  # Ensure no duplicate timestamps

    # Update the latest price and time
    latest_price = st.session_state.price_history["Price"].iloc[-1]
    latest_time = st.session_state.price_history["Timestamp"].iloc[-1]

    # Display the latest price and time on top
    with placeholder_price.container():
        st.markdown(
            f"<h2 style='text-align: center;'>Latest Price: <span style='color: green;'>${latest_price:,.2f}</span></h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<h3 style='text-align: center;'>Time: {latest_time.strftime('%Y-%m-%d %H:%M:%S')}</h3>",
            unsafe_allow_html=True,
        )

    # Update the chart with a unique key based on current time
    with placeholder_chart.container():
        fig = go.Figure()

        # Plot all prices with a material black line
        fig.add_trace(
            go.Scatter(
                x=st.session_state.price_history["Timestamp"],
                y=st.session_state.price_history["Price"],
                mode="lines",
                line=dict(color="black", width=2),
                name="Price",
            )
        )

        # Highlight the latest price with a black dot
        fig.add_trace(
            go.Scatter(
                x=[latest_time],
                y=[latest_price],
                mode="markers+text",
                marker=dict(size=10, color="black"),
                name="Latest",
                text=f"${latest_price:,.2f}",
                textposition="top center",
            )
        )

        # Configure layout
        fig.update_layout(
            title="Live Bitcoin Price",
            xaxis_title="Time (AEST)",
            yaxis_title="Price (USD)",
            template="plotly_dark",
            showlegend=False,
        )

        # Add hover mode
        fig.update_traces(
            hovertemplate="Time: %{x}<br>Price: $%{y:,.2f}<extra></extra>"
        )

        # Using current time to generate a unique key for each chart
        chart_key = f"live_chart_{int(time.time())}"
        st.plotly_chart(fig, use_container_width=True, key=chart_key)

    # Update the live table
    with placeholder_table.container():
        st.markdown("### Live Prices Table")
        st.dataframe(
            st.session_state.price_history.sort_values("Timestamp", ascending=False).head(20),
            height=400,
        )

    # Dynamically update the browser tab title to show the latest price
    components.html(f"""
        <script>
            document.title = 'Live Bitcoin Price: ${latest_price:,.2f}';
        </script>
    """, height=0)

    # Wait for the next update
    time.sleep(refresh_rate)
