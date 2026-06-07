# DESPLIEGUE — VestaGuard
**Esta carpeta contiene los archivos listos para cargar en cada dispositivo.**

No modificar los archivos — están corregidos y listos.
El único archivo que SÍ debes editar antes de cargar es `secrets.py`.

---

## 📁 Estructura

```
DESPLIEGUE/
├── ESP32_CHALECO/          ← Subir ESTOS 4 archivos a la raíz del ESP32 principal
│   ├── main.py             ← Firmware completo (FSM + MQTT + HAL)
│   ├── dispositivos.py     ← HAL de sensores y actuadores
│   ├── secrets.py          ← ⚠️ EDITAR antes de subir (WiFi + MQTT + Firebase)
│   ├── boot.py             ← Inicialización segura
│   └── lib/                ← ⚠️ CARGAR ESTA CARPETA A LA RAÍZ (Subir a /)
│       └── umqtt/          ← Librería MQTT para MicroPython
│
├── ESP32CAM/               ← Subir ESTOS 2 archivos a la raíz de la ESP32-CAM
│   ├── main.py             ← Captura imagen y publica por MQTT
│   └── secrets.py          ← ⚠️ EDITAR antes de subir (mismos datos que el ESP32)
│
├── LAPTOP_SERVIDOR/        ← Scripts que corren en la PC/Laptop con Python
│   ├── servidor_ia.py      ← Terminal 1: Servidor de IA (recibe frames, decide)
│   ├── firebase_vestaguard.py ← Terminal 2: Puente MQTT → Firebase
│   ├── requirements.txt    ← Instalar con: pip install -r requirements.txt
│   └── modelo/
│       ├── deploy.prototxt
│       ├── modelo_vestaguard.joblib
│       └── res10_300x300_ssd_iter_140000.caffemodel
│
└── LAPTOP_DASHBOARD/       ← Abrir dashboard.html en el navegador
    ├── dashboard.html       ← Control y monitoreo en tiempo real
    ├── vestaguard.json      ← Estructura de la base de datos Firebase
    └── ufirebase.py         ← Librería Firebase para MicroPython (copiar al ESP32 si se usa)
```

---

## PASO 1 — Editar secrets.py

Antes de subir al ESP32, edita `ESP32_CHALECO/secrets.py`:

```python
SSID_WIFI       = "NOMBRE_DE_TU_WIFI"     # red donde está la laptop
CONTRASENA_WIFI = "CONTRASENA"
HOST_MQTT       = "192.168.X.X"           # IP de la laptop (ver: ipconfig en cmd)
URL_FIREBASE_DB = "https://vestaguard-XXXXXXX-default-rtdb.firebaseio.com/"
```

Copiar el mismo `secrets.py` editado a `ESP32CAM/secrets.py`.

---

## PASO 2 — Instalar dependencias en la laptop

```bash
pip install -r LAPTOP_SERVIDOR/requirements.txt
```

---

## PASO 3 — Subir archivos al ESP32

Con Thonny:
1. Conectar ESP32 por USB
2. Abrir cada archivo (main, dispositivos, secrets, boot) → Guardar como → "Dispositivo MicroPython" → con el mismo nombre.
3. Para la librería MQTT: Hacer clic derecho en la carpeta `lib` (dentro de ESP32_CHALECO) y seleccionar "Subir a /". Thonny creará la estructura `/lib/umqtt/simple.py` automáticamente.

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

## PASO 4 — Orden de encendido

```
1. mosquitto -v                              (Terminal 0 — broker)
2. python LAPTOP_SERVIDOR/servidor_ia.py     (Terminal 1 — IA)
3. python LAPTOP_SERVIDOR/firebase_vestaguard.py  (Terminal 2 — Firebase)
4. Conectar ESP32 chaleco
5. Conectar ESP32-CAM
6. Abrir LAPTOP_DASHBOARD/dashboard.html en el navegador
```

Ver la guía completa en `GUIA_DESPLIEGUE_FINAL.md` (carpeta raíz del proyecto).
