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

st.title("Estado bomba de agua helada")
st.caption("SmartCampus UTP")
st_autorefresh(interval=50000, limit=None, key="refresh")

# ================= NOTA IMPORTANTE =================
# Sensor/pipeline limitado a ~0–10 Hz.
# ISO 20816 usa severidad por velocidad RMS (mm/s) típicamente en banda mayor (p.ej., 10–1000 Hz).
# Aquí usamos una "Velocidad equivalente" (ISO-like) usando 1X (RPM/60).
# Indicador informativo, no ISO estricto.

# ================= PARÁMETROS =================
RPM = 3335
F_1X = RPM / 60.0  # Hz

VEL_ALERTA_MM_S = 4.5
VEL_CRITICO_MM_S = 7.1

REL_ALERT = 1.30  # +30%
REL_CRIT  = 1.60  # +60%
N_SUSTAIN = 10

# ================= UI =================
PLOT_HEIGHT = 520
ENV_PLOT_HEIGHT = 460
DISABLE_MODEBAR = True

# ================= CONSTANTES =================
G = 9.81
MG_TO_MS2 = G / 1000
Z_GRAVITY_MG = 4000  # si no aplica, ponlo en 0

# ================= CARGA DE DATOS =================
@st.cache_data(ttl=300)
def load_daily_data(date_obj):
    filename = f"smartcampusudp_{date_obj}.csv"
    local_path = f"Data_udp/{filename}"
    github_url = f"https://raw.githubusercontent.com/smartcampusutp/SmartCampus_UTP/main/Data_udp/{filename}"

    try:
        if os.path.exists(local_path):
            df = pd.read_csv(local_path)
        else:
            df = pd.read_csv(github_url)
    except Exception:
        return pd.DataFrame()

    if "time" not in df.columns:
        return pd.DataFrame()

    keep_cols = [
        "time", "deviceName",
        "accXRMS", "accYRMS", "accZRMS",
        "anomaly",
        "temperature", "humidity", "bvoc", "iaq"
    ]
    keep_cols = [c for c in keep_cols if c in df.columns]
    df = df[keep_cols].copy()

    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    df = df.dropna(subset=["time"])
    df = df.sort_values("time").reset_index(drop=True)
    return df


def load_date_range(start_date, end_date):
    frames = []
    d0 = pd.Timestamp(start_date).date()
    d1 = pd.Timestamp(end_date).date()
    if d1 < d0:
        d0, d1 = d1, d0

    cur = d0
    while cur <= d1:
        tmp = load_daily_data(cur)
        if not tmp.empty:
            frames.append(tmp)
        cur = (pd.Timestamp(cur) + pd.Timedelta(days=1)).date()

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def choose_resample_rule(start_date, end_date):
    d0 = pd.Timestamp(start_date)
    d1 = pd.Timestamp(end_date)
    days = max(1, int((d1 - d0).days) + 1)

    if days <= 1:
        return None
    if days <= 3:
        return "30S"
    if days <= 7:
        return "1min"
    if days <= 14:
        return "2min"
    if days <= 31:
        return "5min"
    return "15min"


def resample_df(df_in, rule):
    if rule is None:
        return df_in
    d = df_in.copy().set_index("time").sort_index()

    numeric_cols = [c for c in d.columns if c != "deviceName"]
    out = d[numeric_cols].resample(rule).median()
    out = out.dropna(how="all").reset_index()
    return out


# ================= SIDEBAR =================
st.sidebar.header("Filtros")

today = pd.Timestamp.now().date()
mode = st.sidebar.radio("Rango", ["Día", "Rango de días"], index=0)

if mode == "Día":
    selected_date = st.sidebar.date_input("Día", today)
    start_date, end_date = selected_date, selected_date
else:
    default_start = (pd.Timestamp(today) - pd.Timedelta(days=6)).date()
    start_date = st.sidebar.date_input("Desde", default_start)
    end_date = st.sidebar.date_input("Hasta", today)

df = load_date_range(start_date, end_date)
if df.empty:
    st.warning("No hay datos en el rango seleccionado.")
    st.stop()

if "deviceName" not in df.columns:
    st.error("El CSV no tiene columna 'deviceName'.")
    st.stop()

sensors = sorted(df["deviceName"].dropna().unique())
if not sensors:
    st.warning("No hay sensores en el archivo.")
    st.stop()

selected_sensor = st.sidebar.selectbox("Sensor", sensors)
df_sensor = df[df["deviceName"] == selected_sensor].copy()
if df_sensor.empty:
    st.warning("No hay datos para ese sensor en el rango.")
    st.stop()

# Resolución para ver varios días (sin filtro por hora)
auto_rule = choose_resample_rule(start_date, end_date)
rule = st.sidebar.selectbox(
    "Resolución (para varios días)",
    options=["Auto", "Sin resample", "30S", "1min", "2min", "5min", "15min"],
    index=0
)
if rule == "Auto":
    resample_rule = auto_rule
elif rule == "Sin resample":
    resample_rule = None
else:
    resample_rule = rule

# ================= VALIDACIÓN =================
required_cols = ["accXRMS", "accYRMS", "accZRMS", "anomaly"]
missing = [c for c in required_cols if c not in df_sensor.columns]
if missing:
    st.error(f"Faltan columnas: {missing}")
    st.stop()

# ================= PROCESAMIENTO =================
df_sensor = df_sensor.sort_values("time").reset_index(drop=True)

df_sensor["accX_ms2"] = pd.to_numeric(df_sensor["accXRMS"], errors="coerce") * MG_TO_MS2
df_sensor["accY_ms2"] = pd.to_numeric(df_sensor["accYRMS"], errors="coerce") * MG_TO_MS2
df_sensor["accZ_ms2"] = (pd.to_numeric(df_sensor["accZRMS"], errors="coerce") - Z_GRAVITY_MG) * MG_TO_MS2
df_sensor = df_sensor.dropna(subset=["accX_ms2", "accY_ms2", "accZ_ms2"]).copy()
if df_sensor.empty:
    st.warning("Aceleraciones inválidas tras conversión.")
    st.stop()

df_sensor["RMS_GLOBAL_ACC_ms2"] = np.sqrt(
    df_sensor["accX_ms2"]**2 + df_sensor["accY_ms2"]**2 + df_sensor["accZ_ms2"]**2
)

df_sensor["VEL_EQ_mm_s"] = (df_sensor["RMS_GLOBAL_ACC_ms2"] / (2 * np.pi * F_1X)) * 1000
df_sensor["estado_vel_ref"] = "NORMAL"
df_sensor.loc[df_sensor["VEL_EQ_mm_s"] > VEL_ALERTA_MM_S, "estado_vel_ref"] = "ALERTA"
df_sensor.loc[df_sensor["VEL_EQ_mm_s"] > VEL_CRITICO_MM_S, "estado_vel_ref"] = "CRÍTICA"

df_sensor["anomaly"] = pd.to_numeric(df_sensor["anomaly"], errors="coerce")

# IA periódica (sostenida)
is_ai_anom = (df_sensor["anomaly"] >= 0).astype(int)
is_ai_crit = (df_sensor["anomaly"] >= 1.0).astype(int)
df_sensor["ai_anom_periodico"] = is_ai_anom.rolling(window=N_SUSTAIN, min_periods=N_SUSTAIN).sum() >= N_SUSTAIN
df_sensor["ai_crit_periodico"] = is_ai_crit.rolling(window=N_SUSTAIN, min_periods=N_SUSTAIN).sum() >= N_SUSTAIN

df_sensor["estado_ia_periodico"] = "NORMAL"
df_sensor.loc[df_sensor["ai_anom_periodico"], "estado_ia_periodico"] = "ANOMALÍA"
df_sensor.loc[df_sensor["ai_crit_periodico"], "estado_ia_periodico"] = "CRÍTICA"

# REL baseline
BASELINE_WINDOW = min(600, max(60, len(df_sensor)//6))
MIN_PERIODS = max(10, BASELINE_WINDOW // 5)
df_sensor["baseline_med_ms2"] = (
    df_sensor["RMS_GLOBAL_ACC_ms2"].rolling(window=BASELINE_WINDOW, min_periods=MIN_PERIODS).median()
).bfill()

eps = 1e-9
df_sensor["rms_rel"] = df_sensor["RMS_GLOBAL_ACC_ms2"] / df_sensor["baseline_med_ms2"].clip(lower=eps)

is_rel_alert = (df_sensor["rms_rel"] >= REL_ALERT).astype(int)
is_rel_crit = (df_sensor["rms_rel"] >= REL_CRIT).astype(int)
df_sensor["rel_alert_periodico"] = is_rel_alert.rolling(window=N_SUSTAIN, min_periods=N_SUSTAIN).sum() >= N_SUSTAIN
df_sensor["rel_crit_periodico"] = is_rel_crit.rolling(window=N_SUSTAIN, min_periods=N_SUSTAIN).sum() >= N_SUSTAIN

df_sensor["estado_rel"] = "NORMAL"
df_sensor.loc[df_sensor["rel_alert_periodico"], "estado_rel"] = "ALERTA"
df_sensor.loc[df_sensor["rel_crit_periodico"], "estado_rel"] = "CRÍTICA"

latest = df_sensor.iloc[-1]

# ======= KPIs ambientales (PROMEDIOS del rango seleccionado) =======
env_cols = ["temperature", "humidity", "bvoc", "iaq"]
env_avgs = {}
for c in env_cols:
    if c in df_sensor.columns:
        env_avgs[c] = pd.to_numeric(df_sensor[c], errors="coerce").dropna()

def avg_or_na(series, fmt):
    if series is None or len(series) == 0:
        return "N/A"
    return f"{float(series.mean()):{fmt}}"

# ================= RESAMPLE PARA GRÁFICOS =================
df_plot = df_sensor[[
    "time",
    "accX_ms2", "accY_ms2", "accZ_ms2",
    "RMS_GLOBAL_ACC_ms2",
    "VEL_EQ_mm_s",
    "anomaly",
    "temperature", "humidity", "bvoc", "iaq"
]].copy()

df_plot = resample_df(df_plot, resample_rule)
if df_plot.empty:
    st.warning("No hay datos después del resample.")
    st.stop()

# ================= HEADER =================
st.markdown(f"**Sensor:** {selected_sensor} &nbsp;|&nbsp; **Rango:** {start_date} → {end_date}")

# ================= KPIs (como tu imagen) =================
# fila 1: ambientales (promedio del rango)
a1, a2, a3, a4, a5 = st.columns(5)
if "temperature" in env_avgs:
    a1.metric("Temperatura", f"{avg_or_na(env_avgs['temperature'], '.1f')} °C")
else:
    a1.metric("Temperatura", "N/A")
if "humidity" in env_avgs:
    a2.metric("Humedad", f"{avg_or_na(env_avgs['humidity'], '.1f')} %")
else:
    a2.metric("Humedad", "N/A")
a3.metric("IA Anomaly", f"{float(latest['anomaly']):.2f}" if pd.notna(latest["anomaly"]) else "N/A")
if "bvoc" in env_avgs:
    a4.metric("BVOC", f"{avg_or_na(env_avgs['bvoc'], '.1f')} ppb")
else:
    a4.metric("BVOC", "N/A")
if "iaq" in env_avgs:
    a5.metric("IAQ", f"{avg_or_na(env_avgs['iaq'], '.0f')} ppm")
else:
    a5.metric("IAQ", "N/A")

# fila 2: vibración (último valor)
b1, b2, b3 = st.columns(3)
b1.metric("Acc X", f"{latest['accX_ms2']:.3f} m/s²")
b2.metric("Acc Y", f"{latest['accY_ms2']:.3f} m/s²")
b3.metric("Acc Z", f"{latest['accZ_ms2']:.3f} m/s²")

st.divider()

# ================= ESTADOS =================
s1, s2, s3 = st.columns(3)

def pill(col, label, state):
    if state == "NORMAL":
        col.success(label)
    elif state in ("ALERTA", "ANOMALÍA"):
        col.warning(label)
    else:
        col.error(label)

pill(s1, f"IA: {latest['estado_ia_periodico']}", latest["estado_ia_periodico"])
pill(s2, f"REL: {latest['estado_rel']}", latest["estado_rel"])
pill(s3, f"ISO-like: {latest['estado_vel_ref']}", latest["estado_vel_ref"])

st.caption("⚠️ Vel Eq: indicador ISO-like (sensor limitado a ~10 Hz).")
st.divider()

# ================= FUNCIÓN PLOT (NO UNE HUECOS) =================
def plot_line(df_in, y_cols, title, y_title, height=520, show_legend=True):
    fig = go.Figure()
    d = df_in.sort_values("time").copy()

    for c in y_cols:
        if c not in d.columns or d[c].isna().all():
            continue
        fig.add_trace(go.Scatter(
            x=d["time"],
            y=d[c],
            mode="lines",
            name=c,
            connectgaps=False  # ✅ no diagonales por huecos
        ))

    fig.update_layout(
        title=title,
        yaxis_title=y_title,
        height=height,
        margin=dict(l=45, r=20, t=55, b=35),
        showlegend=show_legend,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ================= GRÁFICOS (1 POR FILA) =================
plot_line(df_plot, ["accX_ms2", "accY_ms2", "accZ_ms2"], "Aceleración RMS", "m/s²", PLOT_HEIGHT, True)
plot_line(df_plot, ["RMS_GLOBAL_ACC_ms2"], "RMS Global", "m/s²", PLOT_HEIGHT, False)
plot_line(df_plot, ["VEL_EQ_mm_s"], "Velocidad Eq (ISO-like)", "mm/s", PLOT_HEIGHT, False)
plot_line(df_plot, ["anomaly"], "IA score", "score", PLOT_HEIGHT, False)

# Ambientales (si existen)
env_map = [
    ("temperature", "Temperatura", "°C"),
    ("humidity", "Humedad", "%"),
    ("bvoc", "BVOC", "ppb"),
    ("iaq", "IAQ", "ppm"),
]
env_present = [(c, t, u) for (c, t, u) in env_map if c in df_plot.columns]

if env_present:
    st.subheader("Ambientales")
    for c, t, u in env_present:
        plot_line(df_plot, [c], t, u, ENV_PLOT_HEIGHT, False)

# ================= TABLAS =================
with st.expander("Últimos datos"):
    st.dataframe(df_sensor.tail(10))

st.subheader("Eventos relevantes (REL periódico o IA periódico)")
df_events = df_sensor[
    (df_sensor["estado_rel"] != "NORMAL") |
    (df_sensor["estado_ia_periodico"] != "NORMAL")
].tail(80)

if df_events.empty:
    st.info("No hay eventos periódicos detectados.")
else:
    st.dataframe(df_events[[
        "time",
        "RMS_GLOBAL_ACC_ms2",
        "VEL_EQ_mm_s",
        "anomaly",
        "estado_rel",
        "estado_ia_periodico",
        "estado_vel_ref",
    ]])