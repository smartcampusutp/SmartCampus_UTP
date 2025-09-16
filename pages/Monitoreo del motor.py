import streamlit as st
import pandas as pd
import altair as alt

# Ruta del archivo CSV único
CSV_FILE = "Data_udp/smartcampus(09-16-09).csv"  # Ajusta el nombre de tu archivo

st.set_page_config(page_title="Dashboard Sensores", layout="wide")
st.title("📊 Dashboard de Sensores en Tiempo Real")

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
    st.markdown("## 📍 Última Actualización")
    latest = df.iloc[-1]

    # Primera fila de métricas
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🌡️ Temperatura", f"{latest['temperature']:.1f} °C")
    with col2:
        st.metric("💧 Humedad", f"{la
