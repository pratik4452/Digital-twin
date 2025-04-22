import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

# ---------- Config ----------
st.set_page_config(page_title="Solar Digital Twin Dashboard", layout="wide")

# ---------- Sidebar ----------
st.sidebar.title("Solar Digital Twin Dashboard")
selected_section = st.sidebar.radio("Go to", ["Overview", "Performance", "Digital Twin", "Alerts", "Predictions"])

# ---------- Plant Info ----------
plant_info = {
    "Plant Name": "Sunil Kumar Dubey",
    "Location": "Village Deori, Sagar, MP",
    "Capacity": "2.0 MW AC / 2.4 MWp DC",
    "Panels": "Pahal TOPCon 600 Wp (G2G)",
    "Inverters": "Sungrow (String Type)"
}

# ---------- Dummy Data ----------
@st.cache_data
def generate_dummy_data():
    date_rng = pd.date_range(start=datetime.now() - timedelta(days=7), end=datetime.now(), freq='15T')
    df = pd.DataFrame(date_rng, columns=['timestamp'])
    df['irradiance'] = np.random.uniform(200, 1000, size=len(df))
    df['module_temp'] = np.random.uniform(30, 60, size=len(df))
    df['dc_power'] = df['irradiance'] * 2.4 * 0.8 / 1000  # Simplified
    df['ac_power_expected'] = df['dc_power'] * 0.96
    df['ac_power_actual'] = df['ac_power_expected'] * np.random.uniform(0.95, 1.05, size=len(df))
    df['fault_flag'] = np.random.choice([0, 1], size=len(df), p=[0.98, 0.02])
    return df

data = generate_dummy_data()

# ---------- Overview Section ----------
if selected_section == "Overview":
    st.title("Plant Overview")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Capacity", plant_info["Capacity"])
        st.metric("Panels", plant_info["Panels"])
        st.metric("Inverters", plant_info["Inverters"])
    with col2:
        st.metric("Location", plant_info["Location"])
        st.metric("Plant Name", plant_info["Plant Name"])
        st.metric("Last Updated", datetime.now().strftime("%Y-%m-%d %H:%M"))

    st.markdown("### Today's Generation")
    today_data = data[data['timestamp'].dt.date == datetime.now().date()]
    fig_today = px.line(today_data, x='timestamp', y='ac_power_actual', title='AC Power Output (Today)')
    st.plotly_chart(fig_today, use_container_width=True)

# ---------- Performance Section ----------
elif selected_section == "Performance":
    st.title("Performance Analysis")
    recent = data[data['timestamp'] > datetime.now() - timedelta(days=3)]

    col1, col2 = st.columns(2)
    with col1:
        pr = (recent['ac_power_actual'].sum() / recent['irradiance'].sum()) * 100
        st.metric("Performance Ratio (PR)", f"{pr:.2f} %")
    with col2:
        cuf = (recent['ac_power_actual'].sum() / (2.0 * 24 * 3)) * 100
        st.metric("Capacity Utilization Factor (CUF)", f"{cuf:.2f} %")

    st.markdown("### Expected vs Actual AC Power")
    fig_perf = px.line(recent, x='timestamp', y=['ac_power_expected', 'ac_power_actual'],
                       labels={'value': 'AC Power (kW)', 'timestamp': 'Time'}, title="Expected vs Actual AC Power")
    st.plotly_chart(fig_perf, use_container_width=True)

# ---------- Digital Twin Section ----------
elif selected_section == "Digital Twin":
    st.title("Digital Twin Simulation")

    st.markdown("**Live Overlay: Actual vs Model Output**")
    twin_data = data[data['timestamp'] > datetime.now() - timedelta(hours=6)]

    fig_twin = px.line(twin_data, x='timestamp', y=['ac_power_expected', 'ac_power_actual'],
                       title='Digital Twin Live Output', labels={'value': 'AC Power (kW)'})
    st.plotly_chart(fig_twin, use_container_width=True)

    deviation = (twin_data['ac_power_actual'] - twin_data['ac_power_expected']) / twin_data['ac_power_expected'] * 100
    fig_dev = px.line(x=twin_data['timestamp'], y=deviation, title="Deviation % (Actual vs Expected)")
    fig_dev.update_yaxes(title_text="Deviation (%)")
    st.plotly_chart(fig_dev, use_container_width=True)

# ---------- Alerts Section ----------
elif selected_section == "Alerts":
    st.title("Alert & Fault Logs")

    fault_data = data[data['fault_flag'] == 1]
    st.warning(f"{len(fault_data)} faults detected in the last 7 days.")

    if not fault_data.empty:
        st.dataframe(fault_data[['timestamp', 'ac_power_actual', 'fault_flag']].tail(20))

        fig_faults = px.scatter(fault_data, x='timestamp', y='ac_power_actual',
                                title='Fault Events - AC Power at Time of Fault',
                                color='fault_flag')
        st.plotly_chart(fig_faults, use_container_width=True)
    else:
        st.success("No faults detected.")

# ---------- Predictions Section ----------
elif selected_section == "Predictions":
    st.title("Predictive Maintenance")

    st.markdown("**Model Insight (Dummy ML Output)**")
    st.markdown("Potential degradation detected in last 3 days based on DC/AC mismatch.")

    pred_data = data[data['timestamp'] > datetime.now() - timedelta(days=3)]
    pred_data['predicted_deviation'] = (pred_data['ac_power_expected'] - pred_data['ac_power_actual']) / pred_data['ac_power_expected']

    st.line_chart(pred_data['predicted_deviation'])

    st.markdown("**Maintenance Suggestion:**")
    st.info("Check Inverter #2 - Deviation consistently >5% during peak hours.")

# ---------- Footer ----------
st.markdown("---")
st.caption("Developed by Pratik Khanorkar | v1.0 | Digital Twin Dashboard")
