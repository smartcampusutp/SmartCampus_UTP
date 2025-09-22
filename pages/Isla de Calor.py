import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(layout='wide', initial_sidebar_state='expanded')
st.title("Dashboard - Isla de Calor")
st.image("https://i.ibb.co/Q3RQT66R/SMT.png", caption=".")

# --- ESTILO CSS OPCIONAL ---
try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("Archivo 'style.css' no encontrado. Se usará el estilo por defecto.")

# --- AUTOREFRESH CADA 1 MINUTO (60000 ms) ---
st_autorefresh(interval=60000, limit=None, key="refresh_counter")

# --- CARGAR DATOS DESDE GITHUB RAW ---
url_csv = "https://raw.githubusercontent.com/smartcampusutp/SmartCampus_UTP/main/Data/uplinks.csv"
try:
    df = pd.read_csv(url_csv)
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
except Exception as e:
    st.error(f"No se pudieron cargar los datos desde GitHub: {e}")
    st.stop()

# --- BARRA LATERAL DE SELECCIÓN ---
st.sidebar.header('Dashboard - UTP')
st.sidebar.header("Filtros")

if "deviceName" in df.columns:
    sensors = df["deviceName"].unique()
    selected_sensor = st.sidebar.selectbox("Seleccionar sensor", sensors)
    df_sensor = df[df["deviceName"] == selected_sensor]
else:
    st.sidebar.warning("Columna 'deviceName' no encontrada.")
    df_sensor = df

st.sidebar.subheader('Parámetros de visualización')
plot_data = st.sidebar.multiselect(
    'Seleccionar valores:',
    ['temperature', 'humidity', 'pressure_hPa'],
    ['temperature', 'humidity']
)
st.sidebar.markdown('---\nCreated by I2')

# --- KPIs ---
st.markdown('### Última Actualización')
col1, col2, col3 = st.columns(3)

if not df_sensor.empty:
    latest = df_sensor.iloc[-1]
    temp = latest.get('temperature')
    hum = latest.get('humidity')
    pres = latest.get('pressure_hPa')
    col1.metric("Temperatura", f"{temp:.2f} °C" if pd.notnull(temp) else "Sin datos")
    col2.metric("Humedad", f"{hum:.2f} %" if pd.notnull(hum) else "Sin datos")
    col3.metric("Presión", f"{pres:.0f} hPa" if pd.notnull(pres) else "Sin datos")
else:
    col1.metric("Temperatura", "Sin datos")
    col2.metric("Humedad", "Sin datos")
    col3.metric("Presión", "Sin datos")

# --- TABLA DE ÚLTIMOS 10 REGISTROS ---
st.markdown(f"### Últimos 10 registros del sensor: **{selected_sensor}**")
cols_to_drop = ["deviceName", "battery_mV", "rssi", "snr"]
df_table = df_sensor.drop(columns=[c for c in cols_to_drop if c in df_sensor.columns])
st.dataframe(df_table.tail(10).iloc[::-1], use_container_width=True)

# --- GRÁFICOS GAUGE ---
if not df_sensor.empty:
    latest_sensor = df_sensor.iloc[-1]
    col1, col2 = st.columns(2)

    # Temperatura
    with col1:
        fig_temp = go.Figure(go.Indicator(
            mode="gauge+number",
            value=latest_sensor.get('temperature', 0),
            title={'text': "Temperatura (°C)"},
            gauge={'axis': {'range': [0, 40]},
                   'bar': {'color': "#d62728"},
                   'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 35}}
        ))
        st.plotly_chart(fig_temp, use_container_width=True)

    # Humedad
    with col2:
        fig_hum = go.Figure(go.Indicator(
            mode="gauge+number",
            value=latest_sensor.get('humidity', 0),
            title={'text': "Humedad (%)"},
            gauge={'axis': {'range': [0, 100]},
                   'bar': {'color': "#1f77b4"},
                   'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 80}}
        ))
        st.plotly_chart(fig_hum, use_container_width=True)

# --- GRÁFICO DE LÍNEAS ---
st.markdown('### Histórico de datos')
if not df_sensor.empty:
    st.line_chart(df_sensor, x='time', y=plot_data, height=400)
else:
    st.warning(f"No hay datos para mostrar para el sensor {selected_sensor}.")
