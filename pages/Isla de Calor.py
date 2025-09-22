import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import time

st.set_page_config(layout='wide', initial_sidebar_state='expanded')
st.title("Dashboard - Isla de Calor")

# Auto-refresh cada 30s
st_autorefresh(interval=30000, limit=None, key="refresh_counter")

# Contenedor dinámico para todo el dashboard
dashboard_container = st.container()

# Función para cargar datos desde GitHub
def cargar_datos():
    url = "https://raw.githubusercontent.com/smartcampusutp/SmartCampus_UTP/main/Data/uplinks.csv"
    df = pd.read_csv(url + f"?t={int(time.time())}")
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    return df

# ------------------- BLOQUE PRINCIPAL -------------------
with dashboard_container:
    df = cargar_datos()

    # Sidebar
    st.sidebar.header("Filtros")
    sensors = df["deviceName"].unique()
    selected_sensor = st.sidebar.selectbox("Seleccionar sensor", sensors)
    df_sensor = df[df["deviceName"] == selected_sensor]

    plot_data = st.sidebar.multiselect(
        "Seleccionar valores:",
        ['temperature', 'humidity', 'pressure_hPa'],
        ['temperature', 'humidity']
    )

    # Últimos valores
    latest = df_sensor.iloc[-1]
    col1, col2, col3 = st.columns(3)
    col1.metric("Temperatura", f"{latest['temperature']:.2f} °C")
    col2.metric("Humedad", f"{latest['humidity']:.2f} %")
    col3.metric("Presión", f"{latest['pressure_hPa']:.0f} hPa")

    # Tabla últimos 10 registros
    st.markdown("### Últimos 10 registros")
    df_table = df_sensor.drop(columns=["deviceName","battery_mV","rssi","snr"], errors='ignore')
    st.dataframe(df_table.tail(10).iloc[::-1], use_container_width=True)

    # Gauges
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
                   'bar': {'color': "b
