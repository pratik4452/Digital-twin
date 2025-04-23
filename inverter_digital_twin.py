import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

# ---------- Page Config ----------
st.set_page_config(page_title="Solar Digital Twin Dashboard", layout="wide")

# ---------- Sidebar ----------
st.sidebar.title("Digital Twin Navigation")

# ---------- File Upload ----------
st.sidebar.markdown("### Step 1: Upload Inverter & Weather Data")
uploaded_file = st.sidebar.file_uploader("Upload CSV", type="csv")

# ---------- DC Capacity Input ----------
dc_capacity = st.sidebar.number_input("Enter Inverter DC Capacity (in Watts)", min_value=100.0, value=6000.0, step=100.0)

# Show main sections only after data is uploaded
if uploaded_file:

    # ---------- Load & Validate Data ----------
    try:
        df = pd.read_csv(uploaded_file, parse_dates=["Time"])
        df = df.set_index("Time")
        required_cols = ["Irradiance", "Module_Temp", "V_dc", "I_dc", "P_ac"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"Missing columns in uploaded file: {set(required_cols) - set(df.columns)}")
            st.stop()
    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.stop()

    # ---------- Constants ----------
    GAMMA = -0.004      # Temp coefficient
    INV_EFF = 0.95      # Inverter efficiency

    # ---------- Calculations ----------
    df["Expected_AC_Power"] = (
        dc_capacity * (df["Irradiance"] / 1000) * (1 + GAMMA * (df["Module_Temp"] - 25)) * INV_EFF
    )
    df["Deviation (%)"] = 100 * (df["P_ac"] - df["Expected_AC_Power"]) / df["Expected_AC_Power"].replace(0, 1)
    df["Status"] = df["Deviation (%)"].apply(lambda x: "OK" if abs(x) < 10 else "Alert")

    # ---------- Sidebar Navigation ----------
    section = st.sidebar.radio("Go to", ["Overview", "Performance", "Digital Twin", "Alerts", "KPIs"])

    # ---------- Overview ----------
    if section == "Overview":
        st.title("Plant Overview")
        st.markdown("### Latest Metrics")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Avg Irradiance", f"{df['Irradiance'].mean():.2f} W/m²")
            st.metric("Avg Module Temp", f"{df['Module_Temp'].mean():.2f} °C")
        with col2:
            st.metric("Avg AC Power", f"{df['P_ac'].mean():.2f} W")
            st.metric("AC Power Max", f"{df['P_ac'].max():.2f} W")

        st.markdown("### Irradiance Trend")
        st.line_chart(df["Irradiance"])

    # ---------- Performance ----------
    elif section == "Performance":
        st.title("Performance Analysis")
        st.markdown("### Expected vs Actual AC Power")
        fig = px.line(df, x=df.index, y=["P_ac", "Expected_AC_Power"],
                      labels={"value": "AC Power (W)", "Time": "Timestamp"},
                      title="Actual vs Expected AC Power")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Deviation Trend (%)")
        fig2 = px.line(df, x=df.index, y="Deviation (%)", title="Deviation Percentage")
        st.plotly_chart(fig2, use_container_width=True)

    # ---------- Digital Twin ----------
    elif section == "Digital Twin":
        st.title("Digital Twin View")
        st.markdown("Overlay of Model vs Actual Output")

        fig3 = px.line(df, x=df.index, y=["Expected_AC_Power", "P_ac"],
                       title="Digital Twin Output", labels={"value": "AC Power (W)"})
        st.plotly_chart(fig3, use_container_width=True)

        st.markdown("### Efficiency Over Time")
        df["Inverter_Efficiency (%)"] = 100 * df["P_ac"] / (df["V_dc"] * df["I_dc"]).replace(0, 1)
        fig_eff = px.line(df, x=df.index, y="Inverter_Efficiency (%)", title="Inverter Efficiency (%)")
        st.plotly_chart(fig_eff, use_container_width=True)

    # ---------- Alerts ----------
    elif section == "Alerts":
        st.title("Alert Logs")
        alert_df = df[df["Status"] == "Alert"]
        st.warning(f"Total Alerts: {len(alert_df)}")
        if not alert_df.empty:
            st.dataframe(alert_df[["Irradiance", "P_ac", "Expected_AC_Power", "Deviation (%)"]].tail(30))
        else:
            st.success("No alerts detected.")

    # ---------- KPIs ----------
    elif section == "KPIs":
        st.title("Key Performance Indicators")

        time_step = (df.index[1] - df.index[0]).total_seconds() / 3600
        actual_energy = df["P_ac"].sum() * time_step
        theoretical_energy = dc_capacity * (df["Irradiance"] / 1000).sum() * time_step
        total_time = len(df) * time_step
        PR = actual_energy / theoretical_energy if theoretical_energy > 0 else np.nan
        CUF = actual_energy / (dc_capacity * total_time) if total_time > 0 else np.nan

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Performance Ratio (PR)", f"{PR*100:.2f} %")
        with col2:
            st.metric("CUF", f"{CUF*100:.2f} %")

        st.success("KPIs calculated using only actual & weather data.")

# ---------- Footer ----------
else:
    st.title("Solar Digital Twin Dashboard")
    st.markdown("Please upload your inverter + weather data (CSV) to begin.")
    st.info("Required columns: `Time`, `Irradiance`, `Module_Temp`, `V_dc`, `I_dc`, `P_ac`")

st.markdown("---")
st.caption("Developed by Pratik Khanorkar | Digital Twin v2.0")

