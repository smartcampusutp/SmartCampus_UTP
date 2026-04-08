import streamlit as st
import pandas as pd
import folium
import numpy as np
import requests

from folium.plugins import MeasureControl, MousePosition
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

# ======================
# CONFIG
# ======================

REPO_API = "https://api.github.com/repos/smartcampusutp/SmartCampus_UTP/contents/Data/mapper"
RAW_BASE = "https://raw.githubusercontent.com/smartcampusutp/SmartCampus_UTP/main/Data/mapper/"

coords_map = {
    "GatewayELII":[9.02451, -79.53423],
    "GatewayFacilidades":[9.023413708152264,-79.53220188617708],
    "GatewaySistemas":[9.02196, -79.53221],
}

gateway_colors = {
    "GatewayELII": "red",
    "GatewayFacilidades": "blue",
    "GatewaySistemas": "green",
}

# ======================
# CACHE
# ======================

@st.cache_data(ttl=3600)
def load_data():
    try:
        files = requests.get(REPO_API).json()
    except:
        return pd.DataFrame()

    df_list = []

    for f in files:
        if f["name"].endswith(".csv"):
            try:
                df_temp = pd.read_csv(
                    RAW_BASE + f["name"],
                    engine="python",
                    on_bad_lines="skip"
                )
                df_list.append(df_temp)
            except:
                continue

    if len(df_list) == 0:
        return pd.DataFrame()

    return pd.concat(df_list, ignore_index=True)

df = load_data()

if df.empty:
    st.error("No hay datos")
    st.stop()

# ======================
# LIMPIEZA
# ======================

df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

# convertir fecha
df["time"] = pd.to_datetime(df["time"], errors="coerce")

df = df.dropna(subset=["latitude", "longitude", "time"])

# ======================
# FILTRO POR DIA
# ======================

st.sidebar.title("Filtros")

min_date = df["time"].dt.date.min()
max_date = df["time"].dt.date.max()

date_range = st.sidebar.date_input(
    "Rango de fechas",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# validar selección
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range

    df = df[
        (df["time"].dt.date >= start_date) &
        (df["time"].dt.date <= end_date)
    ]
else:
    st.warning("Selecciona un rango válido de fechas")

# ======================
# DISTANCIA
# ======================

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)

    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    c = 2*np.arctan2(np.sqrt(a), np.sqrt(1-a))

    return R * c

# ======================
# DETECTAR GATEWAYS
# ======================

gateways = {}

gw_ids = set(col.split("_")[0] for col in df.columns if col.startswith("gw"))

for gw_id in gw_ids:

    name_col = f"{gw_id}_name"
    rssi_col = f"{gw_id}_rssi"
    snr_col  = f"{gw_id}_snr"

    if rssi_col not in df.columns:
        continue

    names = df[name_col].dropna().astype(str).unique()
    if len(names) == 0:
        continue

    gw_name = names[0]

    if gw_name not in coords_map:
        continue

    gateways[gw_name] = {
        "coords": coords_map[gw_name],
        "rssi_col": rssi_col,
        "snr_col": snr_col
    }

if len(gateways) == 0:
    st.error("No se detectaron gateways válidos")
    st.stop()

# ======================
# EXPANDIR DATOS
# ======================

records = []

for _, row in df.iterrows():
    for gw, g in gateways.items():

        rssi = pd.to_numeric(row.get(g["rssi_col"]), errors="coerce")
        snr  = pd.to_numeric(row.get(g["snr_col"]), errors="coerce")

        if pd.notna(rssi):

            d = haversine(
                row.latitude,
                row.longitude,
                g["coords"][0],
                g["coords"][1]
            )

            records.append({
                "lat": row.latitude,
                "lon": row.longitude,
                "gateway": gw,
                "rssi": rssi,
                "snr": snr,
                "distance": d
            })

data = pd.DataFrame(records)

# ======================
# FILTRO DISTANCIA (SUAVE)
# ======================

dist_max = st.sidebar.slider("Distancia máxima (m)", 500, 5000, 2000)

data = data[data["distance"] <= dist_max]

# ======================
# CONTROLES
# ======================

st.sidebar.title("Capas")

show_path = st.sidebar.checkbox("Trayectoria completa", True)

controls = {}

for gw in gateways:
    with st.sidebar.expander(f"{gw}", True):
        controls[gw] = {
            "points": st.checkbox("Points", True, key=f"{gw}_p"),
            "links": st.checkbox("Links", False, key=f"{gw}_l"),
            "rings": st.checkbox("Rings", False, key=f"{gw}_r"),
        }

# ======================
# MAPA
# ======================

m = folium.Map(
    location=[df.latitude.mean(), df.longitude.mean()],
    zoom_start=16,
    max_zoom=22,
    tiles=None
)

folium.TileLayer("cartodbpositron").add_to(m)

folium.TileLayer(
    tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
    attr="Google",
    name="Satellite"
).add_to(m)

folium.LayerControl().add_to(m)

# ======================
# TRAYECTORIA BASE
# ======================

if show_path:
    for _, row in df.iterrows():
        folium.CircleMarker(
            [row["latitude"], row["longitude"]],
            radius=2,
            color="gray",
            fill=True,
            fill_opacity=0.4
        ).add_to(m)

# ======================
# GATEWAYS
# ======================

for gw, g in gateways.items():
    color = gateway_colors.get(gw, "gray")

    folium.Marker(
        g["coords"],
        icon=folium.Icon(color=color, icon="signal"),
        popup=gw
    ).add_to(m)

# ======================
# POINTS + LINKS
# ======================

for _, row in data.iterrows():

    gw = row["gateway"]
    rssi = row["rssi"]

    # color por señal
    if rssi > -85:
        point_color = "green"
    elif rssi > -100:
        point_color = "orange"
    else:
        point_color = "red"

    line_color = gateway_colors.get(gw, "gray")

    if controls[gw]["points"]:
        folium.CircleMarker(
            [row["lat"], row["lon"]],
            radius=4 + ((rssi + 120) / 8),
            color=point_color,
            fill=True,
            fill_opacity=0.9,
            popup=f"""
            Gateway: {gw}<br>
            RSSI: {rssi}<br>
            SNR: {row['snr']}<br>
            Dist: {round(row['distance'],1)} m
            """
        ).add_to(m)

    if controls[gw]["links"]:
        folium.PolyLine(
            [[row["lat"], row["lon"]], gateways[gw]["coords"]],
            color=line_color,
            weight=3,
            opacity=0.7
        ).add_to(m)

# ======================
# EXTRA
# ======================

MeasureControl().add_to(m)
MousePosition().add_to(m)

# ======================
# UI
# ======================

st.title("LoRaWAN Coverage Map")

st_folium(m, width=1400, height=750)
