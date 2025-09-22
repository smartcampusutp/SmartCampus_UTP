import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import time

# ------------------- CONFIG -------------------
st.set_page_config(layout='wide', initial_sidebar_state='expanded')
st.title("Dashboard - Isla de Calor")
st.image("https://i.ibb.co/Q3RQT66R/SMT.png", caption=".")

# ------------------- ESTILO -------------------
with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# ------------------- AUTOREFRESH -------------------
st_autorefresh(interval=30000, limit=None, key="refresh_counter")  # cada 30s

# ------------------- FUNCION DE CARGA -------------------
def cargar_datos():
    url = "https://raw.githubusercontent.com/smartcampusutp/SmartCampus_UTP/main/Data/uplinks.csv"
    df = pd.read_csv(url + f"?t={int(time.time())}")  # timestamp para evitar cache
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    return df

df = cargar_datos()

# ------------------- BARRA DE SELECCIÓN -------------------
st.sidebar.header('Dashboard - UTP')
st.sidebar.header("Filtros")

sensors = df["deviceName"].unique()
selected_sensor = st.sidebar.selectbox("Seleccionar sensor", sensors)
df_sensor = df[df["deviceName"] == selected_sensor]

st.sidebar.subheader('Parámetros de visualización')
plot_data = st.sidebar.multiselect(
    'Seleccionar valores:',
    ['temperature', 'humidity', 'pressure_hPa'],
    ['temperature', 'humidity']
)

st.sidebar.markdown('''
---
Created by I2
''')

# ------------------- CUADRITOS KPI -------------------
st.markdown('### Última Actualización')
col1, col2, col3 = st.columns(3)
latest = df_sensor.iloc[-1]  # último valor del sensor seleccionado

col1.metric("Temperatura", f"{latest['temperature']:.2f} °C")
col2.metric("Humedad", f"{latest['humidity']:.2f} %")
col3.metric("Presión", f"{latest['pressure_hPa']:.0f} hPa")

# ------------------- TABLA DE ÚLTIMOS 10 VALORES -------------------
st.markdown("### Últimos 10 registros")
df_table = df_sensor.drop(columns=["deviceName","battery_mV", "rssi","snr"], errors='ignore')
st.dataframe(df_table.tail(10).iloc[::-1], use_container_width=True)

# ------------------- GRAFICOS -------------------
col1, col2 = st.columns(2)

# GAUGE TEMPERATURA
with col1:
    fig_temp = go.Figure(go.Indicator(
        mode="gauge+number",
        value=latest['temperature'],
        title={'text': "Temperatura (°C)"},
        gauge={
            'axis': {'range': [0, 35]},
            'bar': {'color': "red", 'thickness': 1},
            'threshold' : {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 30}}
    ))
    st.plotly_chart(fig_temp, use_container_width=True)

# GAUGE HUMEDAD
with col2:
    fig_hum = go.Figure(go.Indicator(
        mode="gauge+number",
        value=latest['humidity'],
        title={'text': "Humedad (%)"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "blue", 'thickness': 1},
            'threshold' : {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 80}}
    ))
    st.plotly_chart(fig_hum, use_container_width=True)

# GRAFICO TEMP/HUMEDAD LINE CHART
st.markdown('### Line chart')
st.line_chart(df_sensor, x='time', y=plot_data, height=400)
