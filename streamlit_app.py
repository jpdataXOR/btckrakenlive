import streamlit as st
import time
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit.components.v1 as components
from data_utils import get_stock_data, generate_future_projections
from pytz import timezone
from datetime import datetime

# Convert UTC time to AEST
def convert_to_aest(utc_time):
    aest = timezone("Australia/Sydney")
    return utc_time.astimezone(aest)

# Streamlit UI
st.set_page_config(page_title="Live Bitcoin Price", layout="wide")
st.title("📈 Live Bitcoin Price & Future Projections")

# UI Controls
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("**⏳ Refresh Interval:**")
    refresh_rate = st.radio("Choose refresh rate:", [15, 30, 900, 3600], format_func=lambda x: f"{x} sec" if x < 60 else f"{x//60} min", horizontal=True, index=0)

with col2:
    st.markdown("**🕒 Chart Interval:**")
    ohlc_interval = st.radio("Choose OHLC interval:", [1, 15, 60], format_func=lambda x: f"{x} min", horizontal=True, index=1)

with col3:
    st.markdown("**⏳ Next Refresh In:**")
    countdown_placeholder = st.empty()

with col4:
    latest_price_placeholder = st.empty()
    latest_time_placeholder = st.empty()

# Initialize session state
if "price_history" not in st.session_state:
    st.session_state.price_history = pd.DataFrame(columns=["date", "close"])

# Chart & Debug placeholders
placeholder_chart = st.empty()
placeholder_debug = st.empty()

# Main loop
while True:
    # Fetch latest OHLC data & projections
    stock_data = get_stock_data("XXBTZUSD", ohlc_interval)
    future_projections = generate_future_projections("XXBTZUSD", ohlc_interval)

    if not stock_data:
        debug_message = "**⚠ No new data received!**"
    else:
        st.session_state.price_history = stock_data.copy()

        latest_row = stock_data[-1]
        latest_price = latest_row["close"]
        latest_time = latest_row["date"]
        debug_message = f"📌 **Debug:** Latest Data → {latest_row}"

    # Display latest price
    with latest_price_placeholder:
        st.markdown(f"<h2 style='text-align: center; color: green;'>${latest_price:,.2f}</h2>", unsafe_allow_html=True)

    with latest_time_placeholder:
        st.markdown(f"<h3 style='text-align: center;'>🕒 {latest_time}</h3>", unsafe_allow_html=True)

    # Create step chart
    with placeholder_chart.container():
        fig = go.Figure()

        if stock_data:
            last_20_data = stock_data[-20:]

            fig.add_trace(go.Scatter(
                x=[item["date"] for item in last_20_data],
                y=[item["close"] for item in last_20_data],
                mode="lines",
                line=dict(shape="hv", color="black", width=2),
                name="Price",
            ))

            for proj in future_projections:
                fig.add_trace(go.Scatter(
                    x=[item["date"] for item in proj["data"]],
                    y=[item["close"] for item in proj["data"]],
                    mode="lines",
                    line=dict(shape="hv", dash="dot", color="red"),
                    name=proj["label"],
                ))

        fig.update_layout(title="Live Bitcoin Price with Future Predictions", xaxis_title="Time (AEST)", yaxis_title="Price (USD)", showlegend=True)

        st.plotly_chart(fig, use_container_width=True)

    # Show debug message
    with placeholder_debug.container():
        st.markdown(debug_message)

    # Update countdown timer
    for remaining in range(refresh_rate, 0, -1):
        countdown_placeholder.markdown(f"**{remaining} sec**", unsafe_allow_html=True)
        time.sleep(1)

    # Update browser tab
    components.html(f"<script>document.title = 'Live Bitcoin: ${latest_price:,.2f}';</script>", height=0)
