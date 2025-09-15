import paho.mqtt.client as mqtt
import json
import csv
import os
from datetime import datetime

# Configuración del broker MQTT
BROKER = "127.0.0.1"
PORT = 1883
TOPIC = "application/+/device/+/event/up"

# Carpeta para los CSV
LOG_DIR = "uplink_logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Nombre único para el CSV (1 solo archivo)
CSV_FILE = os.path.join(LOG_DIR, "uplinks.csv")

# Campos a guardar
FIELDS = ["time_local", "deviceName", "temperature", "humidity", "pressure_hPa", "battery_mV", "rssi", "snr"]

# Abrir archivo una sola vez
csv_file = open(CSV_FILE, "a", newline="")
csv_writer = csv.DictWriter(csv_file, fieldnames=FIELDS)

# Si el archivo está vacío, escribir encabezado
if os.stat(CSV_FILE).st_size == 0:
    csv_writer.writeheader()


def on_connect(client, userdata, flags, rc):
    print("Conectado al broker MQTT" if rc == 0 else f"Error de conexión: {rc}")
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())

    # Obtener la hora local de la Raspberry Pi
    time_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = {
        "time_local": time_local,
        "deviceName": data.get("deviceName", ""),
        "temperature": data.get("object", {}).get("temperature"),
        "humidity": data.get("object", {}).get("humidity"),
        "pressure_hPa": data.get("object", {}).get("pressure_hPa"),
        "battery_mV": data.get("object", {}).get("battery_mV"),
        "rssi": data.get("rxInfo", [{}])[0].get("rssi"),
        "snr": data.get("rxInfo", [{}])[0].get("loRaSNR"),
    }
    csv_writer.writerow(row)
    csv_file.flush()

    print(f"[✓] Fila añadida al CSV: {row}")


# Cliente MQTT
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print(f"[+] Guardando datos en: {CSV_FILE}")
client.connect(BROKER, PORT, 60)
client.loop_forever()