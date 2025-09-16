import streamlit as st
import pandas as pd
import altair as alt
import math

# Ruta del archivo CSV único
CSV_FILE = "Data_udp/smartcampusudp.csv"  # Ajusta el nombre de tu archivo

st.set_page_config(page_title="Dashboard Sensores", layout="wide")
st.title("📊 Estado bomba agua helada cuarto de máquinas")

# --- Cargar CSV ---
def load_csv(path):
    try:
        df = pd.read_csv(path)
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Error leyendo archivo: {e}")
        return None

df = load_csv(CSV_FILE)

# --- Helper: calcular dominio Y robusto ---
def compute_y_domain(series):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return None
    min_val = s.min()
    max_val = s.max()
    # margen 5% o al menos 1 unidad
    margin = max((max_val - min_val) * 0.05, 1)
    rango_min = math.floor(min_val - margin)
    rango_max = math.ceil(max_val + margin)
    if rango_min == rango_max:
        rango_max = rango_min + 1
    if rango_min > rango_max:
        rango_min, rango_max = rango_max - 1, rango_max
    return (rango_min, rango_max)

# --- Función para graficar con escala dinámica ---
def plot_line(df, y_cols, title="", y_label="Valor"):
    # preparar datos
    df_melted = df.melt("time", value_vars=y_cols, var_name="variable", value_name="valor")
    # convertir a numérico y eliminar filas inválidas
    df_melted["valor"] = pd.to_numeric(df_melted["valor"], errors="coerce")
    df_melted = df_melted.dropna(subset=["time", "valor"])
    if df_melted.empty:
        # gráfico vacío simple para evitar errores
        return alt.Chart(pd.DataFrame({"time": [], "valor": [], "variable": []})).mark_line().encode()

    # dominio tiempo
    min_time = df["time"].min()
    max_time = df["time"].max()
    # si solo hay un timestamp, expandir un poco para que no quede plano
    if pd.notna(min_time) and pd.notna(max_time) and min_time == max_time:
        min_time = min_time - pd.Timedelta(seconds=30)
        max_time = max_time + pd.Timedelta(seconds=30)

    # dominio Y
    y_domain = compute_y_domain(df_melted["valor"])

    # construir encodings condicionalmente
    if pd.notna(min_time) and pd.notna(max_time):
        x_enc = alt.X("time:T",
                      scale=alt.Scale(domain=[min_time, max_time]),
                      axis=alt.Axis(format="%H:%M", labelAngle=0, labelOverlap=True))
    else:
        x_enc = alt.X("time:T", axis=alt.Axis(format="%H:%M", labelAngle=0, labelOverlap=True))

    if y_domain:
        y_enc = alt.Y("valor:Q",
                      title=y_label,
                      scale=alt.Scale(domain=y_domain),
                      axis=alt.Axis(format="d"))
    else:
        y_enc = alt.Y("valor:Q", title=y_label, axis=alt.Axis(format="d"))

    chart = (
        alt.Chart(df_melted)
        .mark_line(clip=True)
        .encode(
            x=x_enc,
            y=y_enc,
            color="variable:N"
        )
        .properties(width=600, height=300, title=title)
        .interactive()
    )
    return chart

# --- Interfaz ---
if df is not None and not df.empty:
    st.markdown("## 📍 Valores en tiempo real")
    latest = df.iloc[-1]

    # función auxiliar para mostrar métricas de forma segura
    def safe_metric(latest_row, col_name, fmt):
        try:
            val = latest_row[col_name]
            if pd.isna(val):
                return "N/A"
            return f"{float(val):{fmt}}"
        except Exception:
            return "N/A"

    # Primera fila de métricas
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🌡️ Temperatura", f"{safe_metric(latest, 'temperature', '.1f')} °C")
    with col2:
        st.metric("💧 Humedad", f"{safe_metric(latest, 'humidity', '.1f')} %")
    with col3:
        st.metric("⚠️ Anomalía", f"{safe_metric(latest, 'anomaly', '.2f')}")
    with col4:
        st.metric("🌫️ BVOC", f"{safe_metric(latest, 'bvoc', '.1f')} ppb")
    with col5:
        st.metric("🏭 Calidad Aire (IAQ)", f"{safe_metric(latest, 'iaq', '.0f')} ppm")

    # Segunda fila de métricas (Aceleración RMS en X, Y, Z)
    col6, col7, col8 = st.columns(3)
    with col6:
        st.metric("📈 Aceleración X", f"{safe_metric(latest, 'accXRMS', '.2f')} m/s²")
    with col7:
        st.metric("📈 Aceleración Y", f"{safe_metric(latest, 'accYRMS', '.2f')} m/s²")
    with col8:
        st.metric("📈 Aceleración Z", f"{safe_metric(latest, 'accZRMS', '.2f')} m/s²")

    st.divider()

    # --- Gráficos ---
        st.subheader("📈 Aceleración (RMS)")
        st.altair_chart(plot_line(df, ["accXRMS", "accYRMS", "accZRMS"], "Aceleración RMS", y_label="m/s² (RMS)"),
                        use_container_width=True)
        st.subheader("🌡️ Temperatura")
        st.altair_chart(plot_line(df, ["temperature"], "Temperatura", y_label="°C"),
                        use_container_width=True)

        st.subheader("💧 Humedad")
        st.altair_chart(plot_line(df, ["humidity"], "Humedad", y_label="% HR"),
                        use_container_width=True)

        st.subheader("🌫️ Compuestos Orgánicos Volátiles")
        st.altair_chart(plot_line(df, ["bvoc"], "BVOC", y_label="ppb"),
                        use_container_width=True)

        st.subheader("🏭 Índice de Calidad de Aire")
        st.altair_chart(plot_line(df, ["iaq"], "Índice de Calidad del Aire", y_label="ppm"),
                        use_container_width=True)

        st.subheader("⚠️ Anomalía de Vibración")
        # mostrar tabla con últimas 10 anomalías
        if "anomaly" in df.columns:
        st.altair_chart(plot_line(df, ["anomaly"], "Anomaly Score", y_label="Score"),
                        use_container_width=True)

else:
    st.warning("⚠️ No se encontraron datos en el archivo CSV.")
