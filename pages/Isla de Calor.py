import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import requests
import re
import time
from datetime import date

# ------------------- CONFIGURACIÓN -------------------
st.set_page_config(layout="wide", initial_sidebar_state="expanded")
st.title("Dashboard - Isla de Calor UTP")
st.image("https://i.ibb.co/Q3RQT66R/SMT.png", caption=".")

st_autorefresh(interval=60000, limit=None, key="refresh")

# ------------------- OBTENER CSV DISPONIBLES -------------------
@st.cache_data(ttl=300)
def get_available_csvs():
    api_url = (
        "https://api.github.com/repos/"
        "smartcampusutp/SmartCampus_UTP/contents/Data/IslasCalor"
    )

    response = requests.get(api_url)
    response.raise_for_status()
    files = response.json()

    pattern = r"IslasCalor_(\d{4}-\d{2}-\d{2})\.csv"
    data = []

    for f in files:
        match = re.match(pattern, f["name"])
        if match:
            data.append({
                "name": f["name"],
                "date": pd.to_datetime(match.group(1)).date(),
                "url": f["download_url"]
            })

    return pd.DataFrame(data).sort_values("date")

# ------------------- CARGA DE DATOS POR FECHA -------------------
@st.cache_data(ttl=120)
def load_data_by_date(start_date, end_date):
    files_df = get_available_csvs()

    selected = files_df[
        (files_df["date"] >= start_date) &
        (files_df["date"] <= end_date)
    ]

    if selected.empty:
        return pd.DataFrame()

    dfs = []
    for _, row in selected.iterrows():
        df = pd.read_csv(row["url"])
        df["file_date"] = row["date"]
        dfs.append(df)

    data = pd.concat(dfs, ignore_index=True)

    if "time" not in data.columns:
        return pd.DataFrame()

    data["time"] = pd.to_datetime(data["time"], errors="coerce")
    data = data.dropna(subset=["time"])

    return data

# ------------------- SIDEBAR -------------------
st.sidebar.header("Filtros")

files_df = get_available_csvs()

if files_df.empty:
    st.sidebar.error("No hay archivos disponibles")
    st.stop()

min_date = files_df["date"].min()
max_date = files_df["date"].max()

date_range = st.sidebar.date_input(
    "Rango de fechas",
    value=(max_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(date_range, tuple):
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

df = load_data_by_date(start_date, end_date)

# ------------------- FILTRO POR SENSOR -------------------
if "deviceName" in df.columns and not df.empty:
    sensors = sorted(df["deviceName"].unique())
    selected_sensor = st.sidebar.selectbox("Sensor", sensors)
    df_sensor = df[df["deviceName"] == selected_sensor]
else:
    df_sensor = df.copy()

st.sidebar.markdown("---\nCreated by I2")

# ------------------- KPI -------------------
st.markdown("### Última actualización")
col1, col2, col3 = st.columns(3)

if not df_sensor.empty:
    latest = df_sensor.loc[df_sensor["time"].idxmax()]

    col1.metric("🌡️ Temperatura", f"{latest['temperature']:.2f} °C")
    col2.metric("💧 Humedad", f"{latest['humidity']:.2f} %")

    if "pressure_hPa" in latest:
        col3.metric("🔽 Presión", f"{latest['pressure_hPa']:.0f} hPa")
else:
    st.warning("No hay datos para los filtros seleccionados")

# ------------------- TABLA -------------------
st.markdown("### Últimos registros")
if not df_sensor.empty:
    st.dataframe(
        df_sensor.drop(columns=["Unnamed: 0"], errors="ignore")
        .sort_values("time", ascending=False)
        .head(500),
        use_container_width=True
    )

# ------------------- GAUGES -------------------
if not df_sensor.empty:
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(go.Figure(go.Indicator(
            mode="gauge+number",
            value=latest["temperature"],
            title={"text": "Temperatura (°C)"},
            gauge={
                "axis": {"range": [0, 40]},
                "bar": {"color": "red"},
                "threshold": {"line": {"color": "red", "width": 4}, "value": 30}
            }
        )), use_container_width=True)

    with col2:
        st.plotly_chart(go.Figure(go.Indicator(
            mode="gauge+number",
            value=latest["humidity"],
            title={"text": "Humedad (%)"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "blue"},
                "threshold": {"line": {"color": "red", "width": 4}, "value": 80}
            }
        )), use_container_width=True)

# ------------------- GRÁFICOS TEMPORALES -------------------
st.markdown("### Evolución temporal")

if not df_sensor.empty:
    df_plot = df_sensor.sort_values("time")

    def dyn_range(s, m=0.1):
        return s.min() - (s.max() - s.min()) * m, s.max() + (s.max() - s.min()) * m

    # Temperatura
    fig_t = go.Figure()
    fig_t.add_trace(go.Scatter(
        x=df_plot["time"], y=df_plot["temperature"],
        mode="lines", name="Temperatura"
    ))
    fig_t.update_layout(yaxis=dict(range=dyn_range(df_plot["temperature"])))
    st.plotly_chart(fig_t, use_container_width=True)

    # Humedad
    fig_h = go.Figure()
    fig_h.add_trace(go.Scatter(
        x=df_plot["time"], y=df_plot["humidity"],
        mode="lines", name="Humedad"
    ))
    fig_h.update_layout(yaxis=dict(range=dyn_range(df_plot["humidity"])))
    st.plotly_chart(fig_h, use_container_width=True)

    # Presión
    if "pressure_hPa" in df_plot.columns:
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(
            x=df_plot["time"], y=df_plot["pressure_hPa"],
            mode="lines", name="Presión"
        ))
        fig_p.update_layout(yaxis=dict(range=dyn_range(df_plot["pressure_hPa"])))
        st.plotly_chart(fig_p, use_container_width=True)
