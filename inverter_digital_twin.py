# inverter_digital_twin.py

import streamlit as st
import pandas as pd
import numpy as np

# ----- Streamlit Page Setup -----
st.set_page_config(layout="wide")
st.title("Digital Twin – Inverter Performance Monitoring (PVLib‑free)")

# ----- File Upload Section -----
uploaded_file = st.file_uploader("Upload Inverter CSV File", type="csv")

if uploaded_file is not None:
    # Load & index
    df = pd.read_csv(uploaded_file, parse_dates=["Time"]).set_index("Time")

    # Check required columns
    required_cols = ["Irradiance", "Module_Temp", "V_dc", "I_dc", "P_ac"]
    if not all(col in df.columns for col in required_cols):
        st.error("Missing required columns. Required: " + ", ".join(required_cols))
    else:
        # ----- Simple expected AC power model -----
        # Pdc0: rated DC capacity (W)
        # gamma: temp coefficient (per °C)
        # inverter_eff: assumed constant
        Pdc0 = 6000       
        gamma = -0.004    
        inverter_eff = 0.95

        df["Expected_AC_Power"] = (
            Pdc0
            * (df["Irradiance"] / 1000)
            * (1 + gamma * (df["Module_Temp"] - 25))
            * inverter_eff
        )

        # ----- Deviation & Status -----
        df["Deviation (%)"] = 100 * (
            df["P_ac"] - df["Expected_AC_Power"]
        ) / df["Expected_AC_Power"].replace(0, 1)
        df["Status"] = df["Deviation (%)"].apply(
            lambda x: "OK" if abs(x) < 10 else "Alert"
        )

        # ----- Visualizations -----
        st.subheader("Power Comparison")
        st.line_chart(df[["P_ac", "Expected_AC_Power"]])

        st.subheader("Deviation (%)")
        st.bar_chart(df["Deviation (%)"])

        # Show alerts
        alerts = df[df["Status"] == "Alert"]
        st.subheader(f"Alerts Detected: {len(alerts)}")
        st.dataframe(alerts[["P_ac", "Expected_AC_Power", "Deviation (%)"]])

else:
    st.info("Please upload a CSV file to begin.")
