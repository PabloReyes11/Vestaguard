import network
import time
from umqtt.simple import MQTTClient

# 1. Ajusta tu IP aquí (la que vimos en ipconfig que es 10.254.179.79)
SSID = "PR11"
PASSWORD = "Pavo1234"
MQTT_BROKER = "10.254.179.79"
MQTT_CLIENT_ID = "esp32_prueba_aislada"

print("========================================")
print("   INICIANDO PRUEBA DE CONEXIÓN MQTT")
print("========================================")

def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Conectando al WiFi", SSID, "...")
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)
            print(".", end="")
    print("\n[WIFI] Conectado exitosamente. IP:", wlan.ifconfig()[0])

def conectar_mqtt():
    print("[MQTT] Intentando conectar a Mosquitto en la IP:", MQTT_BROKER)
    cliente = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, keepalive=60)
    
    try:
        cliente.connect()
        print("[MQTT] ¡ÉXITO! El ESP32 logró entrar a Mosquitto.")
        cliente.publish(b"vestaguard/prueba", b"Hola desde el ESP32, si lees esto la red esta perfecta!")
        print("[MQTT] Mensaje de prueba enviado al tópico 'vestaguard/prueba'")
        cliente.disconnect()
        print("[PRUEBA FINALIZADA CORRECTAMENTE]")
    except Exception as e:
        print("[ERROR] Falló la conexión a Mosquitto. Motivo:", e)
        print("-> Si dice 'ETIMEDOUT' o se queda trabado, significa que Windows Firewall SIGUE bloqueando la conexión.")
        print("-> Si dice 'ECONNREFUSED', significa que Mosquitto no está corriendo en la laptop.")

# Ejecutar las pruebas
conectar_wifi()
conectar_mqtt()
