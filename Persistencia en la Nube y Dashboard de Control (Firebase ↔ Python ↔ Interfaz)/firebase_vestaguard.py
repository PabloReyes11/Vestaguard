"""
OBJETIVO: Persistencia de eventos VestaGuard en Firebase Realtime Database.
          Actua como puente entre MQTT local y la nube para telemetria,
          alertas de IA y estados de actuadores.
          Incluye modo demo (--demo) para probar sin hardware ni credenciales reales.
SE CARGA EN: Laptop o PC con Python, junto al servidor_ia.py.
RESPONSABLE PRINCIPAL: Rangel Hernandez Aldo.
INTEGRANTES: Alvarez Guevara Estefania Guadalupe (23240077),
             Rangel Hernandez Aldo (23240272),
             Reyes Gutierrez Pablo Alberto (23240055)
PROYECTO: VestaGuard
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Importaciones opcionales — no fallan si faltan
try:
    import firebase_admin
    from firebase_admin import credentials, db as firebase_db
    _FIREBASE_OK = True
except ImportError:
    firebase_admin = None
    _FIREBASE_OK = False

try:
    import paho.mqtt.client as mqtt
    _MQTT_OK = True
except ImportError:
    mqtt = None
    _MQTT_OK = False


# Configuracion de temas MQTT (deben coincidir con el resto del proyecto VestaGuard)
TEMA_TELEMETRIA  = "vestaguard/telemetria/sensores"
TEMA_GPS         = "vestaguard/telemetria/gps"
TEMA_ALERTA_IA   = "vestaguard/ia/resultado"
TEMA_COMANDO_IA  = "vestaguard/ia/comando"
TEMA_CONTROL     = "vestaguard/control/#"      # wildcard: motores, rgb, relevador
TEMA_CAM_ESTADO  = "vestaguard/camara/estado"
TEMA_CAM_FRAME   = "vestaguard/camara/frame"
TEMA_FIREBASE_IN = "vestaguard/firebase/control/#"  # ordenes desde dashboard a chaleco

MQTT_HOST_DEF = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT_DEF = int(os.getenv("MQTT_PORT", "1883"))

# Variable de entorno con la URL de la base de datos Firebase
# EDITAR esta linea con la URL real del proyecto:
FIREBASE_DB_URL = os.getenv(
    "FIREBASE_DB_URL",
    "https://chaleco-vestaguard-default-rtdb.firebaseio.com"
)
FIREBASE_CREDENCIALES = os.getenv(
    "FIREBASE_CREDENTIALS",
    os.path.join(os.path.dirname(__file__), "serviceAccountKey.json"),
)


def _timestamp_iso() -> str:
    """Devuelve timestamp ISO 8601 en UTC."""
    return datetime.now(timezone.utc).isoformat()


def _timestamp_legible() -> str:
    """Devuelve timestamp legible en hora local."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class ClienteFirebase:
    """
    Parametros:
    - modo_demo: si True, solo imprime en consola sin conectar a Firebase.
    - db_url: URL de la base de datos Realtime Database.
    - ruta_credenciales: ruta al archivo serviceAccountKey.json.

    Hace: encapsula la conexion y escritura a Firebase Realtime Database.
    Devuelve: instancia lista para guardar eventos.
    """

    def __init__(
        self,
        modo_demo: bool = False,
        db_url: str = FIREBASE_DB_URL,
        ruta_credenciales: str = FIREBASE_CREDENCIALES,
    ):
        self.modo_demo = modo_demo
        self._db_url = db_url
        self._ruta_credenciales = ruta_credenciales
        self._inicializado = False
        self._conteo: Dict[str, int] = {
            "telemetria": 0,
            "alertas_ia": 0,
            "actuadores": 0,
            "sistema": 0,
        }

        if not modo_demo:
            self._conectar()

    def _conectar(self) -> None:
        """Inicializa firebase-admin con las credenciales del proyecto."""
        if not _FIREBASE_OK:
            print("[Firebase] AVISO: firebase-admin no esta instalado.")
            print("           Ejecuta: pip install firebase-admin")
            print("           El sistema continuara en modo demo.")
            self.modo_demo = True
            return

        if not os.path.exists(self._ruta_credenciales):
            print(f"[Firebase] AVISO: No se encontro el archivo de credenciales.")
            print(f"           ({self._ruta_credenciales})")
            print("           El sistema continuara operando de forma local (simulado).")
            self.modo_demo = True
            return

        try:
            cred = credentials.Certificate(self._ruta_credenciales)
            firebase_admin.initialize_app(cred, {"databaseURL": self._db_url})
            self._inicializado = True
            print(f"[Firebase] Conectado a {self._db_url}")
        except Exception as exc:
            print(f"[Firebase] Error al conectar: {exc}")
            print("           El sistema continuara en modo demo.")
            self.modo_demo = True

    def guardar(self, ruta: str, datos: Dict[str, Any]) -> bool:
        """
        Agrega datos con timestamp al nodo especificado (push).
        - ruta: nodo de Firebase (ejemplo: 'telemetria').
        - datos: diccionario a almacenar como nuevo hijo.
        Devuelve: True si tuvo exito, False en caso contrario.
        """
        datos["timestamp"] = _timestamp_iso()
        datos["timestamp_local"] = _timestamp_legible()

        categoria = ruta.split("/")[0]
        self._conteo[categoria] = self._conteo.get(categoria, 0) + 1

        if self.modo_demo:
            print(f"[Firebase] [{_timestamp_legible()}] /{ruta} -> {json.dumps(datos, ensure_ascii=False)}")
            return True

        if not self._inicializado:
            return False

        try:
            firebase_db.reference(ruta).push(datos)
            print(f"[Firebase] /{ruta} guardado.")
            return True
        except Exception as exc:
            print(f"[Firebase] Error al guardar en /{ruta}: {exc}")
            return False

    def escribir(self, ruta: str, valor: Any) -> bool:
        """
        Sobreescribe el nodo con el valor dado (set, no push).
        Usado para estado online/offline y ultimo estado de actuadores.
        """
        if self.modo_demo:
            print(f"[Firebase] SET /{ruta} = {valor}")
            return True

        if not self._inicializado:
            return False

        try:
            firebase_db.reference(ruta).set(valor)
            return True
        except Exception as exc:
            print(f"[Firebase] Error al escribir en /{ruta}: {exc}")
            return False

    def resumen_conteo(self) -> None:
        """Imprime cuantos eventos de cada tipo se guardaron."""
        print("\n[Firebase] === Resumen de eventos guardados ===")
        for tipo, n in self._conteo.items():
            print(f"  {tipo:<15}: {n} eventos")


def _procesar_telemetria(payload: Dict[str, Any], firebase: ClienteFirebase) -> None:
    """Guarda un evento de telemetria en Firebase (sin imagenes ni rostros)."""
    campos_excluidos = {"imagen_b64", "frame", "foto", "imagen", "rostro", "cara"}
    datos_limpios = {k: v for k, v in payload.items() if k not in campos_excluidos}

    datos = {
        "tipo": "telemetria",
        "distancia_cm":   datos_limpios.get("distancia_cm") or datos_limpios.get("proximidad_cm"),
        "movimiento_pir": datos_limpios.get("movimiento_pir") or datos_limpios.get("pir"),
        "aceleracion_y":  datos_limpios.get("aceleracion_y"),
        "caida_detectada": datos_limpios.get("caida_detectada"),
        "boton_panico":   datos_limpios.get("boton_panico"),
        "gps_latitud":    datos_limpios.get("gps_latitud"),
        "gps_longitud":   datos_limpios.get("gps_longitud"),
        "gps_fijado":     datos_limpios.get("gps_fijado"),
        "bateria_pct":    datos_limpios.get("bateria_pct"),
        "crudo":          datos_limpios,
    }
    firebase.guardar("vestaguard/historial_telemetria", datos)
    firebase.escribir("vestaguard/sensores", datos)


def _procesar_alerta_ia(payload: Dict[str, Any], firebase: ClienteFirebase) -> None:
    """Guarda un evento de alerta IA en Firebase. NUNCA guarda imagen."""
    firebase.guardar("vestaguard/alertas_ia", {
        "tipo":           "alerta_ia",
        "clasificacion":  payload.get("clasificacion", "desconocido"),
        "confianza":      payload.get("confianza", 0.0),
        "accion":         payload.get("accion", ""),
        "fuente":         payload.get("fuente", ""),
    })


def _procesar_estado_actuador(
    topico: str, payload: Any, firebase: ClienteFirebase
) -> None:
    """Guarda el estado de un actuador en Firebase."""
    partes = topico.split("/")
    actuador = partes[-1] if len(partes) > 2 else "desconocido"
    estado_str = (
        str(payload).upper() if not isinstance(payload, dict)
        else json.dumps(payload)
    )

    firebase.guardar("vestaguard/historial_actuadores", {
        "tipo":          "estado_actuador",
        "actuador":      actuador,
        "estado":        estado_str,
        "topico_origen": topico,
    })
    firebase.escribir(f"vestaguard/actuadores/{actuador}", estado_str)


def _procesar_estado_camara(
    payload: Dict[str, Any], firebase: ClienteFirebase
) -> None:
    """Guarda el estado de la ESP32-CAM sin imagen."""
    firebase.escribir("vestaguard/sistema/camara", {
        "evento":       payload.get("evento", "desconocido"),
        "tamano_bytes": payload.get("tamano_bytes", 0),
        "timestamp":    _timestamp_iso(),
    })


def crear_cliente_mqtt(firebase: ClienteFirebase, host: str, puerto: int):
    """
    Crea y configura el cliente paho-mqtt para escuchar temas VestaGuard.
    Devuelve: instancia del cliente MQTT o None si paho no esta disponible.
    """
    if not _MQTT_OK:
        print("[MQTT] AVISO: paho-mqtt no esta instalado.")
        print("       Ejecuta: pip install paho-mqtt")
        return None

    try:
        cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="vestaguard_firebase_bridge")
    except AttributeError:
        cliente = mqtt.Client(client_id="vestaguard_firebase_bridge")

    def on_connect(c, _userdata, _flags, rc):
        if rc == 0:
            print(f"[MQTT] Conectado al broker {host}:{puerto}")
            for tema in (
                TEMA_TELEMETRIA, TEMA_GPS, TEMA_ALERTA_IA,
                TEMA_COMANDO_IA, TEMA_CONTROL, TEMA_CAM_ESTADO, TEMA_CAM_FRAME, TEMA_FIREBASE_IN
            ):
                c.subscribe(tema)
            firebase.escribir("vestaguard/sistema/estado", {
                "online": True,
                "timestamp": _timestamp_iso(),
            })
            print("[MQTT] Suscrito a todos los temas VestaGuard.")
        else:
            print(f"[MQTT] Error de conexion, codigo: {rc}")

    def on_disconnect(_c, _userdata, _rc):
        firebase.escribir("vestaguard/sistema/estado", {
            "online": False,
            "timestamp": _timestamp_iso(),
        })
        print("[MQTT] Desconectado del broker.")

    def on_message(_c, _userdata, mensaje):
        topico = mensaje.topic
        try:
            payload_raw = mensaje.payload.decode("utf-8", errors="ignore")
            try:
                payload = json.loads(payload_raw)
            except Exception:
                payload = {"texto": payload_raw}
        except Exception:
            payload = {}

        print(f"[MQTT] Recibido en [{topico}]")

        if topico in (TEMA_TELEMETRIA, TEMA_GPS) and isinstance(payload, dict):
            _procesar_telemetria(payload, firebase)

        elif topico == TEMA_ALERTA_IA and isinstance(payload, dict):
            _procesar_alerta_ia(payload, firebase)

        elif topico.startswith("vestaguard/control/"):
            _procesar_estado_actuador(topico, payload, firebase)

        elif topico == TEMA_CAM_FRAME and isinstance(payload, dict):
            # Guardar la foto de la camara en Firebase para que el dashboard la vea
            if 'imagen_b64' in payload and payload['imagen_b64']:
                import time
                try:
                    b64_clean = payload['imagen_b64'].replace('\n', '').replace('\r', '')
                    firebase.escribir("vestaguard/sistema/ultima_foto", {
                        "imagen_b64": b64_clean,
                        "timestamp": int(time.time() * 1000)
                    })
                    print(f"[FIREBASE] Foto actualizada en vestaguard/sistema/ultima_foto ({len(b64_clean)} chars)")
                except Exception as e:
                    print(f"[FIREBASE] Error subiendo foto: {e}")
                    
        elif topico == TEMA_CAM_ESTADO and isinstance(payload, dict):
            _procesar_estado_camara(payload, firebase)

        elif topico.startswith("vestaguard/firebase/control/"):
            actuador = topico.split("/")[-1]
            # Re-publica como comando MQTT nativo hacia el chaleco
            _c.publish(f"vestaguard/control/{actuador}", payload_raw)
            firebase.guardar("actuadores", {
                "tipo":     "orden_remota_dashboard",
                "actuador": actuador,
                "estado":   payload_raw,
            })

    cliente.on_connect = on_connect
    cliente.on_disconnect = on_disconnect
    cliente.on_message = on_message

    try:
        cliente.connect(host, puerto, keepalive=60)
    except Exception as exc:
        print(f"[MQTT] No se pudo conectar al broker: {exc}")
        print("       Verifica que Mosquitto este corriendo.")
        return None

    return cliente


def _ejecutar_modo_demo(firebase: ClienteFirebase) -> None:
    """Genera eventos simulados cada 5 segundos para demostrar el flujo."""
    import random

    clasificaciones = ["normal", "vigilancia", "amenaza", "emergencia"]
    acciones_actuador = ["ON", "OFF"]
    actuadores = ["motores", "rgb", "relevador"]

    print("\n[DEMO] Generando eventos simulados VestaGuard cada 5 segundos.")
    print("       Presiona Ctrl+C para detener.\n")

    ciclo = 0
    try:
        while True:
            ciclo += 1

            firebase.guardar("telemetria", {
                "tipo":           "telemetria",
                "distancia_cm":   round(random.uniform(30, 300), 1),
                "movimiento_pir": random.choice([True, False]),
                "aceleracion_y":  round(random.uniform(-2, 2), 3),
                "caida_detectada": ciclo % 7 == 0,
                "boton_panico":   ciclo % 11 == 0,
                "gps_latitud":    21.123456 + random.uniform(-0.001, 0.001),
                "gps_longitud":   -101.678901 + random.uniform(-0.001, 0.001),
                "gps_fijado":     True,
                "bateria_pct":    max(10, 100 - ciclo * 3),
            })

            if ciclo % 2 == 0:
                nivel = random.choice(clasificaciones)
                firebase.guardar("alertas_ia", {
                    "tipo":          "alerta_ia",
                    "clasificacion": nivel,
                    "confianza":     round(random.uniform(0.6, 0.99), 3),
                    "accion":        (
                        "ALERTA_TOTAL" if nivel == "emergencia"
                        else "VIBRACION_FUERTE" if nivel == "amenaza"
                        else "MANTENER"
                    ),
                    "fuente": "heuristica_visual",
                })

            if ciclo % 3 == 0:
                actuador = random.choice(actuadores)
                estado = random.choice(acciones_actuador)
                firebase.guardar("actuadores", {
                    "tipo":          "estado_actuador",
                    "actuador":      actuador,
                    "estado":        estado,
                    "topico_origen": f"vestaguard/control/{actuador}",
                })

            time.sleep(5)

    except KeyboardInterrupt:
        print("\n[DEMO] Detenido por usuario.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="VestaGuard — Puente MQTT a Firebase Realtime Database"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Ejecuta en modo demo: genera datos simulados sin MQTT ni Firebase real.",
    )
    parser.add_argument(
        "--mqtt-host",
        default=MQTT_HOST_DEF,
        help=f"IP del broker MQTT (default: {MQTT_HOST_DEF})",
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=MQTT_PORT_DEF,
        help=f"Puerto del broker MQTT (default: {MQTT_PORT_DEF})",
    )
    parser.add_argument(
        "--db-url",
        default=FIREBASE_DB_URL,
        help="URL de Firebase Realtime Database",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("   VestaGuard — Puente Firebase")
    print("   Integrantes: Estefania, Aldo, Pablo")
    print("=" * 60)

    firebase = ClienteFirebase(
        modo_demo=args.demo,
        db_url=args.db_url,
        ruta_credenciales=FIREBASE_CREDENCIALES,
    )

    if args.demo:
        _ejecutar_modo_demo(firebase)
        firebase.resumen_conteo()
        return

    cliente = crear_cliente_mqtt(firebase, args.mqtt_host, args.mqtt_port)

    if cliente is None:
        print("\n[AVISO] No se pudo iniciar el cliente MQTT.")
        print("        Ejecuta con --demo para probar sin hardware:")
        print("        python firebase_vestaguard.py --demo\n")
        sys.exit(1)

    print(f"[Sistema] Puente activo. Broker: {args.mqtt_host}:{args.mqtt_port}")
    print("          Presiona Ctrl+C para detener.\n")

    if not args.demo and firebase._inicializado:
        def listener_firebase(event):
            try:
                if isinstance(event.data, dict):
                    for actuador, estado in event.data.items():
                        if actuador == 'ultimo_cambio': continue
                        topico = f"vestaguard/control/{actuador}"
                        valor = str(estado)
                        if actuador == 'camara_disparo' and valor.startswith('CAPTURAR'): valor = 'CAPTURAR'
                        print(f"[Firebase->MQTT] Reenviando orden del Dashboard: {topico} = {valor}")
                        cliente.publish(topico, valor)
                else:
                    path = event.path.strip('/')
                    if path and path != 'ultimo_cambio':
                        topico = f"vestaguard/control/{path}"
                        valor = str(event.data)
                        if path == 'camara_disparo' and valor.startswith('CAPTURAR'): valor = 'CAPTURAR'
                        print(f"[Firebase->MQTT] Reenviando orden del Dashboard: {topico} = {valor}")
                        cliente.publish(topico, valor)
            except Exception as e:
                print(f"[ERROR Firebase Listener] {e}")
        try:
            firebase_db.reference("vestaguard/actuadores").listen(listener_firebase)
            print("[Firebase] Escuchando botones del Dashboard en tiempo real...")
        except Exception as e:
            print(f"[ERROR Firebase Escucha] {e}")

    try:
        cliente.loop_forever()
    except KeyboardInterrupt:
        print("\n[Sistema] Detenido por usuario.")
    finally:
        try:
            firebase.escribir("vestaguard/sistema/estado", {
                "online": False,
                "timestamp": _timestamp_iso(),
            })
            cliente.disconnect()
        except Exception:
            pass
        firebase.resumen_conteo()


if __name__ == "__main__":
    main()
