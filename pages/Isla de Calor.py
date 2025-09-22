import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ------------------- CONFIGURACIÓN DE PÁGINA -------------------
st.set_page_config(layout='wide', initial_sidebar_state='expanded')
st.title("Dashboard - Isla de Calor")
st.image("https://i.ibb.co/Q3RQT66R/SMT.png", caption=".")

# ------------------- ESTILOS -------------------
with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# ------------------- AUTOREFRESH -------------------
st_autorefresh(interval=50000, limit=None, key="refresh_counter")  # 50s

# ------------------- CARGAR INFO DESDE GITHUB -------------------
csv_url = "https://raw.githubusercontent.com/smartcampusutp/SmartCampus_UTP/main/Data/uplinks.csv"
df = pd.read_csv(csv_url)
df['time'] = pd.to_datetime(df['time'], errors='coerce')

# ------------------- BARRA LATERAL -------------------
st.sidebar.header('Dashboard - UTP')

sensors = df["deviceName"].unique()
selected_sensor = st.sidebar.selectbox("Seleccionar sensor", sensors)
df_sensor = df[df["deviceName"] == selected_sensor]

plot_data = st.sidebar.multiselect(
    'Seleccionar valores:',
    ['temperature', 'humidity', 'pressure_hPa'],
    ['temperature', 'humidity']
)

st.sidebar.markdown('''---\nCreated by I2''')

# ------------------- INFORMACIÓN DE ÚLTIMA ACTUALIZACIÓN -------------------
latest = df.iloc[-1]
last_update_time = latest['time']

st.markdown(f"### 📅 Última actualización: **{last_update_time.strftime('%Y-%m-%d %H:%M:%S')}**")

# ------------------- KPIs -------------------
col1, col2, col3 = st.columns(3)
col1.metric("🌡️ Temperatura", f"{latest['temperature']:.2f} °C")
col2.metric("💧 Humedad", f"{latest['humidity']:.2f} %")
col3.metric("🌬️ Presión", f"{latest['pressure_hPa']:.0f} hPa")

# ------------------- TABLA DE ÚLTIMOS 10 VALORES -------------------
st.markdown("### 📊 Últimos 10 registros")
df_table = df.drop(columns=["deviceName", "battery_mV", "rssi", "snr"])
st.dataframe(df_table.tail(10).iloc[::-1], use_container_width=True)

# ------------------- GAUGES -------------------
col1, col2 = st.columns(2)

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

# ------------------- LI
