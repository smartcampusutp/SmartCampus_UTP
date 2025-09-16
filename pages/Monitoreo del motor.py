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
            y=alt.Y("valor:Q", title=y_label),
            color="variable:N"
        )
        .properties(width=600, height=300, title=title)
        .interactive()
    )
    return chart


df = load_csv(CSV_FILE)

if df is not None:
    st.markdown("## 🟢 Última Actualización de Sensores")

    latest = df.iloc[-1]

    # 🔹 Primera fila: Temp, Humedad, Presión, BVOC, IAQ
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🌡️ Temperatura", f"{latest['temperature']:.2f} °C")
    col2.metric("💧 Humedad", f"{latest['humidity']:.2f} %")
    col3.metric("🌬️ Presión", f"{latest['pressure_hPa']:.0f} hPa")
    col4.metric("🌫️ BVOC", f"{latest['bvoc']:.0f} ppb")
    col5.metric("🏭 IAQ", f"{latest['iaq']:.0f} ppm")

    st.divider()

    # 🔹 Segunda fila: Aceleraciones X, Y, Z en una sola columna
    st.markdown("### 📈 Aceleración RMS")
    col_acc = st.columns(1)[0]
    col_acc.metric("Eje X", f"{latest['accXRMS']:.2f}")
    col_acc.metric("Eje Y", f"{latest['accYRMS']:.2f}")
    col_acc.metric("Eje Z", f"{latest['accZRMS']:.2f}")

    st.divider()

    # 🔹 Gráficas
    st.subheader("📈 Aceleración (RMS)")
    chart = plot_line(df, ["accXRMS", "accYRMS", "accZRMS"], "Aceleración RMS", y_label="m/s² (RMS)")
    st.altair_chart(chart, use_container_width=True)

    st.subheader("🌡️ Temperatura")
    chart = plot_line(df, ["temperature"], "Temperatura", y_label="°C")
    st.altair_chart(chart, use_container_width=True)

    st.subheader("💧 Humedad")
    chart = plot_line(df, ["humidity"], "Humedad", y_label="% HR")
    st.altair_chart(chart, use_container_width=True)

    st.subheader("🌫️ BVOC")
    chart = plot_line(df, ["bvoc"], "BVOC", y_label="ppb")
    st.altair_chart(chart, use_container_width=True)

    st.subheader("🏭 IAQ")
    chart = plot_line(df, ["iaq"], "Índice de Calidad del Aire", y_label="ppm")
    st.altair_chart(chart, use_container_width=True)

    st.subheader("⚠️ Anomalía")
    st.dataframe(df[["time", "anomaly"]].tail(10))
    chart = plot_line(df, ["anomaly"], "Anomaly Score", y_label="Score")
    st.altair_chart(chart, use_container_width=True)
