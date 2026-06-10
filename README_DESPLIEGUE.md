# DESPLIEGUE â€” VestaGuard
**Esta carpeta contiene los archivos listos para cargar en cada dispositivo.**

No modificar los archivos â€” estÃ¡n corregidos y listos.
El Ãºnico archivo que SÃ debes editar antes de cargar es `secrets.py`.

---

##  Estructura

```
DESPLIEGUE/
â”œâ”€â”€ ESP32_CHALECO/          â† Subir ESTOS 4 archivos a la raÃ­z del ESP32 principal
â”‚   â”œâ”€â”€ main.py             â† Firmware completo (FSM + MQTT + HAL)
â”‚   â”œâ”€â”€ dispositivos.py     â† HAL de sensores y actuadores
â”‚   â”œâ”€â”€ secrets.py          â† ï¸ EDITAR antes de subir (WiFi + MQTT + Firebase)
â”‚   â”œâ”€â”€ boot.py             â† InicializaciÃ³n segura
â”‚   â””â”€â”€ lib/                â† ï¸ CARGAR ESTA CARPETA A LA RAÃZ (Subir a /)
â”‚       â””â”€â”€ umqtt/          â† LibrerÃ­a MQTT para MicroPython
â”‚
â”œâ”€â”€ ESP32CAM/               â† Subir ESTOS 2 archivos a la raÃ­z de la ESP32-CAM
â”‚   â”œâ”€â”€ main.py             â† Captura imagen y publica por MQTT
â”‚   â””â”€â”€ secrets.py          â† ï¸ EDITAR antes de subir (mismos datos que el ESP32)
â”‚
â”œâ”€â”€ LAPTOP_SERVIDOR/        â† Scripts que corren en la PC/Laptop con Python
â”‚   â”œâ”€â”€ servidor_ia.py      â† Terminal 1: Servidor de IA (recibe frames, decide)
â”‚   â”œâ”€â”€ firebase_vestaguard.py â† Terminal 2: Puente MQTT â†’ Firebase
â”‚   â”œâ”€â”€ requirements.txt    â† Instalar con: pip install -r requirements.txt
â”‚   â””â”€â”€ modelo/
â”‚       â”œâ”€â”€ deploy.prototxt
â”‚       â”œâ”€â”€ modelo_vestaguard.joblib
â”‚       â””â”€â”€ res10_300x300_ssd_iter_140000.caffemodel
â”‚
â””â”€â”€ LAPTOP_DASHBOARD/       â† Abrir dashboard.html en el navegador
    â”œâ”€â”€ dashboard.html       â† Control y monitoreo en tiempo real
    â”œâ”€â”€ vestaguard.json      â† Estructura de la base de datos Firebase
    â””â”€â”€ ufirebase.py         â† LibrerÃ­a Firebase para MicroPython (copiar al ESP32 si se usa)
```

---

## PASO 1 â€” Editar secrets.py

Antes de subir al ESP32, edita `ESP32_CHALECO/secrets.py`:

```python
SSID_WIFI       = "NOMBRE_DE_TU_WIFI"     # red donde estÃ¡ la laptop
CONTRASENA_WIFI = "CONTRASENA"
HOST_MQTT       = "192.168.X.X"           # IP de la laptop (ver: ipconfig en cmd)
URL_FIREBASE_DB = "https://vestaguard-XXXXXXX-default-rtdb.firebaseio.com/"
```

Copiar el mismo `secrets.py` editado a `ESP32CAM/secrets.py`.

---

## PASO 2 â€” Instalar dependencias en la laptop

```bash
pip install -r LAPTOP_SERVIDOR/requirements.txt
```

---

## PASO 3 â€” Subir archivos al ESP32

Con Thonny:
1. Conectar ESP32 por USB
2. Abrir cada archivo (main, dispositivos, secrets, boot) â†’ Guardar como â†’ "Dispositivo MicroPython" â†’ con el mismo nombre.
3. Para la librerÃ­a MQTT: Hacer clic derecho en la carpeta `lib` (dentro de ESP32_CHALECO) y seleccionar "Subir a /". Thonny crearÃ¡ la estructura `/lib/umqtt/simple.py` automÃ¡ticamente.

Con ampy:
```bash
ampy --port COM3 put ESP32_CHALECO/main.py main.py
ampy --port COM3 put ESP32_CHALECO/dispositivos.py
ampy --port COM3 put ESP32_CHALECO/secrets.py
ampy --port COM3 put ESP32_CHALECO/boot.py
```

Para la ESP32-CAM (usar el COM del adaptador FTDI):
```bash
ampy --port COM4 put ESP32CAM/main.py main.py
ampy --port COM4 put ESP32CAM/secrets.py
```

---

## PASO 4 â€” Orden de encendido

```
1. mosquitto -v                              (Terminal 0 â€” broker)
2. python LAPTOP_SERVIDOR/servidor_ia.py     (Terminal 1 â€” IA)
3. python LAPTOP_SERVIDOR/firebase_vestaguard.py  (Terminal 2 â€” Firebase)
4. Conectar ESP32 chaleco
5. Conectar ESP32-CAM
6. Abrir LAPTOP_DASHBOARD/dashboard.html en el navegador
```

Ver la guÃ­a completa en `GUIA_DESPLIEGUE_FINAL.md` (carpeta raÃ­z del proyecto).

