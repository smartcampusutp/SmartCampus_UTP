import streamlit as st
import pandas as pd
import altair as alt

# Ruta del archivo CSV único
CSV_FILE = "Data_udp/smartcampus(09-16-09).csv"  # Ajusta el nombre a tu archivo real

st.set_page_config(page_title="Dashboard Sensores", layout="wide")
st.title("📊 Dashboard de Sensores en Tiempo Real")

# Cargar el CSV
def load_csv(path):
    try:
        df = pd.read_csv(path)
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"])
        return df
    except Exception as e:
        st.error(f"Error leyendo archivo: {e}")
        return None

df = load_csv(CSV_FILE)

# Función para graficar con nombre de eje Y
def plot_line(df, y_cols, title="", y_label="Valor"):
    df_melted = df.melt("time", value_vars=y_cols, var_name="variable", value_name="valor")
    min_time = df["time"].min()
    max_time = df["time"].max()

    chart = (
        alt.Chart(df_melted)
        .mark_line(clip=True)
        .encode(
            x=alt.X(
                "time:T",
                scale=alt.Scale(domain=[min_time, max_time]),
                axis=alt.Axis(format="%H:%M", labelAngle=0, labelOverlap=True)
            ),
            y=alt.Y("valor:Q", title=y_label),  # 👈 nombre del eje Y
            color="variable:N"
        )
        .properties(width=600, height=300, title=title)
        .interactive()
    )
    return chart

if df is not None:
    st.markdown("## 🟢 Última Actualización de Sensores")

    latest = df.iloc[-1]

    # 🔹 Primera fila: Temp, Humedad, Presión, BVOC, IAQ
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.markdown(circle_metric("🌡️ Temp", f"{latest['temperature']:.1f}", "°C"), unsafe_allow_html=True)
    with col2: st.markdown(circle_metric("💧 Humedad", f"{latest['humidity']:.1f}", "%"), unsafe_allow_html=True)
    with col3: st.markdown(circle_metric("🌬️ Presión", f"{latest['pressure_hPa']:.0f}", "hPa"), unsafe_allow_html=True)
    with col4: st.markdown(circle_metric("🌫️ BVOC", f"{latest['bvoc']:.0f}", "ppb"), unsafe_allow_html=True)
    with col5: st.markdown(circle_metric("🏭 IAQ", f"{latest['iaq']:.0f}", "ppm"), unsafe_allow_html=True)

    st.divider()

    # 🔹 Segunda fila: Aceleraciones X, Y, Z en columna
    st.markdown("### 📈 Aceleración RMS")
    col_acc = st.columns(1)[0]
    with col_acc:
        st.markdown(circle_metric("X", f"{latest['accXRMS']:.2f}"), unsafe_allow_html=True)
        st.markdown(circle_metric("Y", f"{latest['accYRMS']:.2f}"), unsafe_allow_html=True)
        st.markdown(circle_metric("Z", f"{latest['accZRMS']:.2f}"), unsafe_allow_html=True)

    st.divider()

    cols = st.columns(2)

    # 1️⃣ Aceleración
    st.subheader("📈 Aceleración (RMS)")
    chart = plot_line(df, ["accXRMS", "accYRMS", "accZRMS"], "Aceleración RMS", y_label="m/s² (RMS)")
    st.altair_chart(chart, use_container_width=True)

    # 2️⃣ Temperatura
    st.subheader("🌡️ Temperatura")
    chart = plot_line(df, ["temperature"], "Temperatura", y_label="°C")
    st.altair_chart(chart, use_container_width=True)

    # 3️⃣ Humedad
    st.subheader("💧 Humedad")
    chart = plot_line(df, ["humidity"], "Humedad", y_label="% HR")
    st.altair_chart(chart, use_container_width=True)

    # 4️⃣ BVOC
    st.subheader("🌫️ Compuestos Orgánicos Volátiles")
    chart = plot_line(df, ["bvoc"], "BVOC", y_label="ppb")
    st.altair_chart(chart, use_container_width=True)

    # 5️⃣ IAQ
    st.subheader("🏭Índice de Calidad de Aire")
    chart = plot_line(df, ["iaq"], "Índice de Calidad del Aire", y_label="ICA")
    st.altair_chart(chart, use_container_width=True)

    # 6️⃣ Anomalía
    st.subheader("⚠️ Anomalía de Vibración")
    chart = plot_line(df, ["anomaly"], "Anomaly Score", y_label="Score")
    st.altair_chart(chart, use_container_width=True)
