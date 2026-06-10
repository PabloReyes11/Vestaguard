# Despliegue del Sistema VestaGuard

Este documento contiene la arquitectura de carpetas y los pasos técnicos requeridos para la correcta instalación y despliegue del proyecto VestaGuard.

## Arquitectura de Carpetas

```text
VestaGuard/
│
├── HAL/                    ← Código fuente para los microcontroladores (Capa de Abstracción de Hardware)
│   ├── boot.py             ← Script de inicialización segura
│   ├── dispositivos.py     ← Controladores de actuadores y sensores
│   ├── main.py             ← Máquina de estados (FSM) del chaleco
│   ├── esp32cam_publicador.py ← Script para la ESP32-CAM
│   ├── secrets.py          ← Credenciales de red y MQTT (requiere edición previa)
│   └── lib/                ← Bibliotecas externas (MQTT, GPS, pantallas)
│
├── Servidor/               ← Código backend para la estación base (Python)
│   ├── servidor_ia.py      ← Servidor de IA (análisis de frames)
│   ├── firebase_vestaguard.py ← Puente MQTT hacia Google Firebase
│   ├── requirements_ia.txt ← Dependencias para el entorno de IA
│   ├── requirements_firebase.txt ← Dependencias para el entorno nube
│   ├── mosquitto_local.conf ← Archivo de configuración del broker MQTT
│   └── modelo/             ← Archivos y pesos del modelo Caffe SSD
│
└── docs/                   ← Interfaz de usuario (Frontend SPA)
    └── index.html          ← Dashboard reactivo y lógica del lado del cliente
```

---

## PASO 1 — Configuración de Credenciales

Previo a la carga del firmware, es indispensable editar el archivo `HAL/secrets.py` para configurar las credenciales de la red inalámbrica y las direcciones de los servicios:

```python
SSID_WIFI       = "NOMBRE_DE_TU_WIFI"     # Red local compartida
CONTRASENA_WIFI = "CONTRASENA"
HOST_MQTT       = "192.168.X.X"           # Dirección IP del broker MQTT (estación base)
URL_FIREBASE_DB = "https://vestaguard-XXXXXXX-default-rtdb.firebaseio.com/"
```

Este archivo configurado debe suministrarse a todas las placas ESP32 del proyecto.

---

## PASO 2 — Instalación de Dependencias (Servidor)

Se deben instalar las dependencias requeridas en el entorno de ejecución de la estación base:

```bash
pip install -r Servidor/requirements_ia.txt
pip install -r Servidor/requirements_firebase.txt
```

---

## PASO 3 — Carga de Firmware (ESP32)

Mediante el uso del entorno de desarrollo Thonny:
1. Conectar el ESP32 a la interfaz USB.
2. Transferir los scripts correspondientes (`main.py`, `dispositivos.py`, `secrets.py`, `boot.py`) a la memoria flash del dispositivo.
3. Las bibliotecas contenidas en la carpeta `lib/` deben ser subidas preservando la estructura de directorios en la raíz del microcontrolador.

---

## PASO 4 — Acceso Remoto al Dashboard

El panel de control (Dashboard) se encuentra alojado estáticamente y distribuido globalmente mediante la plataforma GitHub Pages. El monitoreo en tiempo real puede realizarse accediendo a la siguiente URL desde cualquier dispositivo con conectividad web:

**[https://pabloreyes11.github.io/Vestaguard/](https://pabloreyes11.github.io/Vestaguard/)**

El sistema opera de forma autónoma siempre que la estación base mantenga activo el puente de conexión hacia la base de datos en tiempo real.
