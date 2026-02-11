import paho.mqtt.client as mqtt
import json
import csv
import os
import time
import base64
import requests
from datetime import datetime

BROKER = "127.0.0.1"
PORT = 1883
TOPIC = "application/+/device/+/event/up"

BASE_DIR = "DATA_SMARTCAMPUS"

# GitHub
GITHUB_REPO = "smartcampusutp/SmartCampus_UTP"
GITHUB_BRANCH = "main"
GITHUB_TOKEN = "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"
GITHUB_BASE_DIR = "Data"   # <<< CARPETA REMOTA EN GITHUB
GITHUB_PUSH_INTERVAL = 60  # segundos

last_push_time = time.time()


if not os.path.isdir(BASE_DIR):
    os.makedirs(BASE_DIR)
    print(f"[INFO] Directorio base creado: {BASE_DIR}")


def safe_name(name):
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(name))

historial_voltajes = []

def calcular_porcentaje_bateria(voltage_mv, ventana=5):
    if voltage_mv is None:
        return 0

    historial_voltajes.append(voltage_mv)
    if len(historial_voltajes) > ventana:
        historial_voltajes.pop(0)

    v = sum(historial_voltajes) / len(historial_voltajes)

    if v >= 4200:
        return 100
    if v <= 3350:
        return 0

    tabla = [
        (4200,100),(4050,95),(3950,90),(3850,85),
        (3780,80),(3740,70),(3710,50),(3680,30),
        (3650,20),(3600,15),(3500,10),(3400,5),(3350,0)
    ]

    for i in range(len(tabla)-1):
        hi_mv, hi_pct = tabla[i]
        lo_mv, lo_pct = tabla[i+1]
        if v >= lo_mv:
            return round(lo_pct + (v - lo_mv) * (hi_pct - lo_pct) / (hi_mv - lo_mv), 1)
    return 0

ISLA_FIELDS = [
    "time", "deviceName", "temperature", "humidity",
    "pressure_hPa", "battery_mV", "battery_pct", "rssi", "snr"
]

CLASS_LABELS = ["Background Noise", "People", "Vehicle"]

RUIDO_FIELDS = (
    ["time", "deviceName", "Lmax_dB", "Lmax_class", "LAeq1min_dB"]
    + [f"LAeq_{c}" for c in CLASS_LABELS]
    + [f"pct_{c}" for c in CLASS_LABELS]
    + ["P10_dB", "P50_dB", "P90_dB", "rssi", "snr"]
)


def get_file_sha(path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    r = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    return r.json().get("sha") if r.status_code == 200 else None

def push_to_github(local_path, remote_path):
    if not os.path.exists(local_path):
        print(f"[WARN] No existe: {local_path}")
        return

    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode()

    data = {
        "message": f"Update {remote_path}",
        "content": content,
        "branch": GITHUB_BRANCH
    }

    sha = get_file_sha(remote_path)
    if sha:
        data["sha"] = sha

    r = requests.put(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/{remote_path}",
        headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        },
        json=data
    )

    if r.status_code not in (200, 201):
        print(f"[GITHUB ERROR] {remote_path}")
        print("Status:", r.status_code)
        print(r.text)
    else:
        print(f"[GITHUB OK] {remote_path}")


def on_connect(client, userdata, flags, rc):
    print("[MQTT] Conectado")
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    global last_push_time

    data = json.loads(msg.payload.decode())

    
    device_info = data.get("deviceInfo", {})

    application_name = device_info.get("applicationName", "UNKNOWN_APP")
    device_profile   = device_info.get("deviceProfileName", "UNKNOWN_PROFILE")
    device_name      = device_info.get("deviceName", "UNKNOWN_DEVICE")

    app_name = safe_name(application_name)

    print(f"[UPLINK] App: {application_name} | Device: {device_name}")

    
    obj = data.get("object", {})

    rx = data.get("rxInfo", [{}])[0]
    rssi = rx.get("rssi")
    snr  = rx.get("snr")

    
    now = datetime.now()
    ts  = now.strftime("%Y-%m-%d %H:%M:%S")
    day = now.strftime("%Y-%m-%d")

    
    app_dir = os.path.join(BASE_DIR, app_name)

    if not os.path.isdir(app_dir):
        os.makedirs(app_dir)
        print(f"[INFO] Nueva aplicación local → {application_name}")

    csv_name = f"{app_name}_{day}.csv"
    archivo = os.path.join(app_dir, csv_name)
    write_header = not os.path.exists(archivo)

    
    if device_profile == "heltec_nodes":

        batt = obj.get("battery_mV")

        row = {
            "time": ts,
            "deviceName": device_name,
            "temperature": obj.get("temperature"),
            "humidity": obj.get("humidity"),
            "pressure_hPa": obj.get("pressure_hPa"),
            "battery_mV": batt,
            "battery_pct": calcular_porcentaje_bateria(batt),
            "rssi": rssi,
            "snr": snr
        }

        with open(archivo, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=ISLA_FIELDS)
            if write_header:
                w.writeheader()
            w.writerow(row)

    
    elif device_profile == "heltec_sound":

        row = {
            "time": ts,
            "deviceName": device_name,
            "Lmax_dB": obj.get("Lmax_dB"),
            "Lmax_class": obj.get("max_class_label"),
            "LAeq1min_dB": obj.get("LAeq1min_dB"),
            "rssi": rssi,
            "snr": snr
        }

        for c in CLASS_LABELS:
            row[f"LAeq_{c}"] = obj.get("LAeq_per_class_dB", {}).get(c, 0)
            row[f"pct_{c}"]  = obj.get("class_percentage", {}).get(c, 0)

        row.update({
            "P10_dB": obj.get("percentiles_dB", {}).get("P10"),
            "P50_dB": obj.get("percentiles_dB", {}).get("P50"),
            "P90_dB": obj.get("percentiles_dB", {}).get("P90")
        })

        with open(archivo, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=RUIDO_FIELDS)
            if write_header:
                w.writeheader()
            w.writerow(row)

    
    if time.time() - last_push_time >= GITHUB_PUSH_INTERVAL:
        for app in os.listdir(BASE_DIR):
            local_csv = os.path.join(BASE_DIR, app, f"{app}_{day}.csv")
            remote_csv = f"{GITHUB_BASE_DIR}/{app}/{app}_{day}.csv"
            push_to_github(local_csv, remote_csv)
        last_push_time = time.time()


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.loop_forever()
