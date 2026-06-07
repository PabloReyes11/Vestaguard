"""
PROYECTO: VestaGuard - Guardian de Espalda con Inteligencia Artificial
INTEGRANTES: Alvarez Guevara Estefania Guadalupe, Rangel Hernandez Aldo, Reyes Gutierrez Pablo Alberto
DESCRIPCION: Inicializacion segura de arranque para limpiar memoria, validar archivos criticos
             y habilitar un modo rescate sin ejecutar la logica principal.
"""

import gc


ARCHIVOS_REQUERIDOS = (
    "main.py",
    "secrets.py",
    "dispositivos.py",
)
PIN_BOTON_RESCATE = 0
NOMBRE_BANDERA_RESCATE = "MODO_RESCATE.flag"


def limpiar_memoria_inicial():
    """Parametros: ninguno.

    Hace: ejecuta recoleccion de basura al arrancar.
    Devuelve: nada.
    """
    gc.collect()


def validar_archivos_criticos():
    """Parametros: ninguno.

    Hace: valida presencia de archivos necesarios para arranque del proyecto.
    Devuelve: lista de faltantes.
    """
    faltantes = []
    for ruta_archivo in ARCHIVOS_REQUERIDOS:
        try:
            with open(ruta_archivo, "r"):
                pass
        except OSError:
            faltantes.append(ruta_archivo)
    if faltantes:
        print("[BOOT] Archivos faltantes:", faltantes)
    return faltantes


def configurar_modo_rescate():
    """Parametros: ninguno.

    Hace: activa bandera de rescate si el boton de BOOT/GPIO0 esta presionado.
    Devuelve: booleano indicando si se habilito el modo rescate.
    """
    try:
        from machine import Pin
    except Exception:
        return False

    try:
        boton = Pin(PIN_BOTON_RESCATE, Pin.IN, Pin.PULL_UP)
        if boton.value() == 0:
            with open(NOMBRE_BANDERA_RESCATE, "w") as archivo:
                archivo.write("1")
            print("[BOOT] Modo rescate habilitado")
            return True

        try:
            import os

            os.remove(NOMBRE_BANDERA_RESCATE)
        except OSError:
            pass
    except Exception as error_boot:
        print("[BOOT] No se pudo configurar modo rescate:", error_boot)
    return False


limpiar_memoria_inicial()
validar_archivos_criticos()
configuracion_rescate = configurar_modo_rescate()

if not configuracion_rescate:
    try:
        import network
        import time
        import secrets
        
        def conectar_wifi_temprano():
            print("[BOOT] Inicializando red inalambrica desde el arranque limpio...")
            wlan = network.WLAN(network.STA_IF)
            
            if not wlan.isconnected():
                wlan.active(True)
                
                ssid = getattr(secrets, "SSID", getattr(secrets, "SSID_WIFI", ""))
                pw   = getattr(secrets, "CONTRASENA", getattr(secrets, "CONTRASENA_WIFI", ""))
                
                if ssid:
                    wlan.connect(ssid, pw)
                    intentos = 0
                    while not wlan.isconnected() and intentos < 20:
                        time.sleep(0.5)
                        intentos += 1
                        
            if wlan.isconnected():
                print("[BOOT] WiFi Conectado con exito. IP:", wlan.ifconfig()[0])
            else:
                print("[BOOT] Advertencia: No se logro conexion inalambrica aun.")
            gc.collect()

        conectar_wifi_temprano()
    except Exception as e:
        print("[BOOT] Error al inicializar WiFi:", e)
        gc.collect()
