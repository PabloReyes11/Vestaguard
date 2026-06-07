# VestaGuard: Chaleco Háptico con Inteligencia Artificial

Bienvenido al repositorio oficial del proyecto **VestaGuard**, un sistema embebido tipo wearable (chaleco inteligente) diseñado para asistir en la navegación autónoma de personas con discapacidad visual en entornos urbanos.

Este proyecto fue desarrollado para la materia de **Sistemas Programables** impartida por la Ing. Ma. Verónica Tapia Ibarra en el Instituto Tecnológico de León (TecNM).

---

## 👥 Integrantes del Equipo

| Nombre | Matrícula | Rol |
|---|---|---|
| **Álvarez Guevara Estefanía Guadalupe** | 23240077 | Inteligencia Artificial y ESP32-CAM |
| **Rangel Hernández Aldo** | 23240272 | Firebase y Dashboard |
| **Reyes Gutiérrez Pablo Alberto** | 23240055 | Conexiones Físicas y Hardware |

---

## 🎯 Objetivo General

Diseñar e implementar un sistema embebido basado en **ESP32** y programado en **MicroPython**, que sustituya la percepción visual mediante sensores. VestaGuard recopila información del entorno y la traduce en **estímulos hápticos direccionales en tiempo real** usando motores vibradores.

VestaGuard integra:
- **Sensores:** Ultrasónico (HC-SR04), PIR (HC-SR501), GPS (NEO-6M) y MPU6050.
- **ESP32-CAM (OV3660):** Captura de imágenes enviadas al servidor para detección de rostros mediante Inteligencia Artificial (OpenCV DNN + Caffe SSD).
- **Actuadores:** Motores vibradores ERM (hombros) y LED RGB.
- **Red:** Comunicación asíncrona mediante MQTT (broker Mosquitto local).
- **Cloud:** Integración con Firebase Realtime Database y un Dashboard HTML5 interactivo.

---

## 📂 Estructura del Directorio

El repositorio está dividido lógicamente en tres carpetas principales que reflejan las capas arquitectónicas del proyecto, más recursos de pruebas y guías maestras:

### 1. `Integración Total MQTT (ESP32 ↔ Python)`
Contiene la capa lógica del microcontrolador principal (ESP32 NodeMCU) y la capa de abstracción de hardware (HAL):
- `dispositivos.py`: Clases `SensorBox` y `ActuatorBox` para aislar pines de la lógica.
- `main_vestaguard.py` y `main.py`: Lógica principal de telemetría y FSM (Máquina de Estados).
- `boot.py`: Limpia memoria RAM y se conecta a WiFi antes del arranque.
- `servidor.py`: Interfaz Python por consola para probar telemetría y MQTT.
- `secrets.py`: Credenciales de red e IP oficial de Mosquitto.

### 2. `Integración de Inteligencia Artificial en el Ecosistema IoT (ESP32-CAM ↔ Python IA)`
Contiene el backend de Visión Computacional y la configuración de la cámara:
- `servidor_ia.py`: Servidor que procesa los frames mediante OpenCV DNN y toma la decisión para mandar un comando.
- `esp32cam_publicador.py` y `secrets.py`: Firmware de la ESP32-CAM para capturar evidencia y enviarla en fragmentos.
- `modelo/`: Modelo Caffe preentrenado (`.caffemodel`, `.joblib`, `.prototxt`).

### 3. `Persistencia en la Nube y Dashboard de Control (Firebase ↔ Python ↔ Interfaz)`
Contiene el puente de integración Cloud y la interfaz gráfica:
- `firebase_vestaguard.py`: Script bidireccional Python que empuja eventos MQTT hacia Firebase y envía comandos del Dashboard hacia MQTT.
- `dashboard.html`: Visor en tiempo real (HTML5 + Firebase JS SDK) para mostrar lecturas, alertas y la imagen capturada.
- `README_FIREBASE.md`: Guía de despliegue oficial.

### 4. `PRUEBAS/`
Scripts de Python locales para diagnosticar individualmente subsistemas antes de la integración total (Mosquitto, Firebase, Actuadores).

### Archivos de la Raíz
- `GUIA_DESPLIEGUE_FINAL.md`: Guía exhaustiva de los comandos y flujos para arrancar el ecosistema en un escenario de despliegue oficial.
- `mosquitto_local.conf`: Archivo de configuración que habilita el servidor MQTT y conexiones anónimas desde la ESP32.

---

## 🚀 Despliegue Rápido

Para ver las instrucciones detalladas de ejecución de cada componente, por favor consulte la **`GUIA_DESPLIEGUE_FINAL.md`** ubicada en la raíz de este repositorio. El orden de arranque general es:

1. Levantar **Broker Mosquitto** usando `mosquitto_local.conf`.
2. Levantar servidor local Python **`servidor_ia.py`**.
3. Levantar puente web **`firebase_vestaguard.py`**.
4. Abrir **`dashboard.html`** en el navegador.
5. Encender el chaleco (Batería LiPo / PowerBank).

---
*Repositorio creado como Entrega Final E6 — Instituto Tecnológico de León — Junio 2026*
