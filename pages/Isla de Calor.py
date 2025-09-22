import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import os
import time

# ------------------- CONFIG -------------------
st.set_page_config(layout='wide', initial_sidebar_state='expanded')
st.title("Dashboard - Isla de Calor")
st.image("https://i.ibb.co/Q3RQT66R/SMT.png", caption=".")

# ------------------- AUTOREFRESH -------------------
st_autorefresh(interval=10000, limit=None, key="refresh_counter")  # recarga cada 10 segundos

# ------------------- RUTA CSV -------------------
csv_path = "Data/uplinks.csv"

# Mostrar debug para confirmar que se está leyendo el CSV correcto
if not os.path.exists(csv_path):
    st.error(f"El CSV no existe en la ruta: {os.path.abspath(csv_path)}")
else:
    st.write("CSV path:", os.path.abspath(csv_path))
    st.write("Última modificación del CSV:", pd.to_datetime(os.path.getmtime(csv_path), unit='s'))

# ------------------- LEER CSV -------------------
df = pd.read_csv(csv_path)
df['time'] = pd.to_datetime(df['time'], errors='coerce')

# ------------------- SIDEBAR -------------------
st.sidebar.header("Filtros")
sensors = df["deviceName"].unique()
selected_sensor = st.sidebar.selectbox("Seleccionar sensor", sensors)
df_sensor = df[df["deviceName"] == selected_sensor]

plot_data = st.sidebar.multiselect(
    "Seleccionar valores:",
    ['temperature', 'humidity', 'pressure_hPa'],
    ['temperature', 'humidity']
)

st.sidebar.markdown('---\nCreated by I2')

# ------------------- KPIs -------------------
latest = df_sensor.iloc[-1]
col1, col2, col3 = st.columns(3)
col1.metric("Temperatura", f"{latest['temperature']:.2f} °C")
col2.metric("Humedad", f"{latest['humidity']:.2f} %")
col3.metric("Presión", f"{latest['pressure_hPa']:.0f} hPa")

# ------------------- TABLA -------------------
st.markdown("### Últimos 10 registros")
df_table = df_sensor.drop(columns=["deviceName","battery_mV","rssi","snr"], errors='ignore')
st.dataframe(df_table.tail(10).iloc[::-1], use_container_width=True)

# ------------------- GAUGES -------------------
col1, col2 = st.columns(2)

with col1:
    fig_temp = go.Figure(go.Indicator(
        mode="gauge+number",
        value=latest['temperature'],
        title={'text': "Temperatura (°C)"},
        gauge={'axis': {'range': [0, 35]},
               'bar': {'color': "red", 'thickness': 1},
               'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 30}}
    ))
    st.plotly_chart(fig_temp, use_container_width=True)

with col2:
    fig_hum = go.Figure(go.Indicator(
        mode="gauge+number",
        value=latest['humidity'],
        title={'text': "Humedad (%)"},
        gauge={'axis': {'range': [0, 100]},
               'bar': {'color': "blue", 'thickness': 1},
               'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 80}}
    ))
    st.plotly_chart(fig_hum, use_container_width=True)

# ------------------- LINE CHART -------------------
st.markdown("### Line chart")
st.line_chart(df_sensor, x='time', y=plot_data, height=400)

# ------------------- TIMESTAMP STREAMLIT -------------------
st.markdown(f"Última actualización de Streamlit: {pd.Timestamp.now()}")


