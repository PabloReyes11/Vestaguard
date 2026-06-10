# VestaGuard - Guía de Despliegue de Hardware y Nube

El presente documento detalla el procedimiento de inicialización y despliegue operativo del sistema VestaGuard.

### 1. Inicialización del Chaleco (ESP32 Principal)
- Es necesario suministrar energía a la tarjeta de control conectando el PowerBank del chaleco.
- El microcontrolador ESP32 activará el LED indicador en color azul fijo durante la búsqueda y asociación a la red WiFi configurada.
- Tras establecer la conexión inalámbrica y conectarse exitosamente al broker MQTT, el LED azul entrará en modo intermitente, confirmando la activación del modo VIGILANCIA.

### 2. Inicialización del Módulo de Visión (ESP32-CAM)
- Se debe energizar el módulo ESP32-CAM.
- El dispositivo se asociará a la red WiFi y encenderá levemente el flash integrado, confirmando así la conexión al servicio MQTT.
- La cámara permanecerá en estado inactivo (idle) hasta recibir comandos de captura asíncronos emitidos por el chaleco principal.

### 3. Ejecución del Entorno Local (Estación Base / Servidor)
Para habilitar el procesamiento de Inteligencia Artificial y la persistencia de datos en la nube, es imperativo iniciar los servicios en la estación base en el siguiente orden:

1. **Broker MQTT**: Iniciar el servicio de mensajería empleando la configuración local.
   \\ash
   mosquitto -c Servidor/mosquitto_local.conf -v
   \2. **Puente Firebase**: Iniciar el módulo de sincronización de datos telemétricos hacia Google Cloud.
   \\ash
   python Servidor/firebase_vestaguard.py
   \3. **Servidor de IA**: Iniciar el motor de inferencia de visión computacional.
   \\ash
   python Servidor/servidor_ia.py
   \
### 4. Acceso Remoto (Familiar / Supervisor)
El panel de control (Dashboard) está publicado de manera estática y accesible globalmente a través de GitHub Pages.
El monitoreo del sistema en tiempo real se lleva a cabo mediante el siguiente enlace:

**[https://pabloreyes11.github.io/Vestaguard/](https://pabloreyes11.github.io/Vestaguard/)**
