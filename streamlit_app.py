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

# Initialize session state for first run tracking
if "is_first_run" not in st.session_state:
    st.session_state.is_first_run = True

# Initialize session state
if "price_history" not in st.session_state:
    st.session_state.price_history = pd.DataFrame(columns=["date", "close"])
    
# Initialize historical projections storage - empty on first run
if "historical_projections" not in st.session_state:
    st.session_state.historical_projections = []

# Initialize to track refresh groups    
if "refresh_count" not in st.session_state:
    st.session_state.refresh_count = 0
    
# Set maximum number of historical projection groups to keep
MAX_HISTORICAL_GROUPS = 5

# Chart & Debug placeholders
placeholder_chart = st.empty()
placeholder_debug = st.empty()

# Main loop
while True:
    # Fetch latest OHLC data & projections
    stock_data = get_stock_data("XXBTZUSD", ohlc_interval)
    new_projections = generate_future_projections("XXBTZUSD", ohlc_interval)
    
    # Tag this batch of projections with the current refresh count
    current_time = datetime.now()
    refresh_group = st.session_state.refresh_count
    
    for proj in new_projections:
        proj["created_at"] = current_time
        proj["refresh_group"] = refresh_group
    
    # Handle projections storage
    if new_projections:
        if st.session_state.is_first_run:
            # On first run, only keep the current projections
            st.session_state.historical_projections = new_projections
            st.session_state.is_first_run = False
        else:
            # On subsequent runs, append new projections to history
            st.session_state.historical_projections = [*new_projections, *st.session_state.historical_projections]
            
        # Increment refresh count for next batch
        st.session_state.refresh_count += 1
        
        # Keep only projections from the most recent MAX_HISTORICAL_GROUPS refreshes
        groups_to_keep = set()
        projections_to_keep = []
        
        for proj in st.session_state.historical_projections:
            if len(groups_to_keep) < MAX_HISTORICAL_GROUPS or proj["refresh_group"] in groups_to_keep:
                projections_to_keep.append(proj)
                groups_to_keep.add(proj["refresh_group"])
                
        st.session_state.historical_projections = projections_to_keep

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

            # Get the current (newest) refresh group
            current_group = st.session_state.refresh_count - 1 if not st.session_state.is_first_run else 0
            
            # Display all projections
            for proj in st.session_state.historical_projections:
                # Calculate opacity based on age of the projection group
                group_age = current_group - proj["refresh_group"]
                max_age = MAX_HISTORICAL_GROUPS - 1
                opacity = max(0.1, 1 - (group_age / max_age))
                
                # Current projections are red, older groups are gray
                if proj["refresh_group"] == current_group:
                    # For current group (multiple projections), use red with varying intensity
                    color = f"rgba(255,0,0,{opacity})"
                    name = f"{proj['label']} (Current)"
                else:
                    # Older projections are increasingly light gray
                    gray_value = int(180 + (40 * (1 - opacity)))
                    color = f"rgba({gray_value},{gray_value},{gray_value},{opacity})"
                    age_text = "Previous" if group_age == 1 else f"{group_age} refreshes ago"
                    name = f"{proj['label']} ({age_text})"
                
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
        if not st.session_state.is_first_run:
            total_projections = len(st.session_state.historical_projections)
            unique_groups = len(set(p["refresh_group"] for p in st.session_state.historical_projections))
            st.markdown(f"**Historical Projections:** {total_projections} across {unique_groups} refresh groups")

    # Update countdown timer
    for remaining in range(refresh_rate, 0, -1):
        countdown_placeholder.markdown(f"**{remaining} sec**", unsafe_allow_html=True)
        time.sleep(1)

    # Update browser tab
    components.html(f"<script>document.title = 'Live Bitcoin: ${latest_price:,.2f}';</script>", height=0)