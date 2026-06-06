"""
VestaGuard — Chaleco Háptico Inteligente para Seguridad Urbana

ARCHIVO   : main_vestaguard.py
SE CARGA  : ESP32 principal del chaleco (MicroPython)
RENOMBRAR : Copiar este archivo como main.py en el ESP32

DESCRIPCION:
  Punto de entrada DEFINITIVO del chaleco. Implementa el ciclo de control
  completo con concurrencia real (uasyncio), la capa HAL (dispositivos.py),
  la conexión WiFi y el cliente MQTT para publicar telemetría y recibir
  comandos remotos desde el servidor de IA y el dashboard Firebase.

  El sistema es FALL-SAFE: si no hay WiFi o MQTT, el chaleco sigue
  funcionando de forma local con todos sus sensores y actuadores.

ACTUADORES HAPTICOS:
  2 motores vibradores ERM tipo moneda:
    Motor 1 (Hombro Izquierdo) — GPIO 25
    Motor 2 (Hombro Derecho)   — GPIO 27

ARQUITECTURA:
  ┌─────────────────────────────────────┐
  │          ESP32 (este archivo)       │
  │  ┌──────────┐   ┌────────────────┐  │
  │  │ HAL      │   │ MQTT Client    │  │
  │  │ sensores │──▶│ publica cada   │  │
  │  │ actuat.  │   │ 500ms          │  │
  │  └──────────┘   └───────┬────────┘  │
  │       ▲               WiFi          │
  │       │                │            │
  │  FSM local          Broker          │
  │  (siempre activa)   Mosquitto       │
  └─────────────────────────────────────┘

LÓGICA DE ESTADOS FSM:
  NORMAL     : Sin amenaza detectada. LED Verde. Motores OFF.
  VIGILANCIA : PIR activo. Espera confirmación con ultrasónico.
  ALERTA     : Objeto < 120cm persiste. LED Amarillo. Hombros vibran (alternado).
  AMENAZA    : Objeto < 80cm confirmado o comando VIBRACION_FUERTE de IA.
               LED Rojo. Ambos hombros simultaneamente. Relevador.
  EMERGENCIA : Botón pánico o caída MPU6050 o comando ALERTA_TOTAL de IA.
               LED Rojo parpadeando. Hombros alternados rapido. Relevador + MQTT SOS.

TÓPICOS MQTT:
  PUB: vestaguard/telemetria/sensores   → estado completo cada 500ms
  PUB: vestaguard/alerta/sos            → solo en emergencia (QoS 1)
  SUB: vestaguard/ia/comando            → MANTENER | VIBRACION_FUERTE | ALERTA_TOTAL
  SUB: vestaguard/control/motores       → ON | OFF
  SUB: vestaguard/control/rgb           → ROJO | VERDE | AZUL | APAGAR
  SUB: vestaguard/control/relevador     → ON | OFF
  SUB: vestaguard/control/silencio      → ON | OFF

HARDWARE:
  Sensor HC-SR04   : GPIO 5 (Trig), GPIO 18 (Echo)
  Sensor PIR       : GPIO 19
  Sensor MPU6050   : GPIO 21 (SDA), GPIO 22 (SCL)
  GPS NEO-6M       : GPIO 16 (TX2), GPIO 17 (RX2)
  Botón Pánico     : GPIO 32 + R 4.7kΩ Pull-Up + C 100nF
  Motor 1 Hombro Izq: GPIO 25 (via 2N2222 + 1kΩ + 1N4148)
  Motor 2 Hombro Der: GPIO 27 (via 2N2222 + 1kΩ + 1N4148)
  LED RGB          : GPIO 13(R), 14(G), 33(B) + R 220Ω por canal
  Relevador 5V     : GPIO 23 (módulo con transistor integrado)

INTEGRANTES:
  Álvarez Guevara Estefanía Guadalupe  (23240077) — IA y ESP32-CAM
  Rangel Hernández Aldo                (23240272) — Firebase y Dashboard
  Reyes Gutiérrez Pablo Alberto        (23240055) — Conexiones Físicas y Hardware
DOCENTE  : Ing. Ma. Verónica Tapia Ibarra
MATERIA  : Sistemas Programables — ISC TecNM / IT León 2026
=======================================================================
"""

import gc
import json
import ubinascii
import machine
import network
import time

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from umqtt.simple import MQTTClient
from dispositivos import (
    Dispositivos,
    ConfiguracionSensores,
    ConfiguracionActuadores,
    tiempo_ms_actual,
    diferencia_tiempo_ms,
)

try:
    import secrets
except ImportError:
    secrets = None
    print("[ARRANQUE] AVISO: secrets.py no encontrado. El chaleco operará sin red.")


# CONFIGURACIÓN DE PINES (según TABLA_CONEXIONES_HARDWARE.md)
_CFG_SENSORES = {
    "pin_trigger_sr04":   5,
    "pin_echo_sr04":     18,
    "pin_pir":           19,
    "pin_boton_panico":  32,
    "i2c_sda":           21,
    "i2c_scl":           22,
    "uart_gps_tx":       16,
    "uart_gps_rx":       17,
    "umbral_distancia_alerta_cm":   120.0,
    "umbral_distancia_amenaza_cm":   80.0,
    "umbral_aceleracion_caida":       2.5,
    "calibracion_pir_ms":          2000,
}

_CFG_ACTUADORES = {
    "pin_motor_hombro_izq":  25,  # ⚠️ Via 2N2222 + R 1kΩ + Diodo 1N4148 — Hombro Izquierdo
    "pin_motor_hombro_der":  27,  # ⚠️ Via 2N2222 + R 1kΩ + Diodo 1N4148 — Hombro Derecho
    "pin_vibrador":          25,  # Alias HAL → Hombro Izquierdo
    "pines_vibradores_secundarios": [27],  # Alias HAL → Hombro Derecho
    "pin_led_rojo":          13,  # R 220Ω en serie
    # "pin_led_verde":         14,  # EXCLUIDO: No se usa en VestaGuard (solo Rojo y Azul)
    "pin_led_azul":          33,  # R 220Ω en serie
    "pin_led_r":             13,
    # "pin_led_g":             14,  # EXCLUIDO: Solo Rojo y Azul
    "pin_led_b":             33,
    "pin_relevador":         23,  # Módulo relay con transistor/diodo integrados
    "frecuencia_pwm_hz":    500,  # PWM para motores ERM de disco
    "duty_max":             1023,
    "timeout_actuadores_ms": 8000,
}

# TÓPICOS MQTT
TEMA_TELEMETRIA  = b"vestaguard/telemetria/sensores"
TEMA_SOS         = b"vestaguard/alerta/sos"
TEMA_IA_COMANDO  = b"vestaguard/ia/comando"
TEMA_CTRL_MOTORS = b"vestaguard/control/motores"
TEMA_CTRL_RGB    = b"vestaguard/control/rgb"
TEMA_CTRL_RELE   = b"vestaguard/control/relevador"
TEMA_CTRL_SILENC = b"vestaguard/control/silencio"

# CONSTANTES DE ESTADOS FSM
ESTADO_NORMAL     = 0
ESTADO_VIGILANCIA = 1
ESTADO_ALERTA     = 2
ESTADO_AMENAZA    = 3
ESTADO_EMERGENCIA = 4

# Cuánto tiempo confirmar presencia antes de escalar nivel
TIEMPO_CONFIRM_VIGILANCIA_MS = 3000   # 3 s con PIR activo → ALERTA
TIEMPO_CONFIRM_ALERTA_MS     = 5000   # 5 s cerca → AMENAZA
INTERVALO_TELEMETRIA_MS      = 500    # Publicar cada medio segundo
INTERVALO_MANTENIMIENTO_MS   = 5000   # gc.collect cada 5 s

# ESTADO GLOBAL DEL RUNTIME
runtime = {
    "activo":                True,
    "estado_fsm":            ESTADO_NORMAL,
    "modo_silencioso":       False,
    "lectura_sensores":      {},
    "inicio_presencia_ms":   None,
    "cliente_mqtt":          None,
    "wifi_ok":               False,
    "sos_enviado":           False,
}


# RED: WiFi
def conectar_wifi():
    """Conecta al WiFi de forma bloqueante. Timeout 10 segundos."""
    if not secrets:
        return False

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        runtime["wifi_ok"] = True
        return True

    ssid = getattr(secrets, "SSID", getattr(secrets, "SSID_WIFI", ""))
    pw   = getattr(secrets, "CONTRASENA", getattr(secrets, "CONTRASENA_WIFI", ""))
    print(f"[WIFI] Conectando a '{ssid}'...")
    wlan.connect(ssid, pw)

    for _ in range(20):
        if wlan.isconnected():
            print("[WIFI] Conectado →", wlan.ifconfig()[0])
            runtime["wifi_ok"] = True
            return True
        time.sleep_ms(500)

    print("[WIFI] No se pudo conectar. Modo local activo.")
    return False


# RED: MQTT
def _callback_mqtt(topico, mensaje, dispositivos):
    """Callback de mensajes MQTT entrantes (ISR ligera → solo delegar)."""
    try:
        t = topico.decode("utf-8")
        m = mensaje.decode("utf-8").strip()
        mu = m.upper()
        print(f"[MQTT-RX] {t} → {mu}")

        # ── Comandos de la IA
        if t == TEMA_IA_COMANDO.decode():
            if mu == "ALERTA_TOTAL":
                # Patrón: EMERGENCIA completa (4 motores + relevador)
                dispositivos.activar_panico_total()
                runtime["estado_fsm"] = ESTADO_EMERGENCIA
            elif mu == "VIBRACION_FUERTE":
                # Patrón: AMENAZA (ambos hombros simultáneamente)
                dispositivos.activar_alerta_critica()
                if runtime["estado_fsm"] < ESTADO_AMENAZA:
                    runtime["estado_fsm"] = ESTADO_AMENAZA
            elif mu == "MANTENER":
                pass  # No interrumpir la FSM local

        # ── Control remoto desde Dashboard
        elif t == TEMA_CTRL_MOTORS.decode():
            if mu == "ON":
                dispositivos.activar_alerta_suave()
            else:
                dispositivos.mostrar_estado_normal()

        elif t == TEMA_CTRL_RELE.decode():
            if mu == "ON":
                dispositivos.activar_estrobo_emergencia(600)
            else:
                dispositivos.desactivar_estrobo_emergencia()

        elif t == TEMA_CTRL_RGB.decode():
            colores = {
                "ROJO":   (True, False, False),
                # "VERDE":  (False, True, False),  # EXCLUIDO: Redirigido a Azul por hardware
                "VERDE":  (False, False, True),  # Redirigido a Azul
                "AZUL":   (False, False, True),
                # "AMARILLO": (True, True, False),  # EXCLUIDO: Redirigido a Violeta (Rojo + Azul)
                "AMARILLO": (True, False, True),  # Violeta
                "APAGAR": (False, False, False),
                "OFF":    (False, False, False),
            }
            if mu in colores:
                dispositivos.controlar_led_rgb(*colores[mu])

        elif t == TEMA_CTRL_SILENC.decode():
            runtime["modo_silencioso"] = (mu == "ON")
            print("[CTRL] Modo silencioso:", runtime["modo_silencioso"])

    except Exception as e:
        print("[MQTT-CB] Error:", e)


def configurar_mqtt(dispositivos):
    """Conecta al broker y suscribe a todos los tópicos de control."""
    if not runtime["wifi_ok"] or not secrets:
        return None

    host   = getattr(secrets, "MQTT_HOST",    getattr(secrets, "HOST_MQTT", "127.0.0.1"))
    puerto = int(getattr(secrets, "MQTT_PORT", getattr(secrets, "PUERTO_MQTT", 1883)))
    cid    = b"vestaguard_esp32_" + ubinascii.hexlify(machine.unique_id())

    cliente = MQTTClient(cid, host, port=puerto, keepalive=60)
    cliente.set_callback(lambda t, m: _callback_mqtt(t, m, dispositivos))

    try:
        cliente.connect()
        for tema in (TEMA_IA_COMANDO, TEMA_CTRL_MOTORS,
                     TEMA_CTRL_RGB, TEMA_CTRL_RELE, TEMA_CTRL_SILENC):
            cliente.subscribe(tema)
        print(f"[MQTT] Conectado a {host}:{puerto}")
        return cliente
    except Exception as e:
        print("[MQTT] Error de conexion:", e)
        return None


# LÓGICA FSM — SEGURIDAD LOCAL (independiente de la red)
def _aplicar_estado_fsm(dispositivos, nuevo_estado):
    """Aplica actuadores según el nuevo estado FSM."""
    if runtime["modo_silencioso"] and nuevo_estado < ESTADO_EMERGENCIA:
        # Modo silencioso: solo vibración, sin relevador
        if nuevo_estado >= ESTADO_AMENAZA:
            dispositivos.activar_alerta_critica()
            dispositivos.controlar_led_rgb(True, False, False)
        elif nuevo_estado >= ESTADO_ALERTA:
            dispositivos.activar_alerta_suave()
            dispositivos.controlar_led_rgb(True, False, True)  # EXCLUIDO Verde: Violeta (Rojo + Azul)
        else:
            dispositivos.mostrar_estado_normal()
        runtime["estado_fsm"] = nuevo_estado
        return

    if nuevo_estado == ESTADO_NORMAL:
        dispositivos.mostrar_estado_normal()       # LED azul (canal verde excluido), motores OFF
    elif nuevo_estado == ESTADO_VIGILANCIA:
        dispositivos.controlar_led_rgb(False, False, True)  # EXCLUIDO Verde: Azul = vigilando
    elif nuevo_estado == ESTADO_ALERTA:
        # Hombros vibran (aproximación detectada, sin confirmar quién)
        dispositivos.activar_alerta_suave()
        dispositivos.controlar_led_rgb(True, False, True)  # EXCLUIDO Verde: Violeta (Rojo + Azul)
    elif nuevo_estado == ESTADO_AMENAZA:
        # Ambos hombros simultaneamente + LED rojo (IA o sensores confirman amenaza)
        dispositivos.activar_alerta_critica()
        dispositivos.controlar_led_rgb(True, False, False)  # Rojo
    elif nuevo_estado == ESTADO_EMERGENCIA:
        # Pánico total: hombros alternados rápido + relevador estrobo
        dispositivos.activar_panico_total()
        dispositivos.activar_estrobo_emergencia(500)
        dispositivos.controlar_led_rgb(True, False, False)  # Rojo

    runtime["estado_fsm"] = nuevo_estado


def _evaluar_fsm(dispositivos, sensores, ahora_ms):
    """Máquina de estados finitos de seguridad local."""
    estado_actual = runtime["estado_fsm"]

    dist_cm       = sensores.get("distancia_cm", 999.0)
    pir           = bool(sensores.get("movimiento_pir", False))
    caida         = bool(sensores.get("caida_detectada", False))
    panico        = bool(sensores.get("boton_panico", False))

    # ── 1. EMERGENCIA siempre tiene prioridad
    if panico or caida:
        if estado_actual != ESTADO_EMERGENCIA:
            print("[FSM] → EMERGENCIA (panico/caida)")
            _aplicar_estado_fsm(dispositivos, ESTADO_EMERGENCIA)
            runtime["sos_enviado"] = False  # permitir reenvío SOS
        runtime["inicio_presencia_ms"] = None
        return

    # ── 2. Objeto muy cerca: AMENAZA   
    if dist_cm <= _CFG_SENSORES["umbral_distancia_amenaza_cm"] and pir:
        if estado_actual < ESTADO_AMENAZA:
            print(f"[FSM] → AMENAZA (dist={dist_cm:.0f}cm + PIR)")
            _aplicar_estado_fsm(dispositivos, ESTADO_AMENAZA)
        runtime["inicio_presencia_ms"] = ahora_ms
        return

    # ── 3. Proximidad media sostenida: ALERTA → AMENAZA
    if dist_cm <= _CFG_SENSORES["umbral_distancia_alerta_cm"] and pir:
        if estado_actual == ESTADO_NORMAL or estado_actual == ESTADO_VIGILANCIA:
            print(f"[FSM] → ALERTA (dist={dist_cm:.0f}cm)")
            _aplicar_estado_fsm(dispositivos, ESTADO_ALERTA)
            runtime["inicio_presencia_ms"] = ahora_ms
        elif estado_actual == ESTADO_ALERTA:
            if runtime["inicio_presencia_ms"] is not None:
                duracion = diferencia_tiempo_ms(ahora_ms, runtime["inicio_presencia_ms"])
                if duracion >= TIEMPO_CONFIRM_ALERTA_MS:
                    print("[FSM] → AMENAZA (alerta sostenida)")
                    _aplicar_estado_fsm(dispositivos, ESTADO_AMENAZA)
        return

    # ── 4. Solo PIR sin distancia crítica: VIGILANCIA
    if pir:
        if estado_actual == ESTADO_NORMAL:
            print("[FSM] → VIGILANCIA (PIR)")
            _aplicar_estado_fsm(dispositivos, ESTADO_VIGILANCIA)
            runtime["inicio_presencia_ms"] = ahora_ms
        elif estado_actual == ESTADO_VIGILANCIA:
            duracion = diferencia_tiempo_ms(ahora_ms, runtime.get("inicio_presencia_ms") or ahora_ms)
            if duracion >= TIEMPO_CONFIRM_VIGILANCIA_MS:
                print("[FSM] → ALERTA (PIR sostenido)")
                _aplicar_estado_fsm(dispositivos, ESTADO_ALERTA)
        return

    # ── 5. Sin amenaza → NORMAL (solo si no hay emergencia activa) ────
    if estado_actual not in (ESTADO_AMENAZA, ESTADO_EMERGENCIA):
        if estado_actual != ESTADO_NORMAL:
            print("[FSM] → NORMAL")
            _aplicar_estado_fsm(dispositivos, ESTADO_NORMAL)
        runtime["inicio_presencia_ms"] = None


# TAREAS ASÍNCRONAS (uasyncio)
async def tarea_sensores(disp):
    """Tarea 1: Lee todos los sensores cada 10 ms y guarda en runtime."""
    while runtime["activo"]:
        runtime["lectura_sensores"] = disp.obtener_estado_general()
        disp.alimentar_watchdog()
        await asyncio.sleep_ms(10)


async def tarea_fsm(disp):
    """Tarea 2: Evalúa la FSM local cada 25 ms."""
    while runtime["activo"]:
        sensores = runtime["lectura_sensores"]
        if sensores:
            _evaluar_fsm(disp, sensores, tiempo_ms_actual())
            disp.aplicar_timeout_seguridad()
        await asyncio.sleep_ms(25)


async def tarea_telemetria():
    """Tarea 3: Publica telemetría MQTT cada 500 ms."""
    while runtime["activo"]:
        cliente = runtime["cliente_mqtt"]
        sensores = runtime["lectura_sensores"]
        if cliente and sensores:
            # Construir payload limpio (sin imágenes ni bytes)
            datos = {k: v for k, v in sensores.items()
                     if not isinstance(v, (bytes, bytearray))
                     and k not in ("imagen_b64", "rostro")}
            datos["estado_fsm"] = runtime["estado_fsm"]
            datos["modo_silencioso"] = runtime["modo_silencioso"]
            try:
                cliente.publish(TEMA_TELEMETRIA, json.dumps(datos))
            except Exception as e:
                print("[MQTT-TX] Error:", e)
        await asyncio.sleep_ms(INTERVALO_TELEMETRIA_MS)


async def tarea_sos():
    """Tarea 4: Envía mensaje SOS por MQTT cuando hay emergencia (QoS 1 sim.)."""
    while runtime["activo"]:
        if (runtime["estado_fsm"] == ESTADO_EMERGENCIA
                and not runtime["sos_enviado"]
                and runtime["cliente_mqtt"]):
            sensores = runtime["lectura_sensores"]
            payload_sos = json.dumps({
                "origen":    "boton_panico" if sensores.get("boton_panico") else "caida",
                "lat":       sensores.get("gps_latitud", 0.0),
                "lon":       sensores.get("gps_longitud", 0.0),
                "timestamp": tiempo_ms_actual(),
            })
            try:
                runtime["cliente_mqtt"].publish(TEMA_SOS, payload_sos, retain=True)
                print("[SOS] Mensaje de emergencia enviado.")
                runtime["sos_enviado"] = True
            except Exception as e:
                print("[SOS] Error al publicar:", e)
        await asyncio.sleep_ms(1000)


async def tarea_mqtt_rx():
    """Tarea 5: Verifica mensajes MQTT entrantes (no bloqueante)."""
    while runtime["activo"]:
        cliente = runtime["cliente_mqtt"]
        if cliente:
            try:
                cliente.check_msg()
            except OSError:
                pass  # Red temporalmente caída — continuar
        await asyncio.sleep_ms(50)


async def tarea_mantenimiento():
    """Tarea 6: gc.collect periódico para evitar fragmentación del heap."""
    while runtime["activo"]:
        gc.collect()
        await asyncio.sleep_ms(INTERVALO_MANTENIMIENTO_MS)


# ARRANQUE PRINCIPAL
async def main_async():
    gc.collect()
    print()
    print("=" * 55)
    print(" VestaGuard — Chaleco Háptico Inteligente")
    print(" MicroPython · ESP32 · Sistemas Programables 2026")
    print("=" * 55)

    # 1. Inicializar HAL
    cfg_s = ConfiguracionSensores(**_CFG_SENSORES)
    cfg_a = ConfiguracionActuadores(**_CFG_ACTUADORES)
    disp  = Dispositivos(cfg_s, cfg_a)
    disp.mostrar_estado_normal()
    print("[HAL] Dispositivos inicializados.")

    # 2. Conectar red
    conectar_wifi()

    # 3. Conectar MQTT
    runtime["cliente_mqtt"] = configurar_mqtt(disp)

    # 4. Lanzar todas las corrutinas
    tareas = [
        asyncio.create_task(tarea_sensores(disp)),
        asyncio.create_task(tarea_fsm(disp)),
        asyncio.create_task(tarea_mantenimiento()),
    ]
    if runtime["cliente_mqtt"]:
        tareas += [
            asyncio.create_task(tarea_telemetria()),
            asyncio.create_task(tarea_sos()),
            asyncio.create_task(tarea_mqtt_rx()),
        ]

    print(f"[VestaGuard] {len(tareas)} tareas activas. Sistema operativo.")

    try:
        await asyncio.gather(*tareas)
    finally:
        runtime["activo"] = False
        disp.estado_seguro()
        if runtime["cliente_mqtt"]:
            try:
                runtime["cliente_mqtt"].disconnect()
            except Exception:
                pass
        print("[VestaGuard] Sistema detenido de forma segura.")


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[VestaGuard] Interrupción manual.")


if __name__ == "__main__":
    main()
