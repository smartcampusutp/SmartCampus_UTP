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
st.title("Dashboard - Medidores de Ruido UTP")

st_autorefresh(interval=60000, limit=None, key="refresh")

# ------------------- OBTENER CSV DISPONIBLES -------------------
@st.cache_data(ttl=300)
def get_available_csvs():
    api_url = (
        "https://api.github.com/repos/"
        "smartcampusutp/SmartCampus_UTP/contents/Data/Ruido"
    )

    response = requests.get(api_url)
    response.raise_for_status()
    files = response.json()

    pattern = r"ruido_(\d{4}-\d{2}-\d{2})\.csv"
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

    col1.metric("🔊 dB Máximo", f"{latest['Lmax_dB']:.1f}  dB")
    col2.metric("📝 Clase", f"{latest['Lmax_class']}")
    col3.metric("📢 Nivel sonoro continuo equivalente", f"{latest['LAeq1min_dB']:.2f} dB")
else:
    st.warning("No hay datos para los filtros seleccionados")

col4, col5, col6 = st.columns(3)

if not df_sensor.empty:
    latest = df_sensor.loc[df_sensor["time"].idxmax()]

    col4.metric("🔈 LAeq - Sonido de Fondo", f"{latest['LAeq_Background Noise']:.2f}  dB")
    col5.metric("👤 LAeq - Personas", f"{latest['LAeq_People']:.2f}  dB")
    col6.metric("🚗 LAeq - Vehículos", f"{latest['LAeq_Vehicle']:.2f}  dB")
else:
    st.warning("No hay datos para los filtros seleccionados")

col7, col8, col9 = st.columns(3)

if not df_sensor.empty:
    latest = df_sensor.loc[df_sensor["time"].idxmax()]

    col7.metric("🔈 Porcentaje de aparición - Sonido de fondo", f"{latest['pct_Background Noise']:.1f} %")
    col8.metric("👤 Porcentaje de aparición - Personas", f"{latest['pct_People']:.1f} %")
    col9.metric("🚗 Porcentaje de aparición - Vehículos", f"{latest['pct_Vehicle']:.1f} %")
else:
    st.warning("No hay datos para los filtros seleccionados")
    
col10, col11, col12 = st.columns(3)

if not df_sensor.empty:
    latest = df_sensor.loc[df_sensor["time"].idxmax()]

    col10.metric("Percentil 10", f"{latest['P10_dB']:.1f}  dB")
    col11.metric("Percentil 50", f"{latest['P50_dB']:.1f}  dB")
    col12.metric("Percentil 90", f"{latest['P90_dB']:.1f}  dB")
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


# ------------------- GRÁFICOS TEMPORALES -------------------
st.markdown("### Evolución temporal")

if not df_sensor.empty:
    df_plot = df_sensor.sort_values("time")

    def dyn_range(s, m=0.1):
        return s.min() - (s.max() - s.min()) * m, s.max() + (s.max() - s.min()) * m

    # DB MAX
    fig_t = go.Figure()
    fig_t.add_trace(go.Scatter(
        x=df_plot["time"], y=df_plot["Lmax_dB"],
        mode="lines", name="dB Máximo"
    ))
    fig_t.update_layout(
        title=dict(
         text="Evolución temporal del nivel máximo de ruido (Lmax)",
         x=0.5
        ),
        xaxis_title="Tiempo",
        yaxis_title="Nivel sonoro [dB]",
        yaxis=dict(range=dyn_range(df_plot["Lmax_dB"]))
    )
    st.plotly_chart(fig_t, use_container_width=True)

    # LAeq
    fig_h = go.Figure()
    fig_h.add_trace(go.Scatter(
        x=df_plot["time"], y=df_plot["LAeq1min_dB"],
        mode="lines", name="Nivel sonoro continuo equivalente"
    ))
    fig_h.update_layout(
        title=dict(
            text="Evolución temporal del nivel sonoro continuo equivalente (LAeq, 5 min)",
            x=0.5
        ),
        xaxis_title="Tiempo",
        yaxis_title="Nivel sonoro [dB]",
        yaxis=dict(range=dyn_range(df_plot["LAeq1min_dB"]))
    )
            
    st.plotly_chart(fig_h, use_container_width=True)

