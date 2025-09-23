import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import altair as alt
from st_aggrid import AgGrid, GridOptionsBuilder, AgGridDataReturn

st.title("Dashboard - Isla de Calor")
st.image("https://i.ibb.co/Q3RQT66R/SMT.png", caption=".")
st.set_page_config(layout='wide', initial_sidebar_state='expanded')

# ESTILO CSV PARA QUE SE VEA BONITO
with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# AUTOREFRESH CADA CIERTO TIEMPO
st_autorefresh(interval=50000, limit=None, key="refresh_counter")

# ------------------- CARGAR INFO -------------------
@st.cache_data
def load_data():
    # Cargar los datos solo una vez y almacenarlos en cache
    df = pd.read_csv("Data/uplinks.csv")  # <-- NOMBRE DEL CSV REAL
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    return df

df = load_data()

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

latest = df.iloc[-1]  # ULTIMO VALOR
col1.metric("Temperatura", f"{latest['temperature']:.2f} °C")
col2.metric("Humedad", f"{latest['humidity']:.2f} %")
col3.metric("Presión", f"{latest['pressure_hPa']:.0f} hPa")

# ------------------- AG-GRID PARA TABLA CON LA CARGA LAZY -------------------
st.markdown("### Últimos 10 registros (con Lazy Loading)")

# Filtramos las columnas innecesarias antes de pasar a AG-Grid
df_table = df.drop(columns=["deviceName", "battery_mV", "rssi", "snr"])

# Usamos GridOptionsBuilder para configurar AG-Grid con lazy loading
gb = GridOptionsBuilder.from_dataframe(df_table)

# Configuramos el lazy loading (carga de los datos por páginas)
gb.configure_pagination(paginationPageSize=10)  # 10 filas por página
gb.configure_default_column(editable=True, groupable=True)
gb.configure_selection('single')

# Aplicamos las opciones de AG-Grid
grid_options = gb.build()

# Renderizamos la tabla con AG-Grid
AgGrid(df_table, gridOptions=grid_options, height=400, use_container_width=True)

# -------------------- Grafico pritty que yo quiero ------------

col1, col2 = st.columns(2)

# ------------------ GAUGE TEMPERATURA ------------------
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
st.line_chart(df, x='time', y=plot_data, height=400)
