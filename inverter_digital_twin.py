# inverter_digital_twin.py

import streamlit as st
import pandas as pd
import numpy as np
from pvlib.pvsystem import PVSystem
from pvlib.location import Location
from pvlib.modelchain import ModelChain

# ----- Streamlit Page Setup -----
st.set_page_config(layout="wide")
st.title("Digital Twin – Inverter Performance Monitoring")

# ----- File Upload Section -----
uploaded_file = st.file_uploader("Upload Inverter CSV File", type="csv")

if uploaded_file is not None:
    # Load and index
    df = pd.read_csv(uploaded_file, parse_dates=["Time"]).set_index("Time")

    # Check required columns
    required_cols = ["Irradiance", "Module_Temp", "V_dc", "I_dc", "P_ac"]
    if not all(col in df.columns for col in required_cols):
        st.error("Missing required columns. Required: " + ", ".join(required_cols))
    else:
        # ----- PVLib Model Setup with AOI/Spectral Disabled -----
        location = Location(latitude=23.83, longitude=78.72, tz="Asia/Kolkata")
        system = PVSystem(
            surface_tilt=20,
            surface_azimuth=180,
            module_parameters={"pdc0": 6000, "gamma_pdc": -0.004},
            inverter_parameters={"pdc0": 6000},
        )
        mc = ModelChain(
            system,
            location,
            aoi_model=None,        # skip AOI losses
            spectral_model=None    # skip spectral losses
        )

        # Prepare weather input
        weather = pd.DataFrame({
            "ghi": df["Irradiance"],
            "temp_air": df["Module_Temp"],
            "wind_speed": 1
        }, index=df.index)

        # Run the model
        mc.run_model(weather)
        df["Expected_AC_Power"] = mc.ac.fillna(0)

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
