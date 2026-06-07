"""
OBJETIVO: Servidor de IA basado en OpenCV DNN (Caffe SSD Face Detector).
          Integra la evidencia visual de la ESP32-CAM y telemetria del ESP32 principal
          para emitir decisiones a traves de MQTT.
SE CARGA EN: Laptop o PC con Python.
RESPONSABLE PRINCIPAL: Alvarez Guevara Estefania Guadalupe.
INTEGRANTES: Alvarez Guevara Estefania Guadalupe (23240077), Rangel Hernandez Aldo (23240272), Reyes Gutierrez Pablo Alberto (23240055)
PROYECTO: VestaGuard
"""

from __future__ import annotations

import base64
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:
    import cv2
    import numpy as np
except ImportError:
    print("ERROR: Faltan dependencias. Ejecuta: pip install opencv-python numpy")
    sys.exit(1)

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("ERROR: Falta paho-mqtt. Ejecuta: pip install paho-mqtt")
    sys.exit(1)


TEMA_CAMILLA = "vestaguard/camara/frame"
TEMA_TELEMETRIA = "vestaguard/telemetria/sensores"
TEMA_RESULTADO = "vestaguard/ia/resultado"
TEMA_COMANDO = "vestaguard/ia/comando"

ACCION_NORMAL = "MANTENER"
ACCION_ALERTA = "VIBRACION_FUERTE"
ACCION_CRITICA = "ALERTA_TOTAL"


def _decodificar_payload(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, (bytes, bytearray)):
        texto = payload.decode("utf-8", errors="ignore")
    else:
        texto = str(payload)
    try:
        return json.loads(texto)
    except Exception:
        return {"texto": texto}


def _decodificar_imagen_base64(texto_base64: str):
    try:
        datos = base64.b64decode(texto_base64)
        arreglo = np.frombuffer(datos, dtype=np.uint8)
        return cv2.imdecode(arreglo, cv2.IMREAD_COLOR)
    except Exception:
        return None


@dataclass
class DecisionIA:
    clasificacion: str
    confianza: float
    accion: str
    fuente: str


class MotorDecisionIA:
    def __init__(self):
        # Rutas al modelo Caffe pre-entrenado
        self.ruta_prototxt = os.path.join(os.path.dirname(__file__), "modelo", "deploy.prototxt")
        self.ruta_modelo = os.path.join(os.path.dirname(__file__), "modelo", "res10_300x300_ssd_iter_140000.caffemodel")
        self.net = self._cargar_dnn()
        
        self.ultima_telemetria: Dict[str, Any] = {}
        self.ultima_decision = DecisionIA("normal", 0.0, ACCION_NORMAL, "inicio")

    def _cargar_dnn(self):
        if not os.path.exists(self.ruta_prototxt) or not os.path.exists(self.ruta_modelo):
            print(f"[IA-ERROR] No se encuentran los archivos del modelo Caffe en {os.path.dirname(self.ruta_prototxt)}")
            print("[IA-ERROR] Asegurate de ejecutar el script de descarga.")
            return None
        print("[IA] Cargando modelo Caffe SSD Face Detector...")
        return cv2.dnn.readNetFromCaffe(self.ruta_prototxt, self.ruta_modelo)

    def clasificar_frame(self, frame) -> DecisionIA:
        if frame is None:
            return DecisionIA("error", 0.0, ACCION_NORMAL, "sin_imagen")
            
        if self.net is None:
            return DecisionIA("normal", 0.0, ACCION_NORMAL, "modelo_no_disponible")

        # Preprocesamiento para DNN (SSD Face Detector)
        (h, w) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0))
        
        self.net.setInput(blob)
        detections = self.net.forward()
        
        max_confianza = 0.0
        # Buscar la deteccion con mayor confianza
        for i in range(detections.shape[2]):
            confianza = detections[0, 0, i, 2]
            if confianza > max_confianza:
                max_confianza = float(confianza)
                
        # Filtro de confianza (70%)
        if max_confianza > 0.70:
            return DecisionIA("vigilancia", max_confianza, ACCION_NORMAL, "dnn_caffe_rostro")
            
        return DecisionIA("normal", 0.99, ACCION_NORMAL, "dnn_caffe_sin_rostro")

    def clasificar_imagen_base64(self, imagen_base64: str) -> DecisionIA:
        imagen = _decodificar_imagen_base64(imagen_base64)
        return self.clasificar_frame(imagen)

    def evaluar_telemetria(self, telemetria: Dict[str, Any]) -> DecisionIA:
        self.ultima_telemetria = dict(telemetria)

        caida = bool(telemetria.get("caida_detectada"))
        boton_panico = bool(telemetria.get("boton_panico"))
        distancia_cm = telemetria.get("distancia_cm")
        movimiento = bool(telemetria.get("movimiento_pir"))

        if boton_panico or caida:
            return DecisionIA("emergencia", 1.0, ACCION_CRITICA, "telemetria")

        if distancia_cm is not None and movimiento and float(distancia_cm) <= 120.0:
            return DecisionIA("alerta_sensor", 0.80, ACCION_ALERTA, "telemetria")

        return DecisionIA("normal", 0.99, ACCION_NORMAL, "telemetria")

    def consolidar_decision(self, decision_visual: DecisionIA, decision_telemetria: DecisionIA) -> DecisionIA:
        # 1. Prioridad maxima: emergencias (caida, panico)
        if decision_telemetria.clasificacion == "emergencia":
            return decision_telemetria
            
        # 2. Si la IA detecta un rostro (vigilancia) y los sensores detectan proximidad (alerta_sensor) = AMENAZA CONFIRMADA
        if decision_visual.clasificacion == "vigilancia" and decision_telemetria.clasificacion == "alerta_sensor":
            return DecisionIA("amenaza", decision_visual.confianza, ACCION_ALERTA, "fusion_confirmada")
            
        # 3. Si solo hay rostro sin proximidad critica
        if decision_visual.clasificacion == "vigilancia":
            return decision_visual
            
        # 4. Si solo hay proximidad sin rostro
        if decision_telemetria.clasificacion == "alerta_sensor":
            return DecisionIA("amenaza", decision_telemetria.confianza, ACCION_ALERTA, "sensor_sin_rostro")
            
        return DecisionIA("normal", 0.99, ACCION_NORMAL, "fusion_normal")


def publicar_decision(cliente, decision: DecisionIA, telemetria: Optional[Dict[str, Any]] = None):
    if cliente is None:
        return

    mensaje = {
        "clasificacion": decision.clasificacion,
        "confianza": round(float(decision.confianza), 3),
        "accion": decision.accion,
        "fuente": decision.fuente,
        "telemetria": telemetria or {},
    }
    cliente.publish(TEMA_RESULTADO, json.dumps(mensaje))
    cliente.publish(TEMA_COMANDO, decision.accion)
    print(f"[IA] Decision publicada: {decision.clasificacion.upper()} ({decision.accion})")


def crear_cliente_mqtt(motor: MotorDecisionIA):
    broker = os.getenv("MQTT_HOST", "127.0.0.1")
    puerto = int(os.getenv("MQTT_PORT", "1883"))
    try:
        cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="vestaguard_ia_server")
    except AttributeError:
        # Fallback for paho-mqtt < 2.0
        cliente = mqtt.Client(client_id="vestaguard_ia_server")

    def on_connect(cliente_mqtt, _userdata, _flags, _rc):
        print(f"[MQTT] Conectado a {broker}:{puerto}")
        cliente_mqtt.subscribe(TEMA_CAMILLA)
        cliente_mqtt.subscribe(TEMA_TELEMETRIA)

    def on_message(cliente_mqtt, _userdata, mensaje):
        payload = _decodificar_payload(mensaje.payload)
        
        # Procesar Frame de ESP32-CAM
        if mensaje.topic == TEMA_CAMILLA:
            imagen_b64 = payload.get("imagen_b64") or payload.get("frame") or payload.get("foto")
            if not imagen_b64:
                return
            
            decision_visual = motor.clasificar_imagen_base64(str(imagen_b64))
            decision_final = motor.consolidar_decision(
                decision_visual,
                motor.evaluar_telemetria(motor.ultima_telemetria),
            )
            motor.ultima_decision = decision_final
            publicar_decision(cliente_mqtt, decision_final, motor.ultima_telemetria)
            return

        # Procesar Telemetria del ESP32 Principal
        if mensaje.topic == TEMA_TELEMETRIA:
            decision_telemetria = motor.evaluar_telemetria(payload)
            # Solo actualizamos el estado si detecta un cambio brusco, la fusion principal ocurre con la foto
            if decision_telemetria.clasificacion == "emergencia":
                motor.ultima_decision = decision_telemetria
                publicar_decision(cliente_mqtt, motor.ultima_decision, motor.ultima_telemetria)

    cliente.on_connect = on_connect
    cliente.on_message = on_message
    
    try:
        cliente.connect(broker, puerto, 60)
        return cliente
    except Exception as e:
        print(f"[MQTT-ERROR] No se pudo conectar al broker {broker}: {e}")
        return None


def main():
    print("="*60)
    print(" VestaGuard - Servidor de IA (Caffe SSD Face Detector)")
    print("="*60)
    
    motor = MotorDecisionIA()
    cliente = crear_cliente_mqtt(motor)

    if cliente is None:
        print("[IA] Cerrando servidor.")
        return

    print("[IA] Servidor activo. Esperando imagenes de ESP32-CAM y telemetria...")
    try:
        cliente.loop_forever()
    except KeyboardInterrupt:
        print("\n[IA] Servidor detenido.")


if __name__ == "__main__":
    main()