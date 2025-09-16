import streamlit as st
import pandas as pd
import altair as alt

# Ruta del archivo CSV único
CSV_FILE = "Data_udp/smartcampusudp.csv"  # Ajusta el nombre de tu archivo

st.set_page_config(page_title="Dashboard Sensores", layout="wide")
st.title("📊 Estado bomba agua helada cuarto de máquinas")

# --- Cargar CSV ---
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

# --- Función para graficar ---
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

if df is not None and not df.empty:
    # --- Última actualización ---
    st.markdown("## 📍 Valores en tiempo real")
    latest = df.iloc[-1]

    # Primera fila de métricas
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🌡️ Temperatura", f"{latest['temperature']:.1f} °C")
    with col2:
        st.metric("💧 Humedad", f"{latest['humidity']:.1f} %")
    with col3:
        st.metric("⚠️ Anomalía", f"{latest['anomaly']:.2f}")
    with col4:
        st.metric("🌫️ BVOC", f"{latest['bvoc']:.1f} ppb")
    with col5:
        st.metric("🏭 Calidad Aire (IAQ)", f"{latest['iaq']:.0f} ppm")

    # Segunda fila de métricas (Aceleración RMS en X, Y, Z)
    col6, col7, col8 = st.columns(3)
    with col6:
        st.metric("📈 Aceleración X", f"{latest['accXRMS']:.2f} m/s²")
    with col7:
        st.metric("📈 Aceleración Y", f"{latest['accYRMS']:.2f} m/s²")
    with col8:
        st.metric("📈 Aceleración Z", f"{latest['accZRMS']:.2f} m/s²")

    st.divider()

    # --- Gráficos ---
    cols = st.columns(2)

    with cols[0]:
        st.subheader("📈 Aceleración (RMS)")
        chart = plot_line(df, ["accXRMS", "accYRMS", "accZRMS"], "Aceleración RMS", y_label="m/s² (RMS)")
        st.altair_chart(chart, use_container_width=True)

    with cols[1]:
        st.subheader("🌡️ Temperatura")
        chart = plot_line(df, ["temperature"], "Temperatura", y_label="°C")
        st.altair_chart(chart, use_container_width=True)

    cols = st.columns(2)

    with cols[0]:
        st.subheader("💧 Humedad")
        chart = plot_line(df, ["humidity"], "Humedad", y_label="% HR")
        st.altair_chart(chart, use_container_width=True)

    with cols[1]:
        st.subheader("🌫️ BVOC")
        chart = plot_line(df, ["bvoc"], "BVOC", y_label="ppb")
        st.altair_chart(chart, use_container_width=True)

    cols = st.columns(2)

    with cols[0]:
        st.subheader("🏭 IAQ")
        chart = plot_line(df, ["iaq"], "Índice de Calidad del Aire", y_label="ppm")
        st.altair_chart(chart, use_container_width=True)

    with cols[1]:
        st.subheader("⚠️ Anomalía")
        st.dataframe(df[["time", "anomaly"]].tail(10))
        chart = plot_line(df, ["anomaly"], "Anomaly Score", y_label="Score")
        st.altair_chart(chart, use_container_width=True)

else:
    st.warning("⚠️ No se encontraron datos en el archivo CSV.")
