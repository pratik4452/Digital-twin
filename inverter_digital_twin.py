import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ----- Config -----
st.set_page_config(page_title="Advanced Digital Twin", layout="wide")
st.sidebar.title("Solar Digital Twin Dashboard")

# ----- Sidebar Navigation -----
section = st.sidebar.radio("Navigation", ["Upload Data", "Overview", "Performance", "Digital Twin", "Alerts"])

# ----- File Uploads -----
st.sidebar.subheader("Step 1: Upload Data")
inverter_files = st.sidebar.file_uploader("Upload Inverter CSV(s)", type="csv", accept_multiple_files=True)
weather_file = st.sidebar.file_uploader("Upload Weather CSV", type="csv")

# ----- Parameter Inputs -----
st.sidebar.subheader("Step 2: Parameters")
gamma = st.sidebar.number_input("Temp Coefficient (gamma)", value=-0.004, step=0.001)
inv_eff = st.sidebar.slider("Inverter Efficiency", min_value=0.85, max_value=1.0, value=0.95)

# Placeholder for inverter DC capacity entry
dc_capacities = {}

# ----- Process Data -----
if inverter_files and weather_file:
    weather_df = pd.read_csv(weather_file, parse_dates=["Time"]).set_index("Time")
    all_data = []

    for file in inverter_files:
        inv_name = file.name.replace(".csv", "")
        df = pd.read_csv(file, parse_dates=["Time"]).set_index("Time")

        # Prompt user for inverter DC capacity
        dc_capacity = st.sidebar.number_input(f"{inv_name} DC Capacity (W)", value=6000, step=100)
        dc_capacities[inv_name] = dc_capacity

        # Merge with weather
        merged = df.join(weather_df, how="inner", rsuffix="_weather")
        merged["Expected_AC_Power"] = (
            dc_capacity * (merged["Irradiance"] / 1000) *
            (1 + gamma * (merged["Module_Temp"] - 25)) * inv_eff
        )
        merged["Deviation (%)"] = 100 * (merged["P_ac"] - merged["Expected_AC_Power"]) / merged["Expected_AC_Power"].replace(0, 1)
        merged["Status"] = merged["Deviation (%)"].apply(lambda x: "OK" if abs(x) < 10 else "Alert")
        merged["Inverter"] = inv_name

        all_data.append(merged)

    df_all = pd.concat(all_data)

    # ----- Overview -----
    if section == "Overview":
        st.title("Plant Overview")
        st.metric("Total Inverters", len(inverter_files))
        st.metric("Total Data Points", len(df_all))
        st.metric("Date Range", f"{df_all.index.min().date()} to {df_all.index.max().date()}")

        st.write("Sample Data")
        st.dataframe(df_all.head())

    # ----- Performance -----
    elif section == "Performance":
        st.title("Performance Metrics")
        st.markdown("**Key Performance Indicators per Inverter**")
        results = []
        dt_hours = (df_all.index[1] - df_all.index[0]).total_seconds() / 3600

        for inv in df_all["Inverter"].unique():
            sub = df_all[df_all["Inverter"] == inv]
            actual_energy = sub["P_ac"].sum() * dt_hours
            theoretical_energy = dc_capacities[inv] * (sub["Irradiance"] / 1000).sum() * dt_hours
            total_time = len(sub) * dt_hours
            PR = actual_energy / theoretical_energy if theoretical_energy > 0 else np.nan
            CUF = actual_energy / (dc_capacities[inv] * total_time) if total_time > 0 else np.nan
            results.append({"Inverter": inv, "PR": round(PR, 3), "CUF": round(CUF, 3)})

        st.dataframe(pd.DataFrame(results).set_index("Inverter"))

    # ----- Digital Twin -----
    elif section == "Digital Twin":
        st.title("Digital Twin View")
        inv_sel = st.selectbox("Select Inverter", df_all["Inverter"].unique())
        twin = df_all[df_all["Inverter"] == inv_sel]

        st.plotly_chart(px.line(twin, x=twin.index, y=["P_ac", "Expected_AC_Power"],
                                title=f"Actual vs Expected AC Power – {inv_sel}"), use_container_width=True)

        st.plotly_chart(px.line(twin, x=twin.index, y="Deviation (%)",
                                title="Deviation (%)", labels={"Deviation (%)": "Deviation %"}), use_container_width=True)

    # ----- Alerts -----
    elif section == "Alerts":
        st.title("Alerts & Fault Detection")
        alert_df = df_all[df_all["Status"] == "Alert"]
        st.warning(f"{len(alert_df)} alerts found.")
        st.dataframe(alert_df[["Inverter", "P_ac", "Expected_AC_Power", "Deviation (%)"]].tail(20))

else:
    if section != "Upload Data":
        st.warning("Please upload inverter and weather data to proceed.")
