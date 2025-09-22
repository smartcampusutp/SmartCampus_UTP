import streamlit as st
import pandas as pd
import altair as alt
import math
import datetime as dt

CSV_FILE = "Data_udp/smartcampusudp.csv"

st.set_page_config(page_title="Dashboard Sensores", layout="wide")
st.title("📊 Dashboard - ventana de 3 horas por día (optimizado)")

# columnas esperadas (ajusta si tus columnas tienen otros nombres)
DESIRED_COLS = ["temperature", "humidity", "anomaly", "bvoc", "iaq",
                "accXRMS", "accYRMS", "accZRMS"]

# -----------------------
# Utils para leer por chunks (no cargar todo)
# -----------------------
@st.cache_data(ttl=120)
def get_file_columns(path):
    try:
        return pd.read_csv(path, nrows=0).columns.tolist()
    except Exception:
        return []

@st.cache_data(ttl=120)
def get_available_dates(path, time_col="time", chunksize=200_000):
    cols = [time_col]
    dates = set()
    try:
        for chunk in pd.read_csv(path, usecols=cols, parse_dates=[time_col],
                                 chunksize=chunksize, low_memory=True):
            if time_col in chunk.columns:
                chunk = chunk.dropna(subset=[time_col])
                dates.update(chunk[time_col].dt.date.unique())
    except Exception:
        # fallback simple read if chunking fails
        try:
            df = pd.read_csv(path, parse_dates=[time_col])
            dates.update(df[time_col].dt.date.unique())
        except Exception:
            pass
    return sorted(dates)

@st.cache_data(ttl=120)
def get_day_time_bounds(path, selected_date, time_col="time", chunksize=200_000):
    """Devuelve (min_datetime, max_datetime) para el día dado, o (None,None) si no hay datos."""
    min_dt = None
    max_dt = None
    date_obj = pd.to_datetime(selected_date).date()
    cols = [time_col]
    try:
        for chunk in pd.read_csv(path, usecols=cols, parse_dates=[time_col],
                                 chunksize=chunksize, low_memory=True):
            if time_col not in chunk.columns:
                continue
            chunk = chunk.dropna(subset=[time_col])
            mask = chunk[time_col].dt.date == date_obj
            if not mask.any():
                continue
            day_chunk = chunk.loc[mask, time_col]
            cur_min = day_chunk.min()
            cur_max = day_chunk.max()
            if min_dt is None or cur_min < min_dt:
                min_dt = cur_min
            if max_dt is None or cur_max > max_dt:
                max_dt = cur_max
    except Exception:
        # fallback
        try:
            df = pd.read_csv(path, parse_dates=[time_col], low_memory=True)
            df = df.dropna(subset=[time_col])
            df_day = df[df[time_col].dt.date == date_obj]
            if not df_day.empty:
                min_dt = df_day[time_col].min()
                max_dt = df_day[time_col].max()
        except Exception:
            pass
    return min_dt, max_dt

def load_window(path, start_dt, end_dt, time_col="time", chunksize=200_000):
    """Lee por chunks y devuelve sólo las filas entre start_dt (incl) y end_dt (excl)."""
    # descubrir columnas reales del archivo
    all_cols = get_file_columns(path)
    # aseguramos que 'time' esté y tomamos intersección de columnas deseadas
    usecols = [c for c in ["time"] + DESIRED_COLS if c in all_cols]
    if "time" not in usecols:
        st.error("El archivo no tiene la columna 'time'. Revisa el CSV.")
        return pd.DataFrame(columns=usecols)

    pieces = []
    try:
        for chunk in pd.read_csv(path, usecols=usecols, parse_dates=["time"],
                                 chunksize=chunksize, low_memory=True):
            # filtrar por ventana
            mask = (chunk["time"] >= start_dt) & (chunk["time"] < end_dt)
            if mask.any():
                pieces.append(chunk.loc[mask])
    except Exception:
        # fallback a leer todo (solo si chunk falla)
        df = pd.read_csv(path, usecols=usecols, parse_dates=["time"])
        pieces = [df[(df["time"] >= start_dt) & (df["time"] < end_dt)]]

    if not pieces:
        return pd.DataFrame(columns=usecols)

    df_window = pd.concat(pieces, ignore_index=True)
    df_window = df_window.sort_values("time").reset_index(drop=True)
    return df_window

# -----------------------
# Helpers de gráfico
# -----------------------
def compute_y_domain(series):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return None
    min_val, max_val = s.min(), s.max()
    margin = max((max_val - min_val) * 0.01, 0.01 * abs(max_val) if max_val != 0 else 1)
    return (math.floor(min_val - margin), math.ceil(max_val + margin))

def plot_line(df, y_cols, title="", y_label="Valor", start_dt=None, end_dt=None):
    if df.empty:
        return alt.Chart(pd.DataFrame({"time": [], "valor": [], "variable": []})).mark_line()
    # mantener solo columnas existentes
    cols = ["time"] + [c for c in y_cols if c in df.columns]
    if len(cols) <= 1:
        return alt.Chart(pd.DataFrame({"time": [], "valor": [], "variable": []})).mark_line()

    df = df[cols].copy()
    df_melted = df.melt("time", value_vars=[c for c in cols if c != "time"],
                        var_name="variable", value_name="valor")
    df_melted["valor"] = pd.to_numeric(df_melted["valor"], errors="coerce")
    df_melted = df_melted.dropna(subset=["time", "valor"])
    if df_melted.empty:
        return alt.Chart(pd.DataFrame({"time": [], "valor": [], "variable": []})).mark_line()

    y_domain = compute_y_domain(df_melted["valor"])
    x_domain = None
    if start_dt is not None and end_dt is not None:
        x_domain = [start_dt, end_dt]

    x_enc = alt.X("time:T",
                  scale=alt.Scale(domain=x_domain) if x_domain else alt.Undefined,
                  axis=alt.Axis(format="%H:%M", labelAngle=0, labelOverlap=True))
    y_enc = alt.Y("valor:Q", title=y_label,
                  scale=alt.Scale(domain=y_domain) if y_domain else alt.Undefined)

    chart = (
        alt.Chart(df_melted)
           .mark_line(clip=True)
           .encode(x=x_enc, y=y_enc, color="variable:N")
           .properties(width="container", height=280, title=title)
           .interactive()
    )
    return chart

# -----------------------
# UI: selector de día y ventana 3h
# -----------------------
if not st.sidebar.button("Recargar manualmente (limpia cache)"):
    pass

# obtener fechas disponibles (rápido porque lee sólo la columna time por chunks)
available_dates = get_available_dates(CSV_FILE)
if not available_dates:
    st.warning("No se encontraron fechas en el CSV (columna 'time' vacía o archivo inaccesible).")
    st.stop()

# selector de fecha en sidebar para liberar espacio en la página principal
selected_date = st.sidebar.date_input("📅 Selecciona día:", value=available_dates[-1],
                                      min_value=available_dates[0], max_value=available_dates[-1])

# obtener límites de tiempo para ese día
min_dt, max_dt = get_day_time_bounds(CSV_FILE, selected_date)
if min_dt is None or max_dt is None:
    st.warning("No hay datos para el día seleccionado.")
    st.stop()

# convertir a horas enteras para slider (asegurar que haya espacio para 3h)
min_hour = min_dt.hour
max_hour = max_dt.hour
# Si los datos llegan hasta 23:50, permitir start_hour hasta 20 por seguridad
max_start_hour = max(0, max_hour - 2)  # para poder tener 3 horas completas (start + 3)
if max_start_hour < min_hour:
    max_start_hour = min_hour

start_hour = st.sidebar.slider("⏰ Hora inicial (ventana de 3 horas):",
                               min_value=int(min_hour),
                               max_value=int(max_start_hour),
                               value=int(max_start_hour))

# opcional: minute slider para inicio más fino
start_minute = st.sidebar.selectbox("Minuto inicio:", [0, 15, 30, 45], index=0)

start_dt = dt.datetime.combine(selected_date, dt.time(int(start_hour), int(start_minute)))
end_dt = start_dt + dt.timedelta(hours=3)

st.sidebar.markdown(f"Mostrando ventana: **{start_dt.strftime('%Y-%m-%d %H:%M')}** → **{end_dt.strftime('%H:%M')}**")

# -----------------------
# Cargar sólo la ventana y resamplear (después de filtrar)
# -----------------------
with st.spinner("Cargando datos (solo la ventana seleccionada)..."):
    df_window = load_window(CSV_FILE, start_dt, end_dt)

if df_window.empty:
    st.warning("No hay datos en esa ventana de 3 horas.")
    st.stop()

# resamplear SOLO la ventana para evitar explosión de filas (por ejemplo 1s)
# si 'time' no es índice aún:
df_window = df_window.set_index("time").resample("1s").mean().reset_index()

# -----------------------
# Mostrar métricas y gráficos
# -----------------------
st.markdown(f"### 📍 Datos para {selected_date} — {start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')}")

# Métricas
latest = df_window.iloc[-1]
def safe(latest_row, col, fmt=":.2f", unit=""):
    if col in latest_row and not pd.isna(latest_row[col]):
        return f"{float(latest_row[col]):{fmt}}{unit}"
    return "N/A"

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🌡️ Temp", safe(latest, "temperature", ":.1f", " °C"))
c2.metric("💧 Humedad", safe(latest, "humidity", ":.1f", " %"))
c3.metric("⚠️ Anomaly", safe(latest, "anomaly", ":.2f", ""))
c4.metric("🌫️ BVOC", safe(latest, "bvoc", ":.1f", " ppb"))
c5.metric("🏭 IAQ", safe(latest, "iaq", ":.0f", " ppm"))

st.divider()

# Gráficas (cada una mostrará solo la ventana de 3h)
st.subheader("📈 Aceleración (RMS)")
st.altair_chart(plot_line(df_window, ["accXRMS", "accYRMS", "accZRMS"], "Aceleración RMS", "m/s²",
                          start_dt=start_dt, end_dt=end_dt), use_container_width=True)

st.subheader("🌡️ Temperatura")
st.altair_chart(plot_line(df_window, ["temperature"], "Temperatura", "°C",
                          start_dt=start_dt, end_dt=end_dt), use_container_width=True)

st.subheader("💧 Humedad")
st.altair_chart(plot_line(df_window, ["humidity"], "Humedad", "% HR",
                          start_dt=start_dt, end_dt=end_dt), use_container_width=True)

st.subheader("🌫️ BVOC")
st.altair_chart(plot_line(df_window, ["bvoc"], "BVOC", "ppb",
                          start_dt=start_dt, end_dt=end_dt), use_container_width=True)

st.subheader("🏭 IAQ")
st.altair_chart(plot_line(df_window, ["iaq"], "Calidad Aire", "ppm",
                          start_dt=start_dt, end_dt=end_dt), use_container_width=True)

st.subheader("⚠️ Anomaly Score")
st.altair_chart(plot_line(df_window, ["anomaly"], "Anomaly Score", "score",
