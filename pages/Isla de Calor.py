import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import os

st.set_page_config(layout='wide', initial_sidebar_state='expanded')
st.title("Dashboard - Isla de Calor")

# ------------------- CONTENEDORES DINÁMICOS -------------------
table_container = st.empty()
gauge_temp_container = st.empty()
gauge_hum_container = st.empty()
line_chart_container = st.empty()

# ------------------- SIDEBAR -------------------
st.sidebar.header("Filtros")
plot_data = st.sidebar.multiselect(
    "Seleccionar valores:",
    ['temperature', 'humidity', 'pressure_hPa'],
    ['temperature', 'humidity']
)

# ------------------- LOOP DE REFRESCO -------------------
REFRESH_INTERVAL = 10  # segundos

while True:
    if os.path.exists("Data/uplinks.csv"):
        df = pd.read_csv("Data/uplinks.csv")
        df['time'] = pd.to_datetime(df['time'], errors='coerce')

        sensors = df["deviceName"].unique()
        selected_sensor = st.sidebar.selectbox("Seleccionar sensor", sensors)
        df_sensor = df[df["deviceName"] == selected_sensor]

        latest = df_sensor.iloc[-1]

        # ------------------- TABLA -------------------
        df_table = df_sensor.drop(columns=["deviceName","battery_mV","rssi","snr"], errors='ignore')
        table_container.dataframe(df_table.tail(10).iloc[::-1], use_container_width=True)

        # ------------------- GAUGES -------------------
        fig_temp = go.Figure(go.Indicator(
            mode="gauge+number",
            value=latest['temperature'],
            title={'text': "Temperatura (°C)"},
            gauge={'axis': {'range': [0, 35]},
                   'bar': {'color': "red", 'thickness': 1},
                   'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 30}}
        ))
        gauge_temp_container.plotly_chart(fig_temp, use_container_width=True)

        fig_hum = go.Figure(go.Indicator(
            mode="gauge+number",
            value=latest['humidity'],
            title={'text': "Humedad (%)"},
            gauge={'axis': {'range': [0, 100]},
                   'bar': {'color': "blue", 'thickness': 1},
                   'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 80}}
        ))
        gauge_hum_container.plotly_chart(fig_hum, use_container_width=True)

        # ------------------- LINE CHART -------------------
        line_chart_container.line_chart(df_sensor, x='time', y=plot_data, height=400)

    else:
        st.warning("El archivo Data/uplinks.csv no existe.")

    time.sleep(REFRESH_INTERVAL)
