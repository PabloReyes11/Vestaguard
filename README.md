# VestaGuard - Sistema de Asistencia IoT para Invidentes

VestaGuard es un chaleco inteligente diseñado para asistir a personas con discapacidad visual, integrando hardware biométrico, visión por computadora en el borde (Edge AI) y telemetría en tiempo real hacia la nube.

## Estructura del Proyecto

El repositorio está organizado profesionalmente siguiendo un patrón de separación de intereses (Separation of Concerns):

- **`HAL/` (Hardware Abstraction Layer):** Contiene el firmware en MicroPython para los microcontroladores. Aquí se encuentra la lógica de la Máquina de Estados (FSM) del ESP32 NodeMCU, los controladores asíncronos para los sensores/actuadores físicos, y el script de captura JPEG para la ESP32-CAM.
- **`Servidor/` (Backend e IA):** Contiene el código Python que se ejecuta en la PC local. Aloja el servidor de Inteligencia Artificial (OpenCV DNN Caffe SSD) para procesar las imágenes entrantes, el puente bidireccional de MQTT a Google Firebase (`firebase_vestaguard.py`), y la configuración del broker Mosquitto local.
- **`docs/` (Frontend):** Contiene la lógica del lado del cliente (`index.html`), la cual emplea WebSockets nativos de Firebase JS SDK para ofrecer un panel de control reactivo sin latencia (*zero polling*).

## Requisitos Previos

- **Mosquitto Broker:** Descargar e instalar [Eclipse Mosquitto](https://mosquitto.org/download/) en la máquina local.
- **Python 3.9+:** Necesario para el servidor de IA y el puente a Firebase.
- **Thonny IDE o esptool:** Para flashear el código de la carpeta `HAL/` en los ESP32.

## 1. Instalación de Dependencias

Clona este repositorio y navega a la carpeta principal. Instala todas las dependencias necesarias para los módulos de IA y Nube ejecutando:

```bash
pip install -r requirements.txt
pip install -r Servidor/requirements_firebase.txt
pip install -r Servidor/requirements_ia.txt
```

> [!WARNING]
> **Seguridad Firebase:** Asegúrate de conseguir la llave privada de Firebase de tu proyecto y guardarla como `serviceAccountKey.json` dentro de la carpeta `Servidor/` antes de arrancar el puente. Este archivo ya está ignorado en Git para tu seguridad.

## 2. Ejecución del Sistema

Sigue estos pasos en orden para levantar el entorno completo:

1. **Broker MQTT:** Inicia el broker Mosquitto utilizando la configuración local (ubicada en `Servidor/mosquitto_local.conf` para permitir conexiones anónimas en el puerto 1883).
   ```bash
   mosquitto -c Servidor/mosquitto_local.conf -v
   ```
2. **Servidor de Inteligencia Artificial:** Levanta el analizador de video para procesar las fotos de la ESP32-CAM.
   ```bash
   python Servidor/servidor_ia.py
   ```
3. **Puente Firebase:** Inicia el puente bidireccional que sincronizará MQTT con Google Cloud.
   ```bash
   python Servidor/firebase_vestaguard.py
   ```
4. **Hardware (ESP32):** Conecta las baterías a la PowerBank del chaleco para que la Máquina de Estados comience a publicar telemetría.
5. **Dashboard Local:** Abre el archivo `docs/index.html` en cualquier navegador web.

## 3. Acceso Remoto al Dashboard

El dashboard ahora está publicado estáticamente y disponible 24/7 a través de GitHub Pages.
Cualquier familiar o persona autorizada puede acceder al panel de control desde cualquier parte del mundo ingresando a:

**[https://pabloreyes11.github.io/Vestaguard/](https://pabloreyes11.github.io/Vestaguard/)**

Ya no es necesario descargar el archivo HTML, usar Ngrok ni levantar servidores web locales para la interfaz; basta con que la laptop principal esté corriendo el puente de Firebase y conectada a internet.
