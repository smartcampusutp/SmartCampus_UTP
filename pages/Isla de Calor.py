import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import altair as alt
import time

st.set_page_config(layout='wide', initial_sidebar_state='expanded')
st.title("Dashboard - Isla de Calor")
st.image("https://i.ibb.co/Q3RQT66R/SMT.png", caption=".")

# ------------------- CSS -------------------
try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("⚠️ No se encontró style.css, se usará estilo por defecto.")

# ------------------- AUTOREFRESH -------------------
st_autorefresh(interval=50000, limit=None, key="refresh_counter")

# ------------------- CARGA DE DATOS -------------------
@st.cache_data
def load_data():
    start = time.time()
    # ⚡ TIP: Cambiar a parquet para más velocidad
    try:
        df = pd.read_parquet("Data/uplinks.parquet")
    except FileNotFoundError:
        df = pd.read_csv("Data/uplinks.csv")
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    st.write(f"⏱️ Tiempo de carga: {time.time()-start:.2f} s")
    return df

df = load_data()

# Filtrar solo NodoTest al inicio (optimiza downstream)
df = df[df["deviceName"] == "NodoTest"]

# ------------------- SIDEBAR -------------------
st.sidebar.header('Dashboard - UTP')
st.sidebar.header("Filtros")

if "deviceName" in df.columns:
    sensors = df["deviceName"].unique()
    selected_sensor = st.sidebar.selectbox("Seleccionar sensor", sensors)
    df_sensor = df[df["deviceName"] == selected_sensor]
else:
    st.sidebar.warning("⚠️ No se encontró columna 'deviceName'.")
    df_sensor = df

st.sidebar.subheader('Parámetros de visualización')
plot_data = st.sidebar.multiselect(
    'Seleccionar valores:',
    ['temperature', 'humidity', 'pressure_hPa'],
    ['temperature', 'humidity']
)

st.sidebar.markdown("---\nCreated by I2")

# ------------------- KPI -------------------
st.markdown('### Última Actualización')
col1, col2, col3 = st.columns(3)

if not df.empty:
    # Precomputado para evitar ordenar cada vez
    latest = df.iloc[df['time'].idxmax()]
    col1.metric("Temperatura", f"{latest['temperature']:.2f} °C")
    col2.metric("Humedad", f"{latest['humidity']:.2f} %")
    col3.metric("Presión", f"{latest['pressure_hPa']:.0f} hPa")
else:
    st.warning("No hay datos en el CSV.")

# ------------------- TABLA -------------------
st.markdown("### Últimos registros (máx 500)")
if not df.empty:
    df_table = df.drop(columns=["deviceName","battery_mV", "rssi","snr"])
    st.dataframe(df_table.tail(500).iloc[::-1], use_container_width=True)
else:
    st.info("Esperando datos...")

# ------------------- GRÁFICOS -------------------
col1, col2 = st.columns(2)

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

# ------------------- LINE CHART -------------------
st.markdown('### Evolución temporal')
if not df.empty:
    # ⚡ Para velocidad, limitar puntos a últimos 5000
    df_plot = df.tail(5000)
    st.line_chart(df_plot, x='time', y=plot_data, height=400)

