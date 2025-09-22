import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURACIÓN DE LA PÁGINA (Debe ser el primer comando de Streamlit) ---
st.set_page_config(layout='wide', initial_sidebar_state='expanded')

st.title("Dashboard - Isla de Calor")
st.image("https://i.ibb.co/Q3RQT66R/SMT.png", caption=".")

# --- ESTILO CSS (Opcional, asegúrate que el archivo style.css esté en tu repo) ---
try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("Archivo 'style.css' no encontrado. Se usará el estilo por defecto.")

# --- AUTOREFRESH CADA 50 SEGUNDOS ---
st_autorefresh(interval=50000, limit=None, key="refresh_counter")

# ------------------- CARGAR DATOS DESDE GITHUB -------------------
# Esta es la corrección principal: leer el CSV directamente desde la URL "raw".
url_csv = 'https://raw.githubusercontent.com/smartcampusutp/SmartCampus_UTP/main/Data/uplinks.csv'
try:
    df = pd.read_csv(url_csv)
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
except Exception as e:
    st.error(f"Error al cargar los datos desde GitHub: {e}")
    st.stop() # Detiene la ejecución si no se pueden cargar los datos

# ------------------- BARRA LATERAL DE SELECCIÓN -------------------
st.sidebar.header('Dashboard - UTP')
st.sidebar.header("Filtros")

# Aseguramos que la columna exista antes de crear el filtro
if "deviceName" in df.columns:
    sensors = df["deviceName"].unique()
    selected_sensor = st.sidebar.selectbox("Seleccionar sensor", sensors)
    # Filtramos el dataframe principal basado en la selección
    df_filtered_by_sensor = df[df["deviceName"] == selected_sensor]
else:
    st.sidebar.warning("La columna 'deviceName' no se encuentra en el CSV.")
    df_filtered_by_sensor = df # Si no hay columna, usamos el dataframe completo

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

# ------------------- MÉTRICAS (KPIs) -------------------
st.markdown('### Última Actualización')
col1, col2, col3 = st.columns(3)

# Verificamos que el dataframe no esté vacío para evitar errores
if not df.empty:
    latest = df.iloc[-1]  # Último valor global recibido
    col1.metric("Temperatura", f"{latest.get('temperature', 'N/A'):.2f} °C")
    col2.metric("Humedad", f"{latest.get('humidity', 'N/A'):.2f} %")
    col3.metric("Presión", f"{latest.get('pressure_hPa', 'N/A'):.0f} hPa")
else:
    col1.metric("Temperatura", "Sin datos")
    col2.metric("Humedad", "Sin datos")
    col3.metric("Presión", "Sin datos")

# ------------------- TABLA DE ÚLTIMOS 10 VALORES DEL SENSOR SELECCIONADO -------------------
st.markdown(f"### Últimos 10 registros del sensor: **{selected_sensor}**")

# Columnas a eliminar (si existen)
cols_to_drop = ["deviceName", "battery_mV", "rssi", "snr"]
df_table = df_filtered_by_sensor.drop(columns=[col for col in cols_to_drop if col in df_filtered_by_sensor.columns])

# Mostramos la tabla del sensor filtrado
st.dataframe(df_table.tail(10).iloc[::-1], use_container_width=True)

# -------------------- GRÁFICOS DE MEDIDOR (GAUGE) --------------------
# Usamos el último dato del sensor seleccionado para los medidores
if not df_filtered_by_sensor.empty:
    latest_sensor_data = df_filtered_by_sensor.iloc[-1]
    
    col1, col2 = st.columns(2)
    # GAUGE TEMPERATURA
    with col1:
        fig_temp = go.Figure(go.Indicator(
            mode="gauge+number",
            value=latest_sensor_data.get('temperature', 0),
            title={'text': "Temperatura (°C)"},
            gauge={
                'axis': {'range': [0, 40]},
                'bar': {'color': "#d62728"},
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 35}
            }
        ))
        st.plotly_chart(fig_temp, use_container_width=True)

    # GAUGE HUMEDAD
    with col2:
        fig_hum = go.Figure(go.Indicator(
            mode="gauge+number",
            value=latest_sensor_data.get('humidity', 0),
            title={'text': "Humedad (%)"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#1f77b4"},
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 80}
            }
        ))
        st.plotly_chart(fig_hum, use_container_width=True)

# ------------------- GRÁFICO DE LÍNEAS DEL SENSOR SELECCIONADO -------------------
st.markdown('### Histórico de datos')
# Graficamos solo los datos del sensor seleccionado
if not df_filtered_by_sensor.empty:
    st.line_chart(df_filtered_by_sensor, x='time', y=plot_data, height=400)
else:
    st.warning(f"No hay datos para mostrar para el sensor {selected_sensor}.")
