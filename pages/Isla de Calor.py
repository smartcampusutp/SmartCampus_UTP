import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

st.set_page_config(layout='wide', initial_sidebar_state='expanded')
st.title("Dashboard - Isla de Calor")
st.image("https://i.ibb.co/Q3RQT66R/SMT.png", caption=".")

# ---------- ESTILO ----------
with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# ---------- AUTOREFRESH ----------
st_autorefresh(interval=30000, limit=None, key="refresh_counter")

# ---------- CARGAR INFO DESDE GITHUB ----------
csv_url = "https://raw.githubusercontent.com/TU_USUARIO/TU_REPO/main/Data/uplinks.csv"

@st.cache_data(ttl=30)  # cache solo 30 s para forzar actualización
def load_data():
    df = pd.read_csv(csv_url)
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    return df

df = load_data()

# ---------- SIDEBAR ----------
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

st.sidebar.markdown('''---\nCreated by I2''')

# ---------- KPI ----------
st.markdown('### Última Actualización')
col1, col2, col3 = st.columns(3)

latest = df.iloc[-1]  # último registro de todo el CSV
col1.metric("Temperatura", f"{latest['temperature']:.2f} °C")
col2.metric("Humedad", f"{latest['humidity']:.2f} %")
col3.metric("Presión", f"{latest['pressure_hPa']:.0f} hPa")

# ---------- TABLA ----------
st.markdown("### Últimos 10 registros")
df_table = df.drop(columns=["deviceName","battery_mV","rssi","snr"])
st.dataframe(df_table.tail(10).iloc[::-1], use_container_width=True)

# ---------- GAUGES ----------
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

# ---------- GRAFICO ----------
st.markdown('### Line chart')
st.line_chart(df, x='time', y=plot_data, height=400)

# ---------- DEBUG (opcional) ----------
st.caption(f"Último dato cargado: {latest['time']}")

