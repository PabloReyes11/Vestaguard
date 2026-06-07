# =================================================================
# Práctica 2: Integración Total MQTT (ESP32 ↔ Python)
# Fecha: 08/05/26
# =================================================================
# Objetivo:
# Recibir la telemetría completa desde la ESP32 y publicar comandos
# MQTT hacia los motores, el LED RGB y el relevador de VestaGuard.
# =================================================================
# Integrantes de equipo:
# - Alvarez Guevara Estefania Guadalupe (ID: 23240077)
# - Rangel Hernandez Aldo (ID: 23240272)
# - Reyes Gutierrez Pablo Alberto (ID: 23240055)
# =================================================================

import json
from datetime import datetime

import paho.mqtt.client as mqtt

BROKER = "127.0.0.1"
PORT = 1883


def on_connect(client, userdata, flags, rc):
    print("Conectado a Mosquitto exitosamente.")
    client.subscribe("vestaguard/telemetria/#")


def on_message(client, userdata, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        datos = json.loads(msg.payload.decode())
    except Exception:
        datos = msg.payload.decode(errors="ignore")

    if msg.topic.endswith("/gps") and isinstance(datos, dict):
        latitud = datos.get("gps_latitud")
        longitud = datos.get("gps_longitud")
        altitud = datos.get("gps_altitud_m")
        satelites = datos.get("gps_satelites")
        fijado = datos.get("gps_fijado")
        print(f"[{timestamp}] GPS | Lat: {latitud} | Lon: {longitud}")
        print(f"Alt: {altitud}m | Sat: {satelites} | Fix: {fijado}")
        return

    if isinstance(datos, dict):
        pir = datos.get("pir")
        distancia = datos.get("distancia_cm")
        aceleracion = datos.get("aceleracion_y")
        panico = datos.get("boton_panico")
        gps_lat = datos.get("gps_latitud")
        gps_lon = datos.get("gps_longitud")
        print(f"[{timestamp}] PIR: {pir} | Dist: {distancia}cm")
        print(
            f"MPU: {aceleracion} | Panico: {panico} | GPS: {gps_lat}, {gps_lon}"
        )
    else:
        print(f"[{timestamp}] {msg.topic}: {datos}")


def publicar_comando(client, comando):
    comando = comando.strip().upper()

    if comando == "MOTOR_ON":
        client.publish("vestaguard/control/motores", "ON")
    elif comando == "MOTOR_OFF":
        client.publish("vestaguard/control/motores", "OFF")
    elif comando == "RGB_ROJO":
        client.publish("vestaguard/control/rgb", "ROJO")
    # elif comando == "RGB_VERDE": # EXCLUIDO: LED verde no se usa por hardware; se redirige a Azul en el firmware
    #     client.publish("vestaguard/control/rgb", "VERDE")
    elif comando == "RGB_AZUL":
        client.publish("vestaguard/control/rgb", "AZUL")
    elif comando == "RGB_OFF":
        client.publish("vestaguard/control/rgb", "APAGAR")
    elif comando == "RELE_ON":
        client.publish("vestaguard/control/relevador", "ON")
    elif comando == "RELE_OFF":
        client.publish("vestaguard/control/relevador", "OFF")
    elif comando == "TODO_ON":
        client.publish("vestaguard/control/motores", "ON")
        client.publish("vestaguard/control/rgb", "ROJO")
        client.publish("vestaguard/control/relevador", "ON")
    elif comando == "TODO_OFF":
        client.publish("vestaguard/control/motores", "OFF")
        client.publish("vestaguard/control/rgb", "APAGAR")
        client.publish("vestaguard/control/relevador", "OFF")
    else:
        print("Comando no reconocido.")
        return

    print(f"--> RED: Comando {comando} enviado a Mosquitto.")


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.loop_start()

try:
    print("Comandos disponibles:")
    print("MOTOR_ON, MOTOR_OFF, RGB_ROJO, RGB_AZUL (RGB_VERDE EXCLUIDO)")
    print("RGB_OFF, RELE_ON, RELE_OFF, TODO_ON, TODO_OFF")
    while True:
        comando = input("").strip()
        if comando:
            publicar_comando(client, comando)

except KeyboardInterrupt:
    client.loop_stop()
    client.disconnect()
