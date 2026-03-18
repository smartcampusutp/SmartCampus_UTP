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
    "GatewayELII":[9.024833577337148,-79.53453540802003],
    "GatewayFacilidades":[9.023413708152264,-79.53220188617708],
}

# colores por gateway (🔥 clave)
gateway_colors = {
    "GatewayELII": "red",
    "GatewayFacilidades": "blue",
}

# ======================
# CACHE 1 HORA
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
df = df.dropna(subset=["latitude", "longitude"])

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
# FILTROS
# ======================

st.sidebar.title("Filtros")

rssi_min = st.sidebar.slider("RSSI mínimo", -120, -30, -100)
dist_max = st.sidebar.slider("Distancia máxima (m)", 0, 1500, 800)

if st.sidebar.button("🔄 Actualizar datos"):
    st.cache_data.clear()

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
# EXPANDIR
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

data = data[
    (data["rssi"] >= rssi_min) &
    (data["distance"] <= dist_max)
]

# ======================
# CONTROLES
# ======================

st.sidebar.title("Capas")

controls = {}

for gw in gateways:
    with st.sidebar.expander(f"{gw}", True):
        controls[gw] = {
            "points": st.checkbox("Points", True, key=f"{gw}_p"),
            "links": st.checkbox("Links", False, key=f"{gw}_l"),
            "rings": st.checkbox("Rings", False, key=f"{gw}_r"),
        }

# ======================
# MAPA (ESTILO ORIGINAL)
# ======================

m = folium.Map(
    location=[df.latitude.mean(), df.longitude.mean()],
    zoom_start=18,
    max_zoom=22,
    tiles=None
)

folium.TileLayer("cartodbpositron", name="Mapa").add_to(m)

folium.TileLayer(
    tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
    attr="Google",
    name="Satellite"
).add_to(m)

folium.LayerControl().add_to(m)

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
# RINGS
# ======================

rings = [150, 300, 600, 1000]

for gw, g in gateways.items():
    if controls[gw]["rings"]:
        color = gateway_colors.get(gw, "gray")

        for r in rings:
            folium.Circle(
                g["coords"],
                radius=r,
                color=color,
                weight=1.5,
                fill=False
            ).add_to(m)

# ======================
# POINTS + LINKS
# ======================

for _, row in data.iterrows():

    gw = row["gateway"]
    rssi = row["rssi"]

    # color por RSSI (points)
    if rssi > -85:
        point_color = "green"
    elif rssi > -100:
        point_color = "orange"
    else:
        point_color = "red"

    # color por gateway (links)
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
            weight=2.5,   # 🔥 más grueso
            opacity=0.7
        ).add_to(m)

# ======================
# CONTROLES EXTRA
# ======================

MeasureControl().add_to(m)
MousePosition().add_to(m)

# ======================
# UI
# ======================

st.title("LoRaWAN Map")

st_folium(m, width=1400, height=750)
