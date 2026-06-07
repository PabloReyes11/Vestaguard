"""
OBJETIVO: Persistencia de eventos VestaGuard en Firebase Realtime Database.
          Actua como puente entre MQTT local y la nube usando REST API de Firebase
          (metodo visto en clase con urequests y requests, sin SDK externo).
          Registra: telemetria, alertas de IA y estados de actuadores con timestamp.
SE CARGA EN: Laptop o PC con Python, junto al servidor_ia.py.
RESPONSABLE PRINCIPAL: Rangel Hernandez Aldo. (Firebase y Dashboard)
INTEGRANTES: Alvarez Guevara Estefania Guadalupe (23240077),
             Rangel Hernandez Aldo (23240272),
             Reyes Gutierrez Pablo Alberto (23240055)
PROYECTO: VestaGuard

Referencia tecnica:
  - Basado en los slides de la maestra: Sist Progr Unidad4 Firebase.txt
  - Usa REST API directa: PUT, POST (addto), PATCH, GET sobre
    https://[proyecto]-default-rtdb.firebaseio.com/[nodo].json
  - Estructura JSON en Firebase:
      vestaguard/
        sensores/        <- telemetria del chaleco
        alertas_ia/      <- decisiones del modelo
        actuadores/      <- estados de motores, rgb, relevador
        sistema/         <- conexion, camara, online/offline
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# ──────────────────────────────────────────────
# requests: libreria estandar de Python para HTTP
# (equivalente a urequests en MicroPython)
# ──────────────────────────────────────────────
try:
    import requests as _requests
    _HTTP_OK = True
except ImportError:
    _requests = None
    _HTTP_OK = False

try:
    import paho.mqtt.client as mqtt
    _MQTT_OK = True
except ImportError:
    mqtt = None
    _MQTT_OK = False


# ──────────────────────────────────────────────
# Configuracion: URL de Firebase y temas MQTT
# ──────────────────────────────────────────────

# URL base de Firebase Realtime Database (sin slash final)
# Ejemplo: https://vestaguard-default-rtdb.firebaseio.com
FIREBASE_URL = os.getenv(
    "FIREBASE_DB_URL",
    "https://vestaguard-XXXXXXX-default-rtdb.firebaseio.com"
)

# Temas MQTT del proyecto VestaGuard
TEMA_TELEMETRIA  = "vestaguard/telemetria/sensores"
TEMA_GPS         = "vestaguard/telemetria/gps"
TEMA_ALERTA_IA   = "vestaguard/ia/resultado"
TEMA_COMANDO_IA  = "vestaguard/ia/comando"
TEMA_CONTROL     = "vestaguard/control/#"
TEMA_CAM_ESTADO  = "vestaguard/camara/estado"
TEMA_DESDE_DASH  = "vestaguard/firebase/control/#"

MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))


# ──────────────────────────────────────────────
# Utilidades de tiempo
# ──────────────────────────────────────────────

def timestamp_iso() -> str:
    """Devuelve timestamp ISO 8601 en UTC — requerido por el E4."""
    return datetime.now(timezone.utc).isoformat()


def timestamp_local() -> str:
    """Devuelve timestamp legible en hora local."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ──────────────────────────────────────────────
# Capa Firebase — REST API directa
# (igual que en los ejemplos de la maestra con urequests.put / urequests.get)
# ──────────────────────────────────────────────

class FirebaseREST:
    """
    Parametros:
    - url_base: URL base de Firebase Realtime Database.
    - modo_demo: si True imprime en consola sin conectar a Firebase.

    Hace: encapsula PUT, POST (addto) y PATCH sobre la REST API de Firebase.
         Equivale a ufirebase.py pero ejecutado en PC con requests.
    Devuelve: instancia lista para guardar eventos.
    """

    # Codigos HTTP segun slides de la maestra (Sistemas Programables Firebase.txt)
    HTTP_OK      = 200
    HTTP_CREADO  = 201
    HTTP_ERROR   = 400

    def __init__(self, url_base: str = FIREBASE_URL, modo_demo: bool = False):
        self.url_base   = url_base.rstrip("/")
        self.modo_demo  = modo_demo
        self._conteo: Dict[str, int] = {
            "sensores": 0,
            "alertas_ia": 0,
            "actuadores": 0,
            "sistema": 0,
        }

        if not modo_demo and not _HTTP_OK:
            print("[Firebase] AVISO: 'requests' no esta instalado.")
            print("           Ejecuta: pip install requests")
            print("           Continuando en modo demo.")
            self.modo_demo = True

    def _url(self, ruta: str) -> str:
        """Construye la URL completa con sufijo .json (requerido por Firebase REST)."""
        return f"{self.url_base}/{ruta}.json"

    def _manejar_respuesta(self, resp, operacion: str) -> bool:
        """
        Parametros:
        - resp: objeto de respuesta HTTP.
        - operacion: nombre de la operacion (para el log).

        Hace: valida el codigo HTTP segun la tabla de la maestra.
        Devuelve: True si exitoso, False si error.
        """
        if resp.status_code in (self.HTTP_OK, self.HTTP_CREADO):
            return True
        if resp.status_code == 400:
            print(f"[Firebase] Error 400 en {operacion}: Peticion mal formada.")
        elif resp.status_code == 401:
            print(f"[Firebase] Error 401 en {operacion}: No autorizado.")
        elif resp.status_code == 403:
            print(f"[Firebase] Error 403 en {operacion}: Reglas de seguridad. "
                  "Verifica modo de prueba en la consola Firebase.")
        elif resp.status_code == 404:
            print(f"[Firebase] Error 404 en {operacion}: Ruta no existe.")
        elif 500 <= resp.status_code < 600:
            print(f"[Firebase] Error {resp.status_code} servidor Firebase. Reintenta.")
        else:
            print(f"[Firebase] Error desconocido {resp.status_code} en {operacion}.")
        return False

    def put(self, ruta: str, datos: Dict[str, Any]) -> bool:
        """
        Parametros:
        - ruta: nodo de Firebase (ej: 'vestaguard/sistema/estado').
        - datos: diccionario a sobreescribir (HTTP PUT).

        Hace: reemplaza el nodo con los datos indicados. Equivale a firebase.put().
        Devuelve: True si exitoso.
        """
        if self.modo_demo:
            print(f"[Firebase-DEMO] PUT /{ruta} = {json.dumps(datos, ensure_ascii=False)}")
            return True
        try:
            r = _requests.put(self._url(ruta), json=datos, timeout=8)
            ok = self._manejar_respuesta(r, f"PUT /{ruta}")
            if ok:
                print(f"[Firebase] PUT /{ruta} OK")
            return ok
        except Exception as exc:
            print(f"[Firebase] Conexion fallida en PUT /{ruta}: {exc}")
            return False

    def addto(self, ruta: str, datos: Dict[str, Any]) -> bool:
        """
        Parametros:
        - ruta: nodo de Firebase (ej: 'vestaguard/alertas_ia').
        - datos: diccionario a agregar como nuevo hijo con ID automatico (HTTP POST).

        Hace: agrega nuevo registro con ID unico — equivale a firebase.addto().
              Ideal para historial de eventos con timestamp.
        Devuelve: True si exitoso.
        """
        datos["timestamp"]       = timestamp_iso()
        datos["timestamp_local"] = timestamp_local()

        categoria = ruta.split("/")[-1]
        self._conteo[categoria] = self._conteo.get(categoria, 0) + 1

        if self.modo_demo:
            print(f"[Firebase-DEMO] [{timestamp_local()}] addto /{ruta}: {json.dumps(datos, ensure_ascii=False)}")
            return True
        try:
            r = _requests.post(self._url(ruta), json=datos, timeout=8)
            ok = self._manejar_respuesta(r, f"addto /{ruta}")
            if ok:
                print(f"[Firebase] addto /{ruta} OK (id: {r.json().get('name', '?')})")
            return ok
        except Exception as exc:
            print(f"[Firebase] Conexion fallida en addto /{ruta}: {exc}")
            return False

    def patch(self, ruta: str, campos: Dict[str, Any]) -> bool:
        """
        Parametros:
        - ruta: nodo de Firebase.
        - campos: diccionario con solo los campos a actualizar (HTTP PATCH).

        Hace: actualizacion parcial — equivale a firebase.patch().
        Devuelve: True si exitoso.
        """
        if self.modo_demo:
            print(f"[Firebase-DEMO] PATCH /{ruta}: {json.dumps(campos, ensure_ascii=False)}")
            return True
        try:
            r = _requests.patch(self._url(ruta), json=campos, timeout=8)
            ok = self._manejar_respuesta(r, f"PATCH /{ruta}")
            if ok:
                print(f"[Firebase] PATCH /{ruta} OK")
            return ok
        except Exception as exc:
            print(f"[Firebase] Conexion fallida en PATCH /{ruta}: {exc}")
            return False

    def get(self, ruta: str) -> Optional[Any]:
        """
        Parametros:
        - ruta: nodo de Firebase a leer (HTTP GET).

        Hace: lee un valor de Firebase — equivale a firebase.get().
        Devuelve: valor JSON o None si fallo.
        """
        if self.modo_demo:
            print(f"[Firebase-DEMO] GET /{ruta}")
            return None
        try:
            r = _requests.get(self._url(ruta), timeout=8)
            if r.status_code == self.HTTP_OK:
                return r.json()
            self._manejar_respuesta(r, f"GET /{ruta}")
            return None
        except Exception as exc:
            print(f"[Firebase] Conexion fallida en GET /{ruta}: {exc}")
            return None

    def resumen(self) -> None:
        """Imprime cuantos eventos de cada tipo se guardaron."""
        print("\n[Firebase] === Resumen de eventos guardados ===")
        for tipo, n in self._conteo.items():
            print(f"  {tipo:<15}: {n} eventos")


# ──────────────────────────────────────────────
# Logica de guardado por tipo de evento
# ──────────────────────────────────────────────

def _guardar_telemetria(payload: Dict[str, Any], fb: FirebaseREST) -> None:
    """
    Hace: guarda telemetria del chaleco en vestaguard/sensores.
          Estructura igual a la del ejemplo de la maestra: sensores/{campo}.
          NO guarda imagenes ni datos de rostros (privacidad garantizada).
    """
    # Excluir cualquier campo con imagen
    excluir = {"imagen_b64", "frame", "foto", "imagen", "rostro", "cara"}
    datos   = {k: v for k, v in payload.items() if k not in excluir}

    # PUT al nodo sensores (sobreescribe con ultima lectura)
    fb.put("vestaguard/sensores", {
        "distancia_cm":    datos.get("distancia_cm"),
        "movimiento_pir":  datos.get("movimiento_pir") or datos.get("pir"),
        "aceleracion_y":   datos.get("aceleracion_y"),
        "caida_detectada": datos.get("caida_detectada"),
        "boton_panico":    datos.get("boton_panico"),
        "gps_latitud":     datos.get("gps_latitud"),
        "gps_longitud":    datos.get("gps_longitud"),
        "gps_fijado":      datos.get("gps_fijado"),
        "bateria_pct":     datos.get("bateria_pct"),
        "timestamp":       timestamp_iso(),
        "timestamp_local": timestamp_local(),
    })

    # addto al historial de telemetria (registro con ID automatico)
    fb.addto("vestaguard/historial_sensores", {
        "tipo":           "telemetria",
        "distancia_cm":   datos.get("distancia_cm"),
        "movimiento_pir": datos.get("movimiento_pir") or datos.get("pir"),
        "caida":          datos.get("caida_detectada"),
        "panico":         datos.get("boton_panico"),
    })


def _guardar_alerta_ia(payload: Dict[str, Any], fb: FirebaseREST) -> None:
    """
    Hace: guarda decision del modelo IA en vestaguard/alertas_ia.
          Solo datos procesados: clasificacion, confianza, accion.
          SIN imagenes ni datos de vision cruda.
    """
    # Equivale a firebase.addto("alertas_ia", lectura) del ejemplo de la maestra
    fb.addto("vestaguard/alertas_ia", {
        "tipo":          "alerta_ia",
        "clasificacion": payload.get("clasificacion", "desconocido"),
        "confianza":     round(float(payload.get("confianza", 0.0)), 3),
        "accion":        payload.get("accion", ""),
        "fuente":        payload.get("fuente", ""),
    })


def _guardar_actuador(topico: str, payload: Any, fb: FirebaseREST) -> None:
    """
    Hace: guarda estado de un actuador en vestaguard/actuadores.
          Usa PATCH para actualizar solo el campo del actuador afectado
          (equivale a firebase.patch("actuadores", {actuador: estado})).
    """
    partes   = topico.split("/")
    actuador = partes[-1] if len(partes) > 2 else "desconocido"
    estado   = str(payload).upper() if not isinstance(payload, dict) else json.dumps(payload)

    # PATCH — actualizacion parcial del nodo actuadores
    fb.patch("vestaguard/actuadores", {
        actuador:          estado,
        "ultimo_cambio":   timestamp_iso(),
        "ultimo_actuador": actuador,
    })

    # addto — registro historico del cambio de estado
    fb.addto("vestaguard/historial_actuadores", {
        "tipo":     "estado_actuador",
        "actuador": actuador,
        "estado":   estado,
    })


def _actualizar_estado_camara(payload: Dict[str, Any], fb: FirebaseREST) -> None:
    """Hace: actualiza el estado de la ESP32-CAM sin guardar imagen."""
    fb.patch("vestaguard/sistema/camara", {
        "evento":    payload.get("evento", "desconocido"),
        "bytes":     payload.get("tamano_bytes", 0),
        "timestamp": timestamp_iso(),
    })


# ──────────────────────────────────────────────
# Cliente MQTT
# ──────────────────────────────────────────────

def crear_cliente_mqtt(fb: FirebaseREST, host: str, puerto: int):
    """
    Parametros:
    - fb: instancia de FirebaseREST.
    - host: IP del broker MQTT.
    - puerto: puerto del broker.

    Hace: crea el cliente paho-mqtt y lo suscribe a los temas VestaGuard.
    Devuelve: cliente MQTT o None si paho no esta disponible.
    """
    if not _MQTT_OK:
        print("[MQTT] AVISO: paho-mqtt no esta instalado.")
        print("       Ejecuta: pip install paho-mqtt")
        return None

    cliente = mqtt.Client(client_id="vestaguard_firebase_logger")

    def al_conectar(c, _ud, _flags, rc):
        if rc == 0:
            print(f"[MQTT] Conectado al broker {host}:{puerto}")
            # Suscripciones
            c.subscribe(TEMA_TELEMETRIA)
            c.subscribe(TEMA_GPS)
            c.subscribe(TEMA_ALERTA_IA)
            c.subscribe(TEMA_COMANDO_IA)
            c.subscribe(TEMA_CONTROL)
            c.subscribe(TEMA_CAM_ESTADO)
            c.subscribe(TEMA_DESDE_DASH)
            # Marcar sistema como online
            fb.put("vestaguard/sistema/estado", {
                "online":    True,
                "timestamp": timestamp_iso(),
            })
            print("[MQTT] Suscrito a todos los temas. Firebase logger activo.")
        else:
            print(f"[MQTT] Error de conexion, codigo: {rc}")

    def al_desconectar(_c, _ud, _rc):
        fb.put("vestaguard/sistema/estado", {
            "online":    False,
            "timestamp": timestamp_iso(),
        })
        print("[MQTT] Desconectado del broker.")

    def al_recibir(_c, _ud, mensaje):
        topico = mensaje.topic
        try:
            texto = mensaje.payload.decode("utf-8", errors="ignore")
            try:
                payload = json.loads(texto)
            except Exception:
                payload = {"texto": texto}
        except Exception:
            payload = {}

        print(f"[MQTT → Firebase] {topico}")

        # ── Telemetria del chaleco ──────────────────────
        if topico in (TEMA_TELEMETRIA, TEMA_GPS) and isinstance(payload, dict):
            _guardar_telemetria(payload, fb)

        # ── Decision de IA (sin imagen) ─────────────────
        elif topico == TEMA_ALERTA_IA and isinstance(payload, dict):
            _guardar_alerta_ia(payload, fb)

        # ── Estado de actuadores (motores, rgb, relevador)
        elif topico.startswith("vestaguard/control/"):
            _guardar_actuador(topico, payload, fb)

        # ── Estado ESP32-CAM (sin imagen) ───────────────
        elif topico == TEMA_CAM_ESTADO and isinstance(payload, dict):
            _actualizar_estado_camara(payload, fb)

        # ── Control desde dashboard → re-publica al ESP32
        elif topico.startswith("vestaguard/firebase/control/"):
            actuador = topico.split("/")[-1]
            _c.publish(f"vestaguard/control/{actuador}", texto)
            _guardar_actuador(f"vestaguard/control/{actuador}", texto, fb)

    cliente.on_connect    = al_conectar
    cliente.on_disconnect = al_desconectar
    cliente.on_message    = al_recibir

    try:
        cliente.connect(host, puerto, keepalive=60)
    except Exception as exc:
        print(f"[MQTT] No se pudo conectar: {exc}")
        print("       Verifica que Mosquitto este corriendo.")
        return None

    return cliente


# ──────────────────────────────────────────────
# Modo demo — datos simulados sin hardware
# ──────────────────────────────────────────────

def _ejecutar_modo_demo(fb: FirebaseREST) -> None:
    """Simula el flujo completo de VestaGuard cada 5 segundos."""
    import random
    clasificaciones = ["normal", "vigilancia", "amenaza", "emergencia"]
    actuadores_demo = ["motores", "rgb", "relevador"]

    print("\n[DEMO] Generando eventos simulados VestaGuard cada 5 segundos.")
    print("       Los datos se guardan en Firebase (o se muestran en consola si no hay URL).")
    print("       Presiona Ctrl+C para detener.\n")

    ciclo = 0
    try:
        while True:
            ciclo += 1

            # 1. Telemetria
            _guardar_telemetria({
                "distancia_cm":    round(random.uniform(30, 300), 1),
                "movimiento_pir":  random.choice([True, False]),
                "aceleracion_y":   round(random.uniform(-2.5, 2.5), 3),
                "caida_detectada": ciclo % 7 == 0,
                "boton_panico":    ciclo % 11 == 0,
                "gps_latitud":     21.123456 + random.uniform(-0.001, 0.001),
                "gps_longitud":   -101.678901 + random.uniform(-0.001, 0.001),
                "gps_fijado":      True,
                "bateria_pct":     max(10, 100 - ciclo * 2),
            }, fb)

            # 2. Alerta IA (cada 2 ciclos)
            if ciclo % 2 == 0:
                nivel = random.choice(clasificaciones)
                _guardar_alerta_ia({
                    "clasificacion": nivel,
                    "confianza":     round(random.uniform(0.6, 0.99), 3),
                    "accion":        "ALERTA_TOTAL" if nivel == "emergencia"
                                     else "VIBRACION_FUERTE" if nivel == "amenaza"
                                     else "MANTENER",
                    "fuente":        "heuristica_visual",
                }, fb)

            # 3. Estado actuador (cada 3 ciclos)
            if ciclo % 3 == 0:
                actuador = random.choice(actuadores_demo)
                estado   = random.choice(["ON", "OFF"])
                _guardar_actuador(
                    f"vestaguard/control/{actuador}",
                    estado,
                    fb,
                )

            time.sleep(5)

    except KeyboardInterrupt:
        print("\n[DEMO] Detenido por usuario.")


# ──────────────────────────────────────────────
# Punto de entrada
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="VestaGuard — Firebase Logger (REST API)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Modo demo: genera datos simulados sin hardware ni Firebase real.",
    )
    parser.add_argument(
        "--mqtt-host",
        default=MQTT_HOST,
        help=f"IP del broker MQTT (default: {MQTT_HOST})",
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=MQTT_PORT,
        help=f"Puerto del broker (default: {MQTT_PORT})",
    )
    parser.add_argument(
        "--db-url",
        default=FIREBASE_URL,
        help="URL de Firebase Realtime Database",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("   VestaGuard — Firebase Logger")
    print("   Integrantes: Estefania, Aldo, Pablo")
    print("   E4: Firebase + Interfaz Grafica  |  21 mayo 2026")
    print("=" * 60)

    fb = FirebaseREST(url_base=args.db_url, modo_demo=args.demo)

    if args.demo:
        _ejecutar_modo_demo(fb)
        fb.resumen()
        return

    cliente = crear_cliente_mqtt(fb, args.mqtt_host, args.mqtt_port)

    if cliente is None:
        print("\n[AVISO] No se pudo iniciar MQTT.")
        print("        Prueba modo demo: python firebase_logger.py --demo\n")
        sys.exit(1)

    print(f"[Sistema] Firebase logger activo.")
    print(f"          Broker: {args.mqtt_host}:{args.mqtt_port}")
    print("          Presiona Ctrl+C para detener.\n")

    try:
        cliente.loop_forever()
    except KeyboardInterrupt:
        print("\n[Sistema] Detenido por usuario.")
    finally:
        try:
            fb.put("vestaguard/sistema/estado", {
                "online": False, "timestamp": timestamp_iso()
            })
            cliente.disconnect()
        except Exception:
            pass
        fb.resumen()


if __name__ == "__main__":
    main()
