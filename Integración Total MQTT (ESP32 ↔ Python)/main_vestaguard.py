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
from dispositivos import Dispositivos, tiempo_ms_actual, diferencia_tiempo_ms
try:
    import secrets
except ImportError:
    secrets = None
    print('[ARRANQUE] AVISO: secrets.py no encontrado. El chaleco operará sin red.')
_CFG_SENSORES = {'pin_trigger_ultrasonico': 5, 'pin_echo_ultrasonico': 18, 'pin_pir': 19, 'pin_boton_panico': 32, 'pin_sda_mpu6050': 21, 'pin_scl_mpu6050': 22, 'pin_tx_gps': 16, 'pin_rx_gps': 17, 'habilitar_gps': True, 'umbral_distancia_alerta_cm': 120.0, 'umbral_distancia_amenaza_cm': 80.0, 'umbral_aceleracion_caida': 2.5, 'calibracion_pir_ms': 2000}
_CFG_ACTUADORES = {'pin_vibrador': 25, 'pines_vibradores_secundarios': [27], 'pin_led_r': 13, 'pin_led_b': 33, 'pin_relevador': 23, 'habilitar_buzzer': False, 'pin_buzzer': 26, 'timeout_seguridad_ms': 15000, 'modo_silencioso': False}
TEMA_TELEMETRIA = b'vestaguard/telemetria/sensores'
TEMA_SOS = b'vestaguard/alerta/sos'
TEMA_IA_COMANDO = b'vestaguard/ia/comando'
TEMA_CTRL_MOTORS = b'vestaguard/control/motores'
TEMA_CTRL_RGB = b'vestaguard/control/rgb'
TEMA_CTRL_RELE = b'vestaguard/control/relevador'
TEMA_CTRL_SILENC = b'vestaguard/control/silencio'
TEMA_DISPARO = b'vestaguard/control/camara_disparo'
ESTADO_NORMAL = 0
ESTADO_VIGILANCIA = 1
ESTADO_ALERTA = 2
ESTADO_AMENAZA = 3
ESTADO_EMERGENCIA = 4
TIEMPO_CONFIRM_VIGILANCIA_MS = 3000
TIEMPO_CONFIRM_ALERTA_MS = 5000
INTERVALO_TELEMETRIA_MS = 500
INTERVALO_MANTENIMIENTO_MS = 5000
INTERVALO_DISPARO_MS = 10000  # Enfriamiento para no saturar la camara
runtime = {'activo': True, 'estado_fsm': ESTADO_NORMAL, 'modo_silencioso': False, 'lectura_sensores': {}, 'inicio_presencia_ms': None, 'cliente_mqtt': None, 'wifi_ok': False, 'sos_enviado': False, 'ultimo_disparo_ms': 0}

def conectar_wifi():
    if not secrets:
        return False
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        print('[WiFi] Conexión previa detectada con éxito. IP:', wlan.ifconfig()[0])
        runtime['wifi_ok'] = True
        return True
    print('[WiFi] Estado de fondo ocupado detectado. Reiniciando driver de red...')
    wlan.active(False)
    time.sleep(1.0)
    gc.collect()
    wlan.active(True)
    ssid = getattr(secrets, 'SSID', getattr(secrets, 'SSID_WIFI', ''))
    pw = getattr(secrets, 'CONTRASENA', getattr(secrets, 'CONTRASENA_WIFI', ''))
    print('[WiFi] Conectando a la red:', ssid)
    wlan.connect(ssid, pw)
    intentos = 0
    while not wlan.isconnected() and intentos < 20:
        time.sleep_ms(500)
        intentos += 1
    if wlan.isconnected():
        print('[WiFi] Conexión establecida con éxito. IP:', wlan.ifconfig()[0])
        runtime['wifi_ok'] = True
    else:
        print('[WiFi] Error crítico: No se pudo conectar al punto de acceso. Modo local activo.')
    return wlan.isconnected()

def _callback_mqtt(topico, mensaje, dispositivos):
    try:
        t = topico.decode('utf-8')
        m = mensaje.decode('utf-8').strip()
        mu = m.upper()
        print(f'[MQTT-RX] {t} → {mu}')
        if t == TEMA_IA_COMANDO.decode():
            if mu == 'ALERTA_TOTAL':
                dispositivos.activar_panico_total()
                runtime['estado_fsm'] = ESTADO_EMERGENCIA
            elif mu == 'VIBRACION_FUERTE':
                dispositivos.activar_alerta_critica()
                if runtime['estado_fsm'] < ESTADO_AMENAZA:
                    runtime['estado_fsm'] = ESTADO_AMENAZA
            elif mu == 'MANTENER':
                pass
        elif t == TEMA_CTRL_MOTORS.decode():
            if mu == 'ON':
                dispositivos.activar_alerta_suave()
            else:
                dispositivos.mostrar_estado_normal()
        elif t == TEMA_CTRL_RELE.decode():
            if mu == 'ON':
                dispositivos.activar_estrobo_emergencia(600)
            else:
                dispositivos.desactivar_estrobo_emergencia()
        elif t == TEMA_CTRL_RGB.decode():
            colores = {'ROJO': (True, False, False), 'VERDE': (False, True, False), 'AZUL': (False, False, True), 'AMARILLO': (True, True, False), 'APAGAR': (False, False, False), 'OFF': (False, False, False)}
            if mu in colores:
                dispositivos.controlar_led_rgb(*colores[mu])
        elif t == TEMA_CTRL_SILENC.decode():
            runtime['modo_silencioso'] = mu == 'ON'
            print('[CTRL] Modo silencioso:', runtime['modo_silencioso'])
    except Exception as e:
        print('[MQTT-CB] Error:', e)

def configurar_mqtt(dispositivos):
    if not runtime['wifi_ok'] or not secrets:
        return None
    host = getattr(secrets, 'MQTT_HOST', getattr(secrets, 'HOST_MQTT', '127.0.0.1'))
    puerto = int(getattr(secrets, 'MQTT_PORT', getattr(secrets, 'PUERTO_MQTT', 1883)))
    cid = b'vestaguard_esp32_' + ubinascii.hexlify(machine.unique_id())
    cliente = MQTTClient(cid, host, port=puerto, keepalive=60)
    cliente.set_callback(lambda t, m: _callback_mqtt(t, m, dispositivos))
    try:
        cliente.connect()
        for tema in (TEMA_IA_COMANDO, TEMA_CTRL_MOTORS, TEMA_CTRL_RGB, TEMA_CTRL_RELE, TEMA_CTRL_SILENC):
            cliente.subscribe(tema)
        print(f'[MQTT] Conectado a {host}:{puerto}')
        return cliente
    except Exception as e:
        print('[MQTT] Error de conexion:', e)
        return None

def _aplicar_estado_fsm(dispositivos, nuevo_estado):
    if runtime['modo_silencioso'] and nuevo_estado < ESTADO_EMERGENCIA:
        if nuevo_estado >= ESTADO_AMENAZA:
            dispositivos.activar_alerta_critica()
            dispositivos.controlar_led_rgb(True, False, False)
        elif nuevo_estado >= ESTADO_ALERTA:
            dispositivos.activar_alerta_suave()
            dispositivos.controlar_led_rgb(True, False, True)
        else:
            dispositivos.mostrar_estado_normal()
        runtime['estado_fsm'] = nuevo_estado
        return
    if nuevo_estado == ESTADO_NORMAL:
        dispositivos.mostrar_estado_normal()
    elif nuevo_estado == ESTADO_VIGILANCIA:
        dispositivos.controlar_led_rgb(False, False, True)
    elif nuevo_estado == ESTADO_ALERTA:
        dispositivos.activar_alerta_suave()
        dispositivos.controlar_led_rgb(True, False, True)
    elif nuevo_estado == ESTADO_AMENAZA:
        dispositivos.activar_alerta_critica()
        dispositivos.controlar_led_rgb(True, False, False)
    elif nuevo_estado == ESTADO_EMERGENCIA:
        dispositivos.activar_panico_total()
        dispositivos.activar_estrobo_emergencia(500)
        dispositivos.controlar_led_rgb(True, False, False)
    runtime['estado_fsm'] = nuevo_estado

def _disparar_camara_autonomo(ahora_ms):
    cliente = runtime.get('cliente_mqtt')
    if cliente is None:
        return
    
    # Check cooldown
    if (ahora_ms - runtime['ultimo_disparo_ms']) >= INTERVALO_DISPARO_MS:
        try:
            print('[IA] Solicitando captura autonoma de la camara...')
            cliente.publish(TEMA_DISPARO, b'CAPTURAR')
            runtime['ultimo_disparo_ms'] = ahora_ms
        except Exception as e:
            print('[IA] Error al solicitar captura autonoma:', e)

def _evaluar_fsm(dispositivos, sensores, ahora_ms):
    estado_actual = runtime['estado_fsm']
    dist_cm = sensores.get('distancia_cm', 999.0)
    pir = bool(sensores.get('movimiento_pir', False))
    caida = bool(sensores.get('caida_detectada', False))
    panico = bool(sensores.get('boton_panico', False))
    if panico or caida:
        if estado_actual != ESTADO_EMERGENCIA:
            print('[FSM] → EMERGENCIA (panico/caida)')
            _aplicar_estado_fsm(dispositivos, ESTADO_EMERGENCIA)
            runtime['sos_enviado'] = False
        _disparar_camara_autonomo(ahora_ms)
        runtime['inicio_presencia_ms'] = None
        return
    if dist_cm <= _CFG_SENSORES['umbral_distancia_amenaza_cm'] and pir:
        if estado_actual < ESTADO_AMENAZA:
            print(f'[FSM] → AMENAZA (dist={dist_cm:.0f}cm + PIR)')
            _aplicar_estado_fsm(dispositivos, ESTADO_AMENAZA)
            _disparar_camara_autonomo(ahora_ms)
        runtime['inicio_presencia_ms'] = ahora_ms
        return
    if dist_cm <= _CFG_SENSORES['umbral_distancia_alerta_cm'] and pir:
        if estado_actual == ESTADO_NORMAL or estado_actual == ESTADO_VIGILANCIA:
            print(f'[FSM] → ALERTA (dist={dist_cm:.0f}cm)')
            _aplicar_estado_fsm(dispositivos, ESTADO_ALERTA)
            _disparar_camara_autonomo(ahora_ms)
            runtime['inicio_presencia_ms'] = ahora_ms
        elif estado_actual == ESTADO_ALERTA:
            if runtime['inicio_presencia_ms'] is not None:
                duracion = diferencia_tiempo_ms(ahora_ms, runtime['inicio_presencia_ms'])
                if duracion >= TIEMPO_CONFIRM_ALERTA_MS:
                    print('[FSM] → AMENAZA (alerta sostenida)')
                    _aplicar_estado_fsm(dispositivos, ESTADO_AMENAZA)
                    _disparar_camara_autonomo(ahora_ms)
        return
    if pir:
        if estado_actual == ESTADO_NORMAL:
            print('[FSM] → VIGILANCIA (PIR)')
            _aplicar_estado_fsm(dispositivos, ESTADO_VIGILANCIA)
            runtime['inicio_presencia_ms'] = ahora_ms
        elif estado_actual == ESTADO_VIGILANCIA:
            duracion = diferencia_tiempo_ms(ahora_ms, runtime.get('inicio_presencia_ms') or ahora_ms)
            if duracion >= TIEMPO_CONFIRM_VIGILANCIA_MS:
                print('[FSM] → ALERTA (PIR sostenido)')
                _aplicar_estado_fsm(dispositivos, ESTADO_ALERTA)
        return
    if estado_actual not in (ESTADO_AMENAZA, ESTADO_EMERGENCIA):
        if estado_actual != ESTADO_NORMAL:
            print('[FSM] → NORMAL')
            _aplicar_estado_fsm(dispositivos, ESTADO_NORMAL)
        runtime['inicio_presencia_ms'] = None

async def tarea_sensores(disp):
    while runtime['activo']:
        runtime['lectura_sensores'] = disp.obtener_estado_general()
        disp.alimentar_watchdog()
        await asyncio.sleep_ms(10)

async def tarea_fsm(disp):
    while runtime['activo']:
        sensores = runtime['lectura_sensores']
        if sensores:
            _evaluar_fsm(disp, sensores, tiempo_ms_actual())
            disp.aplicar_timeout_seguridad()
        await asyncio.sleep_ms(25)

async def tarea_telemetria():
    while runtime['activo']:
        cliente = runtime['cliente_mqtt']
        sensores = runtime['lectura_sensores']
        if cliente and sensores:
            datos = {k: v for k, v in sensores.items() if not isinstance(v, (bytes, bytearray)) and k not in ('imagen_b64', 'rostro')}
            datos['estado_fsm'] = runtime['estado_fsm']
            datos['modo_silencioso'] = runtime['modo_silencioso']
            try:
                cliente.publish(TEMA_TELEMETRIA, json.dumps(datos))
            except Exception as e:
                print('[MQTT-TX] Error:', e)
        await asyncio.sleep_ms(INTERVALO_TELEMETRIA_MS)

async def tarea_sos():
    while runtime['activo']:
        if runtime['estado_fsm'] == ESTADO_EMERGENCIA and (not runtime['sos_enviado']) and runtime['cliente_mqtt']:
            sensores = runtime['lectura_sensores']
            payload_sos = json.dumps({'origen': 'boton_panico' if sensores.get('boton_panico') else 'caida', 'lat': sensores.get('gps_latitud', 0.0), 'lon': sensores.get('gps_longitud', 0.0), 'timestamp': tiempo_ms_actual()})
            try:
                runtime['cliente_mqtt'].publish(TEMA_SOS, payload_sos, retain=True)
                print('[SOS] Mensaje de emergencia enviado.')
                runtime['sos_enviado'] = True
            except Exception as e:
                print('[SOS] Error al publicar:', e)
        await asyncio.sleep_ms(1000)

async def tarea_mqtt_rx():
    while runtime['activo']:
        cliente = runtime['cliente_mqtt']
        if cliente:
            try:
                cliente.check_msg()
            except OSError:
                pass
        await asyncio.sleep_ms(50)

async def tarea_mantenimiento():
    while runtime['activo']:
        gc.collect()
        await asyncio.sleep_ms(INTERVALO_MANTENIMIENTO_MS)

async def main_async():
    gc.collect()
    print()
    print('=' * 55)
    print(' VestaGuard — Chaleco Háptico Inteligente')
    print(' MicroPython · ESP32 · Sistemas Programables 2026')
    print('=' * 55)
    conectar_wifi()
    gc.collect()
    disp = Dispositivos(_CFG_SENSORES, _CFG_ACTUADORES)
    disp.mostrar_estado_normal()
    print('[HAL] Dispositivos inicializados.')
    runtime['cliente_mqtt'] = configurar_mqtt(disp)
    tareas = [asyncio.create_task(tarea_sensores(disp)), asyncio.create_task(tarea_fsm(disp)), asyncio.create_task(tarea_mantenimiento())]
    if runtime['cliente_mqtt']:
        tareas += [asyncio.create_task(tarea_telemetria()), asyncio.create_task(tarea_sos()), asyncio.create_task(tarea_mqtt_rx())]
    print(f'[VestaGuard] {len(tareas)} tareas activas. Sistema operativo.')
    try:
        await asyncio.gather(*tareas)
    finally:
        runtime['activo'] = False
        disp.estado_seguro()
        if runtime['cliente_mqtt']:
            try:
                runtime['cliente_mqtt'].disconnect()
            except Exception:
                pass
        print('[VestaGuard] Sistema detenido de forma segura.')

def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print('\n[VestaGuard] Interrupción manual.')
if __name__ == '__main__':
    main()