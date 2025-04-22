import streamlit as st
import pandas as pd
import numpy as np
import json
from io import BytesIO

# ----- Constants -----
PDC0 = 6000         # Rated DC capacity per inverter (W)
GAMMA = -0.004      # Temp coefficient of power (per °C)
INV_EFF = 0.95      # Assumed inverter efficiency

# ----- Streamlit Page Setup -----
st.set_page_config(layout="wide")
st.title("Digital Twin – Multi‑Inverter Performance Monitoring")

# ----- Optional Uploads -----
with st.sidebar.expander("Optional: Upload Metadata & Weather"):
    metadata_file = st.file_uploader("Plant Metadata (JSON)", type="json")
    weather_file = st.file_uploader("Weather Data CSV", type="csv")

# Display Metadata Panel
if metadata_file:
    try:
        meta = json.load(metadata_file)
        with st.expander("Plant Info", expanded=True):
            st.markdown(f"**Plant Name:** {meta.get('plant_name', 'N/A')}")
            st.markdown(f"**Location:** {meta.get('location', 'N/A')}")
            st.markdown(f"**Capacity:** {meta.get('capacity', 'N/A')}")
            st.markdown(f"**Inverters:** {meta.get('inverters', 'N/A')}")
    except:
        st.warning("Metadata JSON is invalid.")

# Optional Weather Preview
if weather_file:
    try:
        weather_df = pd.read_csv(weather_file)
        st.expander("Preview Weather Data").dataframe(weather_df.head())
    except:
        st.warning("Weather file is not valid.")

# ----- Main File Upload (Multiple Inverters) -----
uploaded_files = st.file_uploader(
    "Upload Inverter CSV File(s)",
    type="csv",
    accept_multiple_files=True
)

if uploaded_files:
    # Load all files into dict of DataFrames
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

    # ----- Global Date‑Range Picker -----
    all_mins = [df.index.min().date() for df in dfs.values()]
    all_maxs = [df.index.max().date() for df in dfs.values()]
    min_date = min(all_mins)
    max_date = max(all_maxs)
    start_date, end_date = st.date_input(
        "Select date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    if isinstance(start_date, tuple):
        start_date, end_date = start_date

    # Process each inverter
    processed = []
    for name, df in dfs.items():
        df = df.loc[(df.index.date >= start_date) & (df.index.date <= end_date)].copy()
        if df.empty:
            continue

        df["Expected_AC_Power"] = (
            PDC0 * (df["Irradiance"] / 1000) * (1 + GAMMA * (df["Module_Temp"] - 25)) * INV_EFF
        )
        df["Deviation (%)"] = 100 * (df["P_ac"] - df["Expected_AC_Power"]) / df["Expected_AC_Power"].replace(0, 1)
        df["Status"] = df["Deviation (%)"].apply(lambda x: "OK" if abs(x) < 10 else "Alert")
        df["Inverter"] = name
        processed.append(df)

    if not processed:
        st.warning("No data in the selected date range.")
        st.stop()

    df_all = pd.concat(processed)

    # ----- Multi‑Inverter Comparison -----
    inverter_names = df_all["Inverter"].unique().tolist()
    selected = st.multiselect("Select Inverters to Compare", inverter_names, default=inverter_names)

    if selected:
        df_sel = df_all[df_all["Inverter"].isin(selected)]

        # Pivot for actual power
        actual_pivot = df_sel.pivot_table(index=df_sel.index, columns="Inverter", values="P_ac")
        if not actual_pivot.empty:
            st.subheader("Actual AC Power Comparison")
            st.line_chart(actual_pivot)
        else:
            st.warning("No data available for AC Power Comparison.")

        # Pivot for deviation
        dev_pivot = df_sel.pivot_table(index=df_sel.index, columns="Inverter", values="Deviation (%)")
        if not dev_pivot.empty:
            st.subheader("Deviation (%) Comparison")
            st.line_chart(dev_pivot)
        else:
            st.warning("No data available for Deviation (%) Comparison.")
    else:
        st.warning("Please select at least one inverter to compare.")

    # ----- KPI Table -----
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
    kpi_df = pd.DataFrame(kpi_list).set_index("Inverter")
    st.subheader("Key Performance Indicators")
    st.dataframe(kpi_df)

    # ----- Alerts Table -----
    alerts = df_all[df_all["Status"] == "Alert"]
    st.subheader(f"Total Alerts: {len(alerts)}")
    if not alerts.empty:
        st.dataframe(alerts[["Inverter", "P_ac", "Expected_AC_Power", "Deviation (%)"]])
    else:
        st.success("No alerts in selected period.")

    # ----- Download Processed Data -----
    def convert_df(df):
        return df.to_csv(index=True).encode("utf-8")

    csv_all = convert_df(df_all)
    st.download_button("Download Full Processed Data", csv_all, "inverter_data_processed.csv", "text/csv")

    if not alerts.empty:
        csv_alerts = convert_df(alerts)
        st.download_button("Download Alerts Only", csv_alerts, "inverter_alerts.csv", "text/csv")

else:
    st.info("Please upload one or more inverter CSV files to begin.")
