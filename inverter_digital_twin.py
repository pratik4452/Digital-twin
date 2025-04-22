# inverter_digital_twin_sidebar.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ----- Constants -----
PDC0 = 6000         # Rated DC capacity per inverter (W)
GAMMA = -0.004      # Temp coefficient of power (per °C)
INV_EFF = 0.95      # Assumed inverter efficiency

# ----- Streamlit Config -----
st.set_page_config(page_title="Digital Twin – Inverter Performance", layout="wide")

# ----- Sidebar Navigation -----
st.sidebar.title("Digital Twin Dashboard")
section = st.sidebar.radio("Go to", ["Overview", "Performance", "Digital Twin", "Alerts"])

# ----- File Upload (in Sidebar) -----
uploaded_files = st.sidebar.file_uploader(
    "Upload Inverter CSV File(s)",
    type="csv",
    accept_multiple_files=True
)

# ----- Plant Info -----
plant_info = {
    "Plant Name": "Sunil Kumar Dubey",
    "Location": "Village Deori, Sagar, MP",
    "Capacity": "2.0 MW AC / 2.4 MWp DC",
    "Panels": "Pahal TOPCon 600 Wp (G2G)",
    "Inverters": "Sungrow (String Type)"
}

if uploaded_files:
    dfs = {}
    for file in uploaded_files:
        try:
            df = pd.read_csv(file, parse_dates=["Time"])
            df = df.set_index("Time")
            required = ["Irradiance", "Module_Temp", "V_dc", "I_dc", "P_ac"]
            if not all(col in df.columns for col in required):
                st.error(f"File {file.name} missing columns: {set(required) - set(df.columns)}")
                continue
            dfs[file.name] = df
        except Exception as e:
            st.error(f"Error reading {file.name}: {e}")

    if not dfs:
        st.warning("No valid files to process.")
        st.stop()

    all_mins = [df.index.min().date() for df in dfs.values()]
    all_maxs = [df.index.max().date() for df in dfs.values()]
    min_date, max_date = min(all_mins), max(all_maxs)

    start_date, end_date = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    if isinstance(start_date, tuple): start_date, end_date = start_date

    # ----- Process Data -----
    processed = []
    for name, df in dfs.items():
        df = df.loc[(df.index.date >= start_date) & (df.index.date <= end_date)].copy()
        if df.empty: continue
        df["Expected_AC_Power"] = (
            PDC0 * (df["Irradiance"] / 1000) * (1 + GAMMA * (df["Module_Temp"] - 25)) * INV_EFF
        )
        df["Deviation (%)"] = 100 * (df["P_ac"] - df["Expected_AC_Power"]) / df["Expected_AC_Power"].replace(0, 1)
        df["Status"] = df["Deviation (%)"].apply(lambda x: "OK" if abs(x) < 10 else "Alert")
        df["Inverter"] = name
        processed.append(df)

    if not processed:
        st.warning("No data in selected range.")
        st.stop()

    df_all = pd.concat(processed)
    inverter_names = df_all["Inverter"].unique().tolist()
    selected = st.sidebar.multiselect("Select Inverters", inverter_names, default=inverter_names)

    df_sel = df_all[df_all["Inverter"].isin(selected)]

    # ----- Overview -----
    if section == "Overview":
        st.title("Plant Overview")
        col1, col2 = st.columns(2)
        with col1:
            for k in ["Plant Name", "Location", "Capacity"]:
                st.metric(k, plant_info[k])
        with col2:
            for k in ["Panels", "Inverters"]:
                st.metric(k, plant_info[k])
            st.metric("Date Range", f"{start_date} to {end_date}")

    # ----- Performance -----
    elif section == "Performance":
        st.title("Performance Comparison")
        if not df_sel.empty:
            actual_pivot = df_sel.pivot_table(index=df_sel.index, columns="Inverter", values="P_ac")
            dev_pivot = df_sel.pivot_table(index=df_sel.index, columns="Inverter", values="Deviation (%)")

            st.subheader("Actual AC Power Comparison")
            st.line_chart(actual_pivot)

            st.subheader("Deviation (%) Comparison")
            st.line_chart(dev_pivot)

    # ----- Digital Twin -----
    elif section == "Digital Twin":
        st.title("Digital Twin – Modeled vs Actual Output")

        for name in selected:
            st.subheader(f"Inverter: {name}")
            df_i = df_sel[df_sel["Inverter"] == name]
            fig = px.line(df_i, x=df_i.index, y=["P_ac", "Expected_AC_Power"], title="Expected vs Actual AC Power")
            st.plotly_chart(fig, use_container_width=True)

            fig_dev = px.line(df_i, x=df_i.index, y="Deviation (%)", title="Deviation (%) Over Time")
            st.plotly_chart(fig_dev, use_container_width=True)

    # ----- Alerts -----
    elif section == "Alerts":
        st.title("Alert Summary")
        alerts = df_all[df_all["Status"] == "Alert"]
        st.subheader(f"Total Alerts: {len(alerts)}")

        if not alerts.empty:
            st.dataframe(alerts[["Inverter", "P_ac", "Expected_AC_Power", "Deviation (%)"]])
            fig = px.scatter(alerts, x=alerts.index, y="Deviation (%)", color="Inverter", title="Alert Events")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("No alerts detected.")

    # ----- KPIs -----
    st.markdown("---")
    st.subheader("Key Performance Indicators")
    kpi_list = []
    dt_hours = (processed[0].index[1] - processed[0].index[0]).total_seconds() / 3600
    for name in inverter_names:
        df_i = df_all[df_all["Inverter"] == name]
        actual_energy = df_i["P_ac"].sum() * dt_hours
        theoretical_energy = PDC0 * (df_i["Irradiance"] / 1000).sum() * dt_hours
        total_time = len(df_i) * dt_hours
        PR = actual_energy / theoretical_energy if theoretical_energy > 0 else np.nan
        CUF = actual_energy / (PDC0 * total_time) if total_time > 0 else np.nan
        kpi_list.append({
            "Inverter": name,
            "PR": round(PR, 3),
            "CUF": round(CUF, 3)
        })
    st.dataframe(pd.DataFrame(kpi_list).set_index("Inverter"))

else:
    st.info("Please upload inverter CSV file(s) using the sidebar.")
