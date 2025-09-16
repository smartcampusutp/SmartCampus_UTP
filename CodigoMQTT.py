import paho.mqtt.client as mqtt
import json
import csv
import os
from datetime import datetime
import base64
import requests
import time

# ================================
# CONFIGURACIÓN MQTT
# ================================
BROKER = "######"
PORT = ####
TOPIC = "application/+/device/+/event/up"

# ================================
# CONFIGURACIÓN DE ARCHIVO CSV
# ================================
LOG_DIR = "uplink_logs"   #Carpeta De Guardado Local
os.makedirs(LOG_DIR, exist_ok=True)

CSV_FILE = os.path.join(LOG_DIR, "uplinks.csv")   #Guardado y Nombre del archivo

# 🔹 Nombres de columnas consistentes
FIELDS = ["time", "deviceName", "temperature", "humidity", "pressure_hPa", "battery_mV", "rssi", "snr"]

csv_file = open(CSV_FILE, "a", newline="")
csv_writer = csv.DictWriter(csv_file, fieldnames=FIELDS)

# Escribir encabezado si el archivo está vacío
if os.stat(CSV_FILE).st_size == 0:
    csv_writer.writeheader()

# ================================
# CONFIGURACIÓN GITHUB API
# ================================
GITHUB_REPO = "smartcampusutp/SmartCampus_UTP"  # Cambiar por tu repo
GITHUB_FILE = "Data/uplinks.csv"
GITHUB_BRANCH = "main"
GITHUB_TOKEN = "###############"  # 

# Intervalo de subida a GitHub en segundos
GITHUB_PUSH_INTERVAL = 600  # 10 minutos
last_push_time = 0  # Hora del último push

def push_to_github():
    """Sube el archivo CSV al repositorio de GitHub usando la API"""
    print("[⏳] Iniciando subida a GitHub...")
    try:
        with open(CSV_FILE, "rb") as f:
            content = f.read()
        b64_content = base64.b64encode(content).decode()

        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}

        resp = requests.get(url, headers=headers)
        sha = resp.json().get("sha") if resp.status_code == 200 else None

        data = {
            "message": f"Update uplinks.csv at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": b64_content,
            "branch": GITHUB_BRANCH,
        }
        if sha:
            data["sha"] = sha

        r = requests.put(url, headers=headers, json=data)

        if r.status_code in (200, 201):
            print(f"[✓] CSV actualizado en GitHub correctamente ({datetime.now().strftime('%H:%M:%S')})")
        else:
            print(f"[✗] Error al subir a GitHub: {r.json()}")
    except Exception as e:
        print(f"[✗] Excepción durante push a GitHub: {e}")

# ================================
# CALLBACKS MQTT
# ================================
def on_connect(client, userdata, flags, rc):
    print("Conectado al broker MQTT" if rc == 0 else f"Error de conexión: {rc}")
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    global last_push_time

    try:
        payload = msg.payload.decode()
        data = json.loads(payload)

        # Hora local
        time_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Capturar deviceName correctamente
        device_name = data.get("deviceName") or data.get("deviceInfo", {}).get("deviceName", "Unknown")

        row = {
            "time": time_local,  # columna consistente
            "deviceName": device_name,
            "temperature": data.get("object", {}).get("temperature"),
            "humidity": data.get("object", {}).get("humidity"),
            "pressure_hPa": data.get("object", {}).get("pressure_hPa"),
            "battery_mV": data.get("object", {}).get("battery_mV"),
            "rssi": data.get("rxInfo", [{}])[0].get("rssi"),
            "snr": data.get("rxInfo", [{}])[0].get("loRaSNR"),
        }

        # Guardar fila en CSV local
        csv_writer.writerow(row)
        csv_file.flush()
        print(f"[✓] Fila añadida al CSV: {row}")

        # Subir a GitHub solo si ha pasado el intervalo
        current_time = time.time()
        if current_time - last_push_time >= GITHUB_PUSH_INTERVAL:
            push_to_github()
            last_push_time = current_time
        else:
            remaining = int(GITHUB_PUSH_INTERVAL - (current_time - last_push_time))
            print(f"[ℹ️] Próximo push a GitHub en {remaining} segundos")

    except Exception as e:
        print("[✗] Error procesando mensaje:", e)

# ================================
# INICIO DEL CLIENTE MQTT
# ================================
print(f"[+] Guardando datos en: {CSV_FILE}")
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_forever()
