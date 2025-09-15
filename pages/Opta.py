import streamlit as st
import pandas as pd
import os
from glob import glob
import altair as alt

BASE_DIR = "Data/data_udp/"
VARIABLES = {
    "aceleracion": ["accX", "accY", "accZ"],
    "temp_x100": ["temp_x100"],
    "hum_x100": ["hum_x100"],
    "bvoc_x100": ["bvoc_x100"],
    "iaq_x10": ["iaq_x10"],
    "anomaly_score": ["anomaly_score"],
    "fault": ["fault"],
}

st.set_page_config(page_title="Dashboard Sensores", layout="wide")
st.title("📊 Dashboard de Sensores en Tiempo Real")

# Función para listar archivos CSV de una variable
def list_csv_files(var):
    pattern = os.path.join(BASE_DIR, f"*{var}*.csv")
    return sorted(glob(pattern), key=os.path.getctime, reverse=True)

# Función para cargar CSV seleccionado
def load_csv(path):
    try:
        df = pd.read_csv(path)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception as e:
        st.error(f"Error leyendo archivo: {e}")
        return None

# Función para graficar con ajuste de escala del eje X
def plot_line(df, y_cols, title=""):
    df_melted = df.melt("timestamp", value_vars=y_cols, var_name="variable", value_name="valor")
    min_time = df["timestamp"].min()
    max_time = df["timestamp"].max()

    chart = (
        alt.Chart(df_melted)
        .mark_line(clip=True)
        .encode(
            x=alt.X(
                "timestamp:T",
                scale=alt.Scale(domain=[min_time, max_time]),
                axis=alt.Axis(
                    format="%H:%M",
                    tickMinStep=3600,  # ticks cada 1 hora
                    labelAngle=0,
                    labelOverlap=True
                )
            ),
            y=alt.Y("valor:Q", scale=alt.Scale(zero=False)),
            color="variable:N"
        )
        .properties(width=600, height=300, title=title)
        .interactive()
    )
    return chart

cols = st.columns(2)

for i, (var, cols_names) in enumerate(VARIABLES.items()):
    with cols[i % 2]:
        st.subheader(f"📈 {var}")
        files = list_csv_files(var)
        if not files:
            st.warning(f"No hay archivos disponibles para {var}.")
            continue
        # Selector para elegir archivo/día
        selection = st.selectbox(f"Selecciona archivo para {var}", options=files, format_func=lambda x: os.path.basename(x))
        df = load_csv(selection)
        if df is not None:
            st.caption(f"Archivo seleccionado: {os.path.basename(selection)}")
            if var == "fault":
                st.dataframe(df.tail(10))
            else:
                chart = plot_line(df, cols_names, var)
                st.altair_chart(chart, use_container_width=True)
