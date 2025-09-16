import streamlit as st
import pandas as pd
import altair as alt

# Ruta del archivo CSV único
CSV_FILE = "Data_udp/smartcampus(09-16-09).csv"  # Ajusta el nombre a tu archivo real

st.set_page_config(page_title="Dashboard Sensores", layout="wide")
st.title("📊 Dashboard - OPTA")
st.image("https://i.ibb.co/Dy8pxgj/ANGEL-MOTOR.png", caption=".")

# Cargar el CSV
@st.cache_data
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

# Función para graficar
def plot_line(df, y_cols, title=""):
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
            y=alt.Y("valor:Q", scale=alt.Scale(zero=False)),
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
        chart = plot_line(df, ["accXRMS", "accYRMS", "accZRMS"], "Aceleración RMS")
        st.altair_chart(chart, use_container_width=True)

    # 2️⃣ Temperatura
    with cols[1]:
        st.subheader("🌡️ Temperatura")
        chart = plot_line(df, ["temperature"], "Temperatura")
        st.altair_chart(chart, use_container_width=True)
        
    # 3️⃣ Humedad
    with cols[0]:
        st.subheader("💧 Humedad")
        chart = plot_line(df, ["humidity"], "Humedad")
        st.altair_chart(chart, use_container_width=True)

    # 4️⃣ BVOC
    with cols[1]:
        st.subheader("🌫️ Compuestos Orgánicos Volátiles")
        chart = plot_line(df, ["bvoc"], "BVOC")
        st.altair_chart(chart, use_container_width=True)

    # 🚨 Los últimos ocupan todo el ancho 🚨
    # 5️⃣ IAQ
    st.subheader("🏭 Índice de Calidad de Aire")
    chart = plot_line(df, ["iaq"], "Índice de Calidad del Aire")
    st.altair_chart(chart, use_container_width=True)

    # 6️⃣ Anomalía
    st.subheader("⚠️ Anomalía de Vibración")
    st.dataframe(df[["time", "anomaly"]].tail(10))
    chart = plot_line(df, ["anomaly"], "Anomaly Score")
    st.altair_chart(chart, use_container_width=True)
