import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ------------------- CONFIG -------------------
st.set_page_config(layout='wide', initial_sidebar_state='expanded')
st.title("Dashboard - Isla de Calor")
st.image("https://i.ibb.co/Q3RQT66R/SMT.png", caption=".")

# ------------------- ESTILO -------------------
with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# ------------------- AUTOREFRESH -------------------
st_autorefresh(interval=50000, limit=None, key="refresh_counter")  # cada 50 segundos

# ------------------- CARGAR CSV -------------------
df = pd.read_csv("Data/uplinks.csv")
df['time'] = pd.to_datetime(df['time'], errors='coerce')

# ------------------- FILTRAR SOLO NODOTEST -------------------
df_sensor = df[df["deviceName"] == "NodoTest"]

# ------------------- SIDEBAR -------------------
st.sidebar.header("Dashboard - UTP")
st.sidebar.subheader('Parámetros de visualización')
plot_data = st.sidebar.multiselect(
    'Seleccionar valores:',
    ['temperature', 'humidity', 'pressure_hPa'],
    ['temperature', 'humidity']
)
st.sidebar.markdown('''---\nCreated by I2''')

# ------------------- KPIs -------------------
st.markdown('### Última Actualización')
latest = df_sensor.iloc[-1]  # último valor de NodoTest
col1, col2, col3 = st.columns(3)
col1.metric("Temperatura", f"{latest['temperature']:.2f} °C")
col2.metric("Humedad", f"{latest['humidity']:

