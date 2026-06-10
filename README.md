# VestaGuard - Sistema de Asistencia IoT para Invidentes

VestaGuard es un chaleco inteligente diseñado para asistir a personas con discapacidad visual, integrando hardware biométrico, visión por computadora en el borde (Edge AI) y telemetría en tiempo real hacia la nube.

## Estructura del Proyecto

El repositorio está organizado profesionalmente siguiendo el patrón de diseño de separación de responsabilidades (Separation of Concerns):

- **\HAL/\ (Hardware Abstraction Layer):** Contiene el firmware en MicroPython para los microcontroladores. Aquí reside la lógica de la Máquina de Estados (FSM) del ESP32 NodeMCU, los controladores asíncronos para los sensores/actuadores físicos, y el script de captura JPEG para la ESP32-CAM.
- **\Servidor/\ (Backend e IA):** Contiene el código Python de ejecución local. Aloja el servidor de Inteligencia Artificial (OpenCV DNN Caffe SSD) encargado de procesar las imágenes entrantes, el puente bidireccional de MQTT a Google Firebase (\irebase_vestaguard.py\), y la configuración del broker Mosquitto local.
- **\docs/\ (Frontend):** Contiene la lógica de presentación y el cliente web (\index.html\), el cual emplea WebSockets nativos a través del SDK de Firebase para ofrecer un panel de control reactivo en tiempo real.

## Requisitos Previos

- **Mosquitto Broker:** Instalación del servicio [Eclipse Mosquitto](https://mosquitto.org/download/) en el entorno local.
- **Python 3.9+:** Requerido para la ejecución del servidor de IA y el puente de comunicación hacia Firebase.
- **Thonny IDE o esptool:** Herramientas necesarias para realizar el flasheo del firmware ubicado en la carpeta \HAL/\ hacia los dispositivos ESP32.

## 1. Instalación de Dependencias

Se requiere clonar el repositorio y, posteriormente, instalar las dependencias necesarias para los módulos de Inteligencia Artificial y computación en la nube ejecutando:

\\Bash
pip install -r requirements.txt
pip install -r Servidor/requirements_firebase.txt
pip install -r Servidor/requirements_ia.txt
\
> [!WARNING]
> **Seguridad Firebase:** Es indispensable obtener la llave privada de la base de datos de Firebase correspondiente al proyecto y ubicarla bajo el nombre \serviceAccountKey.json\ dentro de la carpeta \Servidor/\ previo a la ejecución del puente de conexión. Por motivos de seguridad, este archivo se encuentra ignorado en el control de versiones.

## 2. Ejecución del Sistema

Para el correcto despliegue del entorno, se deben seguir los siguientes pasos secuenciales:

1. **Broker MQTT:** Inicializar el broker Mosquitto empleando la configuración local (ubicada en \Servidor/mosquitto_local.conf\), la cual permite conexiones anónimas en el puerto 1883.
   \\ash
   mosquitto -c Servidor/mosquitto_local.conf -v
   \2. **Servidor de Inteligencia Artificial:** Ejecutar el analizador de video para el procesamiento de los cuadros capturados por la ESP32-CAM.
   \\ash
   python Servidor/servidor_ia.py
   \3. **Puente Firebase:** Iniciar el servicio puente encargado de sincronizar la telemetría local de MQTT con la base de datos de Google Cloud.
   \\ash
   python Servidor/firebase_vestaguard.py
   \4. **Hardware (ESP32):** Suministrar energía a la tarjeta principal del chaleco para inicializar la Máquina de Estados y comenzar la transmisión de telemetría.
5. **Dashboard Local (Opcional):** Para pruebas locales, es posible abrir el archivo \docs/index.html\ en un navegador web convencional.

## 3. Acceso Remoto al Dashboard

El panel de control (Dashboard) se encuentra publicado de manera estática a través de la plataforma GitHub Pages, garantizando disponibilidad continua.
El acceso remoto para monitoreo y control se realiza mediante la siguiente dirección web:

**[https://pabloreyes11.github.io/Vestaguard/](https://pabloreyes11.github.io/Vestaguard/)**

El despliegue en la nube elimina la necesidad de alojar el frontend localmente o de emplear túneles HTTP, requiriendo únicamente que el dispositivo servidor (Laptop) mantenga conexión a internet y ejecute el puente de Firebase.
