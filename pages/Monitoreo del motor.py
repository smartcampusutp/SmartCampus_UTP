import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import os
import numpy as np

# ================= CONFIGURACIÓN =================
st.set_page_config(
    page_title="Estado bomba agua helada",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Umbrales ISO referenciales (aceleración RMS)
ISO_ALERTA = 3.0    # m/s²
ISO_CRITICO = 10.0  # m/s²

st.title("Estado bomba de agua helada — SmartCampus UTP")
st_autorefresh(interval=50000, limit=None, key="refresh")

# ================= CONSTANTES FÍSICAS =================
G = 9.81
MG_TO_MS2 = G / 1000
Z_GRAVITY_MG = 4000

# ================= CARGA DE DATOS =================
@st.cache_data(ttl=60)
def load_daily_data(selected_date):
    filename = f"smartcampusudp_{selected_date}.csv"
    local_path = f"Data_udp/{filename}"
    github_url = f"https://raw.githubusercontent.com/smartcampusutp/SmartCampus_UTP/main/Data_udp/{filename}"

    try:
        if os.path.exists(local_path):
            df = pd.read_csv(local_path)
        else:
            df = pd.read_csv(github_url)
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    df = df.dropna(subset=["time"])
    df = df.sort_values("time").reset_index(drop=True)
    return df

# ================= SIDEBAR =================
st.sidebar.header("Filtros")

today = pd.Timestamp.now().date()
selected_date = st.sidebar.date_input("Seleccionar día", today)

df = load_daily_data(selected_date)
if df.empty:
    st.warning("No hay datos.")
    st.stop()

sensors = sorted(df["deviceName"].dropna().unique())
selected_sensor = st.sidebar.selectbox("Seleccionar sensor", sensors)

df_sensor = df[df["deviceName"] == selected_sensor].copy()
if df_sensor.empty:
    st.stop()

# -------- FILTRO POR HORA --------
available_hours = sorted(df_sensor["time"].dt.hour.unique())

selected_hour = st.sidebar.selectbox(
    "Seleccionar hora",
    available_hours,
    format_func=lambda h: f"{h:02d}:00 - {h:02d}:59"
)

df_sensor = df_sensor[df_sensor["time"].dt.hour == selected_hour]
if df_sensor.empty:
    st.stop()

# ================= PROCESAMIENTO DE ACELERACIONES =================
df_sensor["accX_ms2"] = df_sensor["accXRMS"] * MG_TO_MS2
df_sensor["accY_ms2"] = df_sensor["accYRMS"] * MG_TO_MS2
df_sensor["accZ_ms2"] = (df_sensor["accZRMS"] - Z_GRAVITY_MG) * MG_TO_MS2

df_sensor["RMS_GLOBAL"] = np.sqrt(
    df_sensor["accX_ms2"]**2 +
    df_sensor["accY_ms2"]**2 +
    df_sensor["accZ_ms2"]**2
)

# ================= ESTADO ISO (REFERENCIAL) =================
df_sensor["estado_iso"] = "NORMAL"
df_sensor.loc[df_sensor["RMS_GLOBAL"] > ISO_ALERTA, "estado_iso"] = "ALERTA"
df_sensor.loc[df_sensor["RMS_GLOBAL"] > ISO_CRITICO, "estado_iso"] = "CRÍTICA"

# ================= DETECCIÓN DE ANOMALÍAS (IA PURA) =================
df_sensor["estado"] = "NORMAL"

# anomaly score:
# < 0  → comportamiento normal
# >= 0 → fuera del clúster normal
# >= 1 → anomalía severa
df_sensor.loc[df_sensor["anomaly"] >= 0, "estado"] = "ANOMALÍA"
df_sensor.loc[df_sensor["anomaly"] >= 1.0, "estado"] = "CRÍTICA"

latest = df_sensor.iloc[-1]

# ================= FUNCIONES AUX =================
def safe_metric(row, col, fmt, unit=""):
    v = row.get(col)
    if pd.isna(v):
        return "N/A"
    return f"{float(v):{fmt}} {unit}".strip()

# ================= KPIs =================
st.markdown(
    f"## Sensor: *{selected_sensor}* — Fecha: *{selected_date}* — Hora: *{selected_hour:02d}:00*"
)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🌡️ Temperatura", safe_metric(latest, "temperature", ".1f", "°C"))
c2.metric("💧 Humedad", safe_metric(latest, "humidity", ".1f", "%"))
c3.metric("⚠️ IA Anomaly", safe_metric(latest, "anomaly", ".2f"))
c4.metric("🌫️ BVOC", safe_metric(latest, "bvoc", ".1f", "ppb"))
c5.metric("🏭 IAQ", safe_metric(latest, "iaq", ".0f", "ppm"))

c6, c7, c8 = st.columns(3)
c6.metric("📈 Acc X", f"{latest['accX_ms2']:.3f} m/s²")
c7.metric("📈 Acc Y", f"{latest['accY_ms2']:.3f} m/s²")
c8.metric("📈 Acc Z", f"{latest['accZ_ms2']:.3f} m/s²")

st.divider()

# ================= ESTADO GENERAL =================
if latest["estado"] == "NORMAL":
    st.success("🟢 OPERACIÓN NORMAL")
elif latest["estado"] == "ANOMALÍA":
    st.warning("🟠 ANOMALÍA DETECTADA (IA)")
else:
    st.error("🔴 ANOMALÍA CRÍTICA")

# ================= GRÁFICOS =================
df_plot = df_sensor.tail(2000)

def plot_line(y_cols, title, unit):
    fig = go.Figure()
    for c in y_cols:
        fig.add_trace(go.Scattergl(
            x=df_plot["time"],
            y=df_plot[c],
            mode="lines",
            name=c
        ))
    fig.update_layout(
        title=title,
        yaxis_title=unit,
        height=300
    )
    st.plotly_chart(fig, use_container_width=True)

plot_line(["accX_ms2", "accY_ms2", "accZ_ms2"], "Aceleración RMS corregida", "m/s²")
plot_line(["RMS_GLOBAL"], "RMS Global", "m/s²")
plot_line(["anomaly"], "Anomaly Score (IA)", "score")
plot_line(["temperature"], "Temperatura", "°C")
plot_line(["humidity"], "Humedad", "%")
plot_line(["bvoc"], "BVOC", "ppb")
plot_line(["iaq"], "IAQ", "ppm")

# ================= TABLAS =================
with st.expander("Últimos datos"):
    st.dataframe(df_sensor.tail(10))

st.subheader("Registros con anomalía detectada por IA")

df_ia_anom = df_sensor[df_sensor["anomaly"] >= 0].tail(20)

if df_ia_anom.empty:
    st.info("No se detectaron anomalías según IA.")
else:
    st.dataframe(
        df_ia_anom[[
            "time",
            "anomaly",
            "RMS_GLOBAL",
            "temperature",
            "humidity",
            "estado_iso"
        ]]
    )

st.subheader("Registros con vibración elevada (ISO 20816 – referencia)")

df_iso = df_sensor[df_sensor["RMS_GLOBAL"] > ISO_ALERTA].tail(20)

if df_iso.empty:
    st.info("No se detectaron vibraciones fuera del rango normal.")
else:
    st.dataframe(
        df_iso[[
            "time",
            "RMS_GLOBAL",
            "accX_ms2",
            "accY_ms2",
            "accZ_ms2",
            "estado_iso"
        ]]
    )
