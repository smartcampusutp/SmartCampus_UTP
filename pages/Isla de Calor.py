import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import altair as alt

st.set_page_config(layout='wide', initial_sidebar_state='expanded')
st.title("Dashboard - Isla de Calor")
st.image("https://i.ibb.co/Q3RQT66R/SMT.png", caption=".")

# ESTILO CSS PARA QUE SE VEA BONITO
try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("⚠️ No se encontró style.css, se usará estilo por defecto.")

# AUTOREFRESH CADA CIERTO TIEMPO
st_autorefresh(interval=50000, limit=None, key="refresh_counter")

# ------------------- CARGAR INFO -------------------
@st.cache_data
def load_data():
    df = pd.read_csv("Data/uplinks.csv")
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    return df

df = load_data()
df = df[df["deviceName"] == "NodoTest"]  # 🔹 Filtrar SOLO los datos del NodoTest

# ------------------- BARRA DE SELECCIÓN -------------------
st.sidebar.header('Dashboard - UTP')

st.sidebar.header("Filtros")
if "deviceName" in df.columns:
    sensors = df["deviceName"].unique()
    selected_sensor = st.sidebar.selectbox("Seleccionar sensor", sensors)
    df_sensor = df[df["deviceName"] == selected_sensor]
else:
    st.sidebar.warning("⚠️ No se encontró columna 'deviceName' en el CSV.")
    df_sensor = df

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

if not df.empty:
    latest = df.sort_values("time").iloc[-1]  # usamos la más reciente por fecha
    col1.metric("Temperatura", f"{latest['temperature']:.2f} °C")
    col2.metric("Humedad", f"{latest['humidity']:.2f} %")
    col3.metric("Presión", f"{latest['pressure_hPa']:.0f} hPa")
else:
    st.warning("No hay datos en el CSV.")

# ------------------- TABLA SIN AG-GRID -------------------
st.markdown("### Últimos 10 registros")
if not df.empty:
    df_table = df.drop(columns=["deviceName","battery_mV", "rssi","snr"])   # Eliminar columna
    st.dataframe(df_table.tail(10).iloc[::-1], use_container_width=True)    # Mostrar
else:
    st.info("Esperando datos...")

# -------------------- GRAFICOS -------------------
col1, col2 = st.columns(2)

# ------------------ GAUGE TEMPERATURA ------------------
if not df.empty:
    with col1:
        fig_temp = go.Figure(go.Indicator(
            mode="gauge+number",
            value=latest['temperature'],
            title={'text': "Temperatura (°C)"},
            gauge={
                'axis': {'range': [0, 35]},
                'bar': {'color': "red", 'thickness': 1},
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 30}
            }
        ))
        st.plotly_chart(fig_temp, use_container_width=True)

    # ------------------ GAUGE HUMEDAD ------------------
    with col2:
        fig_hum = go.Figure(go.Indicator(
            mode="gauge+number",
            value=latest['humidity'],
            title={'text': "Humedad (%)"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "blue", 'thickness': 1},
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 80}
            }
        ))
        st.plotly_chart(fig_hum, use_container_width=True)


# ------------------- GRAFICO TEMP HUMEDAD -------------------
st.markdown('### Line chart')
if not df.empty:
    st.line_chart(df, x='time', y=plot_data, height=400)
