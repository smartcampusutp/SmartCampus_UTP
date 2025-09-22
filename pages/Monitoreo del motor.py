import streamlit as st
import pandas as pd
import altair as alt
import math
import datetime as dt

CSV_FILE = "Data_udp/smartcampusudp.csv"

st.set_page_config(page_title="Dashboard Sensores", layout="wide")
st.title("📊 Estado bomba agua helada cuarto de máquinas")

# --- Cargar CSV ---
@st.cache_data(ttl=30)
def load_csv(path):
    df = pd.read_csv(path, engine="pyarrow")
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
    return df

df = load_csv(CSV_FILE)

# --- Función para calcular dominio Y ---
def compute_y_domain(series):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return None
    min_val, max_val = s.min(), s.max()
    margin = max((max_val - min_val) * 0.005, 1)
    return (math.floor(min_val - margin), math.ceil(max_val + margin))

# --- Función para graficar ---
def plot_line(df, y_cols, title="", y_label="Valor"):
    if df.empty:
        return alt.Chart(pd.DataFrame({"time": [], "valor": [], "variable": []})).mark_line()

    df_melted = df.melt("time", value_vars=y_cols, var_name="variable", value_name="valor")
    df_melted = df_melted.dropna(subset=["time", "valor"])
    if df_melted.empty:
        return alt.Chart(pd.DataFrame({"time": [], "valor": [], "variable": []})).mark_line()

    min_time = df["time"].min()
    max_time = df["time"].max()

    y_domain = compute_y_domain(df_melted["valor"])

    chart = (
        alt.Chart(df_melted)
        .mark_line(clip=True)
        .encode(
            x=alt.X("time:T", scale=alt.Scale(domain=[min_time, max_time]),
                    axis=alt.Axis(format="%H:%M", labelAngle=0)),
            y=alt.Y("valor:Q", title=y_label,
                    scale=alt.Scale(domain=y_domain) if y_domain else alt.Undefined),
            color="variable:N",
        )
        .properties(width=800, height=300, title=title)
        .interactive()
    )
    return chart

# ==========================
# 🔹 Filtro de día y hora
# ==========================
if not df.empty and "time" in df.columns:
    df["date"] = df["time"].dt.date
    available_dates = sorted(df["date"].dropna().unique())

    # Selector de día
    selected_date = st.date_input(
        "📅 Selecciona el día:",
        value=available_dates[-1],
        min_value=min(available_dates),
        max_value=max(available_dates)
    )

    # Filtrar solo ese día
    df_day = df[df["date"] == pd.to_datetime(selected_date).date()]

    if df_day.empty:
        st.warning("⚠️ No hay datos para este día.")
    else:
        # Selector de hora para ventana de 3h
        min_hour = df_day["time"].dt.hour.min()
        max_hour = df_day["time"].dt.hour.max()
        start_hour = st.slider("⏰ Selecciona hora inicial (3h por ventana):",
                               min_value=int(min_hour), max_value=int(max_hour-1),
                               value=int(max_hour)-3 if max_hour >= 3 else int(min_hour))

        start_time = dt.datetime.combine(selected_date, dt.time(start_hour, 0))
        end_time = start_time + dt.timedelta(hours=3)

        # Filtrar rango horario
        df_window = df_day[(df_day["time"] >= start_time) & (df_day["time"] < end_time)]

        # Resamplear solo este rango
        if not df_window.empty:
            df_window = df_window.set_index("time").resample("1s").mean().reset_index()

            st.success(f"Mostrando datos de {start_time.strftime('%H:%M')} a {end_time.strftime('%H:%M')}")

            # --- Métricas ---
            latest = df_window.iloc[-1]

            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("🌡️ Temp", f"{latest['temperature']:.1f} °C" if not pd.isna(latest['temperature']) else "N/A")
            col2.metric("💧 Humedad", f"{latest['humidity']:.1f} %" if not pd.isna(latest['humidity']) else "N/A")
            col3.metric("⚠️ Anomalía", f"{latest['anomaly']:.2f}" if not pd.isna(latest['anomaly']) else "N/A")
            col4.metric("🌫️ BVOC", f"{latest['bvoc']:.1f} ppb" if not pd.isna(latest['bvoc']) else "N/A")
            col5.metric("🏭 IAQ", f"{latest['iaq']:.0f} ppm" if not pd.isna(latest['iaq']) else "N/A")

            st.divider()

            # --- Gráficos ---
            st.subheader("📈 Aceleración (RMS)")
            st.altair_chart(plot_line(df_window, ["accXRMS", "accYRMS", "accZRMS"], "Aceleración RMS", y_label="m/s²"),
                            use_container_width=True)

            st.subheader("🌡️ Temperatura")
            st.altair_chart(plot_line(df_window, ["temperature"], "Temperatura", y_label="°C"),
                            use_container_width=True)

            st.subheader("💧 Humedad")
            st.altair_chart(plot_line(df_window, ["humidity"], "Humedad", y_label="% HR"),
                            use_container_width=True)

            st.subheader("🌫️ BVOC")
            st.altair_chart(plot_line(df_window, ["bvoc"], "BVOC", y_label="ppb"),
                            use_container_width=True)

            st.subheader("🏭 IAQ")
            st.altair_chart(plot_line(df_window, ["iaq"], "Calidad Aire", y_label="ppm"),
                            use_container_width=True)

            st.subheader("⚠️ Anomalía de Vibración")
            st.altair_chart(plot_line(df_window, ["anomaly"], "Anomaly Score", y_label="Score"),
                            use_container_width=True)
        else:
            st.warning("⚠️ No hay datos en esta ventana de 3h.")
else:
    st.warning("⚠️ No se encontraron datos en el archivo CSV.")
