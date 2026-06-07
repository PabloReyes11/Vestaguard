"""
OBJETIVO: Integrar IA para capturar imagenes con ESP32-CAM y publicar evidencia visual por MQTT.
SE CARGA EN: ESP32-CAM con sensor OV3660.
RESPONSABLE PRINCIPAL: Alvarez Guevara Estefania Guadalupe.
APOYO DE LECTURA: Rangel revisa MQTT y Pablo revisa el montaje fisico.
INTEGRANTES: Alvarez Guevara Estefania Guadalupe (23240077), Rangel Hernandez Aldo (23240272), Reyes Gutierrez Pablo Alberto (23240055)
PROYECTO: VestaGuard

Modelo: no ejecuta IA local; la prediccion corre en el servidor Python.
Precision aproximada: 0.80 a 0.92 segun el dataset usado.
Tipo de prediccion: amenaza, vigilancia o normal a partir de un frame JPEG enviado por la ESP32-CAM.
"""



import gc
import json

try:
    import camera
except Exception:  # pragma: no cover - depende del firmware de la ESP32-CAM
    camera = None

try:
    import network
except Exception:  # pragma: no cover - compatibilidad con entornos de escritorio
    network = None

try:
    import time
except Exception:  # pragma: no cover - compatibilidad general
    time = None

try:
    import ubinascii
except Exception:  # pragma: no cover - compatibilidad de escritorio
    ubinascii = None

try:
    import ujson as json_micro
except Exception:  # pragma: no cover - usa json estandar fuera de MicroPython
    json_micro = json

try:
    from umqtt.simple import MQTTClient
except Exception:  # pragma: no cover - validacion de sintaxis fuera de MicroPython
    MQTTClient = None

try:
    import machine
except Exception:  # pragma: no cover - compatibilidad de escritorio
    machine = None

try:
    import secrets
except Exception:  # pragma: no cover - si no existe secrets.py se usan valores por defecto
    secrets = None


TEMA_DISPARO = b"vestaguard/control/camara_disparo"
TEMA_FRAME = b"vestaguard/camara/frame"
TEMA_ESTADO = b"vestaguard/camara/estado"

ANCHO = 320
ALTO = 240
CALIDAD_JPEG = 12
INTERVALO_HEARTBEAT_MS = 30000


def _obtener_parametro(nombre, valor_por_defecto):
    if secrets is None:
        return valor_por_defecto
    return getattr(secrets, nombre, valor_por_defecto)


def _obtener_credenciales_wifi():
    ssid = _obtener_parametro("SSID_WIFI", _obtener_parametro("SSID", ""))
    contrasena = _obtener_parametro("CONTRASENA_WIFI", _obtener_parametro("CONTRASENA", ""))
    return ssid, contrasena


def _obtener_credenciales_mqtt():
    host = _obtener_parametro("MQTT_HOST", _obtener_parametro("HOST_MQTT", "127.0.0.1"))
    puerto = int(_obtener_parametro("MQTT_PORT", _obtener_parametro("PUERTO_MQTT", 1883)))
    return host, puerto


def _id_cliente():
    if machine is None or ubinascii is None:
        return b"esp32cam_vestaguard"
    return b"esp32cam_" + ubinascii.hexlify(machine.unique_id())


def conectar_wifi():
    if network is None:
        raise RuntimeError("network no esta disponible en este entorno")

    ssid, contrasena = _obtener_credenciales_wifi()
    interfaz = network.WLAN(network.STA_IF)
    interfaz.active(True)
    try:
        interfaz.config(dhcp_hostname="esp32cam")
    except Exception:
        pass
    if not interfaz.isconnected():
        print("Conectando a WiFi...")
        interfaz.connect(ssid, contrasena)

    inicio = time.ticks_ms() if time is not None else 0
    while not interfaz.isconnected():
        if time is not None and time.ticks_diff(time.ticks_ms(), inicio) > 20000:
            raise RuntimeError("No fue posible conectar la ESP32-CAM a WiFi")
        if time is not None:
            time.sleep_ms(250)
    print("WiFi Conectado! IP:", interfaz.ifconfig()[0])
    return interfaz


def inicializar_camara():
    if camera is None:
        raise RuntimeError("El modulo camera no esta disponible en el firmware de la ESP32-CAM")

    if hasattr(camera, "init"):
        try:
            camera.init(0, format=getattr(camera, "JPEG", 0))
        except TypeError:
            camera.init(0)

    if hasattr(camera, "framesize") and hasattr(camera, "QVGA"):
        try:
            camera.framesize(camera.QVGA)
        except Exception:
            pass

    if hasattr(camera, "quality"):
        try:
            camera.quality(CALIDAD_JPEG)
        except Exception:
            pass

    if hasattr(camera, "flip"):
        try:
            camera.flip(1)
        except Exception:
            pass

    if hasattr(camera, "mirror"):
        try:
            camera.mirror(1)
        except Exception:
            pass


def capturar_jpeg():
    if machine is not None and time is not None:
        try:
            flash = machine.Pin(4, machine.Pin.OUT)
            flash.value(1)
            time.sleep(1)
        except Exception:
            flash = None
    else:
        flash = None

    gc.collect()
    imagen = camera.capture()

    if flash is not None:
        try:
            flash.value(0)
        except Exception:
            pass

    if isinstance(imagen, tuple):
        imagen = imagen[0]
    if not isinstance(imagen, (bytes, bytearray)):
        raise RuntimeError("La captura no devolvio bytes JPEG")
    return bytes(imagen)


def publicar_estado(cliente, evento, tamano_bytes=0):
    mensaje = {
        "evento": evento,
        "tamano_bytes": tamano_bytes,
        "ancho": ANCHO,
        "alto": ALTO,
    }
    cliente.publish(TEMA_ESTADO, json_micro.dumps(mensaje))


def publicar_frame(cliente, evento="alerta"):
    imagen = capturar_jpeg()
    imagen_b64 = ubinascii.b2a_base64(imagen).decode().strip() if ubinascii is not None else ""
    payload = {
        "imagen_b64": imagen_b64,
        "formato": "jpeg",
        "ancho": ANCHO,
        "alto": ALTO,
        "evento": evento,
        "origen": "esp32cam",
    }
    cliente.publish(TEMA_FRAME, json_micro.dumps(payload))
    publicar_estado(cliente, evento, len(imagen))
    return len(imagen)


def main():
    if MQTTClient is None:
        raise RuntimeError("MQTTClient no esta disponible en este entorno")

    print("Iniciando ESP32-CAM VestaGuard...")
    conectar_wifi()
    
    print("Inicializando camara...")
    inicializar_camara()

    host, puerto = _obtener_credenciales_mqtt()
    print("Conectando a MQTT en", host)
    cliente = MQTTClient(_id_cliente(), host, puerto)

    def _callback(topico, mensaje):
        topico_dec = topico.decode() if isinstance(topico, (bytes, bytearray)) else str(topico)
        mensaje_dec = mensaje.decode() if isinstance(mensaje, (bytes, bytearray)) else str(mensaje)
        print("MQTT Recibido:", topico_dec, "->", mensaje_dec)
        if topico_dec == TEMA_DISPARO.decode() and mensaje_dec.strip().upper() in {"1", "ON", "CAPTURAR", "FOTO"}:
            print("¡Tomando foto!")
            publicar_frame(cliente, evento="solicitud_remota")

    cliente.set_callback(_callback)
    cliente.connect()
    cliente.subscribe(TEMA_DISPARO)
    print("Suscrito a TEMA_DISPARO:", TEMA_DISPARO.decode())
    print("ESP32-CAM Lista y esperando ordenes...")

    ultimo_heartbeat = time.ticks_ms() if time is not None else 0

    try:
        while True:
            cliente.check_msg()
            ahora = time.ticks_ms() if time is not None else 0
            if time is not None and time.ticks_diff(ahora, ultimo_heartbeat) >= INTERVALO_HEARTBEAT_MS:
                publicar_estado(cliente, "en_linea", 0)
                ultimo_heartbeat = ahora
            if time is not None:
                time.sleep_ms(100)
    finally:
        try:
            publicar_estado(cliente, "apagado", 0)
        except Exception:
            pass
        cliente.disconnect()


if __name__ == "__main__":
    main()