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
    utc_dt = datetime.strptime(utc_time, "%d-%b-%Y %H:%M")
    utc_dt = utc_dt.replace(tzinfo=timezone('UTC'))
    aest = timezone("Australia/Sydney")
    aest_time = utc_dt.astimezone(aest)
    return aest_time.strftime("%d-%b-%Y %H:%M")

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
    
# Initialize historical projections storage
if "historical_projections" not in st.session_state:
    st.session_state.historical_projections = []
    
# Set maximum number of historical projections to keep
MAX_HISTORICAL_PROJECTIONS = 5

# Chart & Debug placeholders
placeholder_chart = st.empty()
placeholder_debug = st.empty()

# Main loop
while True:
    # Fetch latest OHLC data & projections
    stock_data = get_stock_data("XXBTZUSD", ohlc_interval)
    new_projections = generate_future_projections("XXBTZUSD", ohlc_interval)
    
    # Add timestamp to the projections for tracking
    current_time = datetime.now()
    for proj in new_projections:
        proj["created_at"] = current_time
    
    # Add new projections to historical list
    if new_projections:
        st.session_state.historical_projections = [*new_projections, *st.session_state.historical_projections]
        # Limit the number of historical projections
        st.session_state.historical_projections = st.session_state.historical_projections[:MAX_HISTORICAL_PROJECTIONS]

    if not stock_data:
        debug_message = "**⚠ No new data received!**"
    else:
        st.session_state.price_history = stock_data.copy()

        latest_row = stock_data[-1]
        latest_price = latest_row["close"]
        latest_time = convert_to_aest(latest_row["date"])
        debug_message = f"📌 **Debug:** Latest Data → {latest_row}"

    # Display latest price
    with latest_price_placeholder:
        st.markdown(f"<h2 style='text-align: center; color: green;'>${latest_price:,.2f}</h2>", unsafe_allow_html=True)

    with latest_time_placeholder:
        st.markdown(f"<h3 style='text-align: center;'>🕒 {latest_time} AEST</h3>", unsafe_allow_html=True)

    # Create step chart
    with placeholder_chart.container():
        fig = go.Figure()

        if stock_data:
            last_20_data = stock_data[-20:]

            fig.add_trace(go.Scatter(
                x=[convert_to_aest(item["date"]) for item in last_20_data],
                y=[item["close"] for item in last_20_data],
                mode="lines",
                line=dict(shape="hv", color="black", width=2),
                name="Price",
            ))

            # Display historical projections with fading colors
            for idx, proj in enumerate(st.session_state.historical_projections):
                # Calculate opacity based on age (newer = more opaque)
                age_seconds = (datetime.now() - proj["created_at"]).total_seconds()
                max_age_seconds = refresh_rate * MAX_HISTORICAL_PROJECTIONS
                opacity = max(0.1, 1 - (age_seconds / max_age_seconds))
                
                # Newest projection is red, older ones fade to gray
                if idx == 0:
                    # Newest projection is red
                    color = f"rgba(255,0,0,{opacity})"
                    name = f"{proj['label']} (Current)"
                else:
                    # Older projections are increasingly gray
                    gray_value = int(120 * (1 - opacity))
                    color = f"rgba({gray_value},{gray_value},{gray_value},{opacity})"
                    name = f"{proj['label']} (Past {idx}, {int(opacity*100)}%)"
                
                # Only show if still has some visibility
                if opacity > 0.1:
                    fig.add_trace(go.Scatter(
                        x=[convert_to_aest(item["date"]) for item in proj["data"]],
                        y=[item["close"] for item in proj["data"]],
                        mode="lines",
                        line=dict(shape="hv", dash="dot", color=color),
                        name=name,
                    ))

        fig.update_layout(
            title="Live Bitcoin Price with Future Predictions", 
            xaxis_title="Time (AEST)", 
            yaxis_title="Price (USD)", 
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)

    # Show debug message
    with placeholder_debug.container():
        st.markdown(debug_message)
        st.markdown(f"**Historical Projections:** {len(st.session_state.historical_projections)}")

    # Update countdown timer
    for remaining in range(refresh_rate, 0, -1):
        countdown_placeholder.markdown(f"**{remaining} sec**", unsafe_allow_html=True)
        time.sleep(1)

    # Update browser tab
    components.html(f"<script>document.title = 'Live Bitcoin: ${latest_price:,.2f}';</script>", height=0)