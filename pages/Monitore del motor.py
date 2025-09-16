import streamlit as st
import pandas as pd
import altair as alt

# Ruta del archivo CSV único
CSV_FILE = "data_udp/sensores.csv"  # Ajusta el nombre a tu archivo real

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
            y=alt.Y("valor:Q", title=y_label),  # 👈 aquí va el nombre del eje Y
            color="variable:N"
        )
        .properties(width=600, height=300, title=title)
        .interactive()
    )
    return chart

if df is not None:
    cols = st.columns(2)

    # 1️⃣ Aceleración
    with cols[0]:
        st.subheader("📈 Aceleración (RMS)")
        chart = plot_line(df, ["accXRMS", "accYRMS", "accZRMS"], "Aceleración RMS", y_label="m/s² (RMS)")
        st.altair_chart(chart, use_container_width=True)

    # 2️⃣ Temperatura
    with cols[1]:
        st.subheader("🌡️ Temperatura")
        chart = plot_line(df, ["temperature"], "Temperatura", y_label="°C")
        st.altair_chart(chart, use_container_width=True)

    # 3️⃣ Humedad
    with cols[0]:
        st.subheader("💧 Humedad")
        chart = plot_line(df, ["humidity"], "Humedad", y_label="% HR")
        st.altair_chart(chart, use_container_width=True)

    # 4️⃣ BVOC
    with cols[1]:
        st.subheader("🌫️ BVOC")
        chart = plot_line(df, ["bvoc"], "BVOC", y_label="ppb")
        st.altair_chart(chart, use_container_width=True)

    # 5️⃣ IAQ
    with cols[0]:
        st.subheader("🏭 IAQ")
        chart = plot_line(df, ["iaq"], "Índice de Calidad del Aire", y_label="IAQ Index")
        st.altair_chart(chart, use_container_width=True)

    # 6️⃣ Anomalía
    with cols[1]:
        st.subheader("⚠️ Anomalía")
        st.dataframe(df[["time", "anomaly"]].tail(10))
        chart = plot_line(df, ["anomaly"], "Anomaly Score", y_label="Score")
        st.altair_chart(chart, use_container_width=True)
