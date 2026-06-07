# =================================================================
# Práctica 2: Integración Total MQTT (ESP32 ↔ Python)
# Fecha: 08/05/26
# =================================================================
# Objetivo:
# Establecer la conexión WiFi y MQTT en la ESP32 para publicar la
# telemetría de sensores y recibir comandos remotos que se aplican
# mediante la capa HAL.
# =================================================================
# Integrantes de equipo:
# - Alvarez Guevara Estefania Guadalupe (ID: 23240077)
# - Rangel Hernandez Aldo (ID: 23240272)
# - Reyes Gutierrez Pablo Alberto (ID: 23240055)
# =================================================================

from dispositivos import SensorBox, ActuatorBox
from umqtt.simple import MQTTClient
import machine, network, time, json, ubinascii

WIFI_SSID = 'PR11'
WIFI_PASS = 'Pavo1234'
SERVIDOR_MQTT = '10.51.4.79' 
PUERTO_MQTT = 1883
ID_CLIENTE = ubinascii.hexlify(machine.unique_id())

sensores = SensorBox()
actuadores = ActuatorBox()
cliente = None

def conectar_wifi():
    # La ESP32 se conecta a la misma red local donde corre Mosquitto.
    print("Conectando WiFi", end="")
    interfaz = network.WLAN(network.STA_IF)
    interfaz.active(True)
    interfaz.connect(WIFI_SSID, WIFI_PASS)
    while not interfaz.isconnected():
        print(".", end="")
        time.sleep(0.5)
    print(" IP:", interfaz.ifconfig()[0])

def establecer_conexion_mqtt():
    global cliente
    # Cliente MQTT con ID hexadecimal para evitar conflictos de bytes crudos.
    cliente = MQTTClient(ID_CLIENTE, SERVIDOR_MQTT, PUERTO_MQTT)
    cliente.connect()
    print("MQTT Conectado")

def enrutar_topico(topico, mensaje):
    # Callback de suscripción:
    # 1) decodifica tópico y payload,
    # 2) identifica el comando,
    # 3) delega la acción física a la HAL.
    topico_dec = topico.decode().strip()
    mensaje_dec = mensaje.decode().strip()
    
    # Bitácora de depuración para verificar qué comando recibió el broker.
    print(f"\n>>> ORDEN RECIBIDA DEL BROKER | Tópico: {topico_dec} | Comando: {mensaje_dec}")
    
    if topico_dec == 'vestaguard/control/vibrador':
        actuadores.activar_vibrador(mensaje_dec == 'ON')
        
    elif topico_dec == 'vestaguard/control/rgb':
        if mensaje_dec == 'ROJO':
            actuadores.set_color_rgb(255, 0, 0)
        elif mensaje_dec == 'VERDE':
            actuadores.set_color_rgb(0, 255, 0)
        elif mensaje_dec == 'APAGAR':
            actuadores.set_color_rgb(0, 0, 0)

try:
    conectar_wifi()
    establecer_conexion_mqtt()
    
    # La ESP32 escucha comandos; las acciones físicas siempre pasan por la HAL.
    cliente.set_callback(enrutar_topico)
    cliente.subscribe(b'vestaguard/control/vibrador')
    cliente.subscribe(b'vestaguard/control/rgb')
    
    ultimo_envio = time.ticks_ms()

    while True:
        # check_msg() evita bloquear el bucle mientras se esperan comandos.
        cliente.check_msg()
        
        ahora = time.ticks_ms()
        if time.ticks_diff(ahora, ultimo_envio) >= 2000:
            # Publicación periódica de telemetría en formato JSON.
            datos = {
                "pir": sensores.leer_movimiento(),
                "distancia_cm": round(sensores.leer_distancia(), 1),
                "aceleracion_y": sensores.leer_aceleracion()
            }
            cliente.publish(b'vestaguard/telemetria/sensores', json.dumps(datos))
            ultimo_envio = ahora

except KeyboardInterrupt:
    # Cierre seguro: apagar actuadores y desconectar MQTT.
    actuadores.estado_seguro()
    cliente.disconnect()
