# PROYECTO: VestaGuard - Guardian de Espalda con Inteligencia Artificial
# DESCRIPCION: Parametros de red para el ESP32 principal del chaleco.
#              EDITAR este archivo con los datos reales antes de subirlo al ESP32.

# ── WiFi ─────────────────────────────────────────────────────────────────
# Red WiFi donde tambien esta conectada la laptop con Mosquitto
SSID_WIFI      = "PR11"       # <-- cambiar esto
CONTRASENA_WIFI = "Pavo1234"      # <-- cambiar esto

# Aliases (el main.py usa ambas formas)
SSID      = SSID_WIFI
CONTRASENA = CONTRASENA_WIFI

# ── MQTT ──────────────────────────────────────────────────────────────────
# IP de la laptop donde corre Mosquitto
# Para obtenerla: abrir cmd en la laptop -> escribir "ipconfig"
# Direccion IPv4 oficial asignada al servidor de VestaGuard
HOST_MQTT       = "10.254.179.79"          # IP oficial de despliegue
PUERTO_MQTT     = 1883
USUARIO_MQTT    = ""                     # dejar vacio si no hay autenticacion
CLAVE_MQTT      = ""                     # dejar vacio si no hay autenticacion
ID_CLIENTE_MQTT = "vestaguard_esp32"

# ── Firebase ──────────────────────────────────────────────────────────────
# URL del Realtime Database (ver Firebase Console -> Realtime Database)
URL_FIREBASE_DB      = "https://chaleco-vestaguard-default-rtdb.firebaseio.com"
URL_FIREBASE_STORAGE = ""
TOKEN_FIREBASE       = ""               # dejar vacio si las reglas son abiertas

# ── Opciones ──────────────────────────────────────────────────────────────
HABILITAR_MODO_SILENCIOSO = False
