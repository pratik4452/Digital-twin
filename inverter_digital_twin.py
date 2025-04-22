import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

# ---------- Config ----------
st.set_page_config(page_title="Solar Digital Twin Dashboard", layout="wide")

# ---------- App Title ----------
st.title("Solar Digital Twin Dashboard")

# ---------- Upload Data ----------
uploaded_files = st.file_uploader("Upload Inverter CSV File(s)", type="csv", accept_multiple_files=True)

if uploaded_files:
    # ---------- Load Data ----------
    dfs = {}
    for file in uploaded_files:
        try:
            df = pd.read_csv(file, parse_dates=["Time"])
            df = df.set_index("Time")
            required = ["Irradiance", "Module_Temp", "V_dc", "I_dc", "P_ac"]
            if not all(col in df.columns for col in required):
                st.error(f"File {file.name} is missing columns: {set(required) - set(df.columns)}")
                continue
            dfs[file.name] = df
        except Exception as e:
            st.error(f"Error reading file {file.name}: {e}")

    if not dfs:
        st.warning("No valid files to process.")
        st.stop()

    # ---------- Sidebar Navigation ----------
    st.sidebar.title("Navigation")
    selected_section = st.sidebar.radio("Go to", ["Overview", "Performance", "Digital Twin", "Alerts", "Predictions"])

    # ---------- Combine All Data ----------
    PDC0 = 6000
    GAMMA = -0.004
    INV_EFF = 0.95

    processed = []
    for name, df in dfs.items():
        df["Expected_AC_Power"] = (
            PDC0 * (df["Irradiance"] / 1000) * (1 + GAMMA * (df["Module_Temp"] - 25)) * INV_EFF
        )
        df["Deviation (%)"] = 100 * (df["P_ac"] - df["Expected_AC_Power"]) / df["Expected_AC_Power"].replace(0, 1)
        df["Status"] = df["Deviation (%)"].apply(lambda x: "OK" if abs(x) < 10 else "Alert")
        df["Inverter"] = name
        df["timestamp"] = df.index
        processed.append(df)

    df_all = pd.concat(processed)

    # ---------- Overview ----------
    if selected_section == "Overview":
        st.subheader("Plant Overview")
        plant_info = {
            "Plant Name": "Sunil Kumar Dubey",
            "Location": "Village Deori, Sagar, MP",
            "Capacity": "2.0 MW AC / 2.4 MWp DC",
            "Panels": "Pahal TOPCon 600 Wp (G2G)",
            "Inverters": "Sungrow (String Type)"
        }

        col1, col2 = st.columns(2)
        with col1:
            for key, val in list(plant_info.items())[:3]:
                st.metric(key, val)
        with col2:
            for key, val in list(plant_info.items())[3:]:
                st.metric(key, val)

        st.markdown("### Today's Generation (Actual AC Power)")
        today_data = df_all[df_all["timestamp"].dt.date == datetime.now().date()]
        if not today_data.empty:
            fig_today = px.line(today_data, x='timestamp', y='P_ac', title='AC Power Output (Today)')
            st.plotly_chart(fig_today, use_container_width=True)
        else:
            st.info("No data available for today.")

    # ---------- Performance ----------
    elif selected_section == "Performance":
        st.subheader("Performance Analysis")
        last_3days = df_all[df_all["timestamp"] > datetime.now() - timedelta(days=3)]

        if not last_3days.empty:
            col1, col2 = st.columns(2)
            pr = (last_3days['P_ac'].sum() / (last_3days['Irradiance'].sum() * PDC0 / 1000)) * 100
            cuf = (last_3days['P_ac'].sum() / (PDC0 * 3 * 24)) * 100
            col1.metric("Performance Ratio (PR)", f"{pr:.2f} %")
            col2.metric("CUF", f"{cuf:.2f} %")

            st.markdown("### Expected vs Actual AC Power")
            fig_perf = px.line(last_3days, x='timestamp', y=['Expected_AC_Power', 'P_ac'],
                               labels={'value': 'AC Power (W)', 'timestamp': 'Time'},
                               title="Expected vs Actual AC Power")
            st.plotly_chart(fig_perf, use_container_width=True)
        else:
            st.info("Not enough data for performance analysis.")

    # ---------- Digital Twin ----------
    elif selected_section == "Digital Twin":
        st.subheader("Digital Twin Simulation")
        twin_data = df_all[df_all["timestamp"] > datetime.now() - timedelta(hours=6)]

        if not twin_data.empty:
            st.markdown("### Live Overlay: Actual vs Model Output")
            fig_twin = px.line(twin_data, x='timestamp', y=['Expected_AC_Power', 'P_ac'],
                               title='Digital Twin Live Output')
            st.plotly_chart(fig_twin, use_container_width=True)

            deviation = (twin_data['P_ac'] - twin_data['Expected_AC_Power']) / twin_data['Expected_AC_Power'] * 100
            fig_dev = px.line(x=twin_data['timestamp'], y=deviation, title="Deviation % (Actual vs Expected)")
            fig_dev.update_yaxes(title_text="Deviation (%)")
            st.plotly_chart(fig_dev, use_container_width=True)
        else:
            st.info("No recent data available for digital twin simulation.")

    # ---------- Alerts ----------
    elif selected_section == "Alerts":
        st.subheader("Alert & Fault Logs")
        alerts = df_all[df_all["Status"] == "Alert"]
        st.warning(f"{len(alerts)} alert(s) detected.")
        if not alerts.empty:
            st.dataframe(alerts[['timestamp', 'Inverter', 'P_ac', 'Expected_AC_Power', 'Deviation (%)']].tail(30))
        else:
            st.success("No alerts detected.")

    # ---------- Predictions ----------
    elif selected_section == "Predictions":
        st.subheader("Predictive Maintenance")
        pred_data = df_all[df_all['timestamp'] > datetime.now() - timedelta(days=3)]
        pred_data['predicted_deviation'] = (pred_data['Expected_AC_Power'] - pred_data['P_ac']) / pred_data['Expected_AC_Power']
        st.line_chart(pred_data['predicted_deviation'])

        st.markdown("**Maintenance Suggestion:**")
        st.info("Check Inverter(s) with consistently high deviation >5% during peak hours.")

    # ---------- Footer ----------
    st.markdown("---")
    st.caption("Developed by Pratik Kewat | Digital Twin Dashboard v1.0")

else:
    st.info("Please upload one or more inverter CSV files to begin.")
