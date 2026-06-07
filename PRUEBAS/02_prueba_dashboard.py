import network
import time
import ujson
from umqtt.simple import MQTTClient

# 1. Ajustes
SSID = "PR11"
PASSWORD = "Pavo1234"
MQTT_BROKER = "10.254.179.79"
CLIENT_ID = "esp32_prueba_dashboard"

print("========================================")
print("  INICIANDO PRUEBA DE CONEXION A DASHBOARD")
print("========================================")

def al_recibir_mensaje(topic, msg):
    # Esta función se activa cuando le das clic a un botón en el Dashboard
    t = topic.decode("utf-8")
    m = msg.decode("utf-8")
    
    print("\n[RECIBIDO DEL DASHBOARD] Topic:", t, "| Mensaje:", m)
    
    if "control/rgb" in t:
        print("-> ACCION: Cambiando color del LED a", m)
    elif "ia/comando" in t:
        print("-> ACCION: Encendiendo VIBRADORES por comando:", m)
    elif "alerta/sos" in t:
        print("-> ACCION: ¡MODO PÁNICO ACTIVADO DESDE DASHBOARD!")

def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Conectando al WiFi...")
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)
            print(".", end="")
    print("\n[WIFI] IP:", wlan.ifconfig()[0])

def iniciar_prueba():
    conectar_wifi()
    
    cliente = MQTTClient(CLIENT_ID, MQTT_BROKER, keepalive=60)
    cliente.set_callback(al_recibir_mensaje)
    
    print("[MQTT] Conectando a Mosquitto...")
    cliente.connect()
    
    # Nos suscribimos para escuchar los botones del dashboard
    cliente.subscribe(b"vestaguard/control/#")
    cliente.subscribe(b"vestaguard/ia/comando")
    cliente.subscribe(b"vestaguard/alerta/sos")
    print("[MQTT] Suscrito a los botones del Dashboard. (Ya puedes darle clic en la página)")
    
    contador = 0
    try:
        while True:
            # 1. Checamos si el dashboard mandó alguna instrucción (botones)
            cliente.check_msg()
            
            # 2. Cada 3 segundos, mandamos datos falsos simulando sensores
            if contador % 3 == 0:
                fake_telemetry = {
                    "proximidad_cm": 45.5 + (contador % 10),  # Va cambiando un poco
                    "movimiento_pir": True if (contador % 2 == 0) else False,
                    "aceleracion_y": 0.98 + (contador % 3) * 0.1, # Datos del acelerómetro
                    "caida_detectada": False,
                    "boton_panico": False,
                    "bateria_pct": 85 - (contador % 5), # Batería simulada
                    "gps_latitud": 21.12345,
                    "gps_longitud": -101.67890,
                    "gps_fijado": True,
                    "estado_fsm": "VIGILANCIA"
                }
                
                payload = ujson.dumps(fake_telemetry)
                cliente.publish(b"vestaguard/telemetria/sensores", payload.encode("utf-8"))
                print(f"[ENVIADO] Datos al dashboard: Distancia={fake_telemetry['proximidad_cm']}cm, PIR={fake_telemetry['movimiento_pir']}")
            
            time.sleep(1)
            contador += 1
            
    except KeyboardInterrupt:
        print("\nPrueba detenida.")
        cliente.disconnect()

iniciar_prueba()
