# VestaGuard — Firebase + Dashboard (E4)
# Guía de configuración paso a paso
# Basada en: Sist Progr Unidad4 Firebase.txt (recursos de la maestra)
# Integrantes: Estefania Alvarez (23240077), Aldo Rangel (23240272), Pablo Reyes (23240055)

## ¿Qué contiene esta carpeta?

| Archivo | Descripción |
|---|---|
| `firebase_vestaguard.py` | Script Python — puente MQTT → Firebase (ejecutar en PC/laptop) |
| `dashboard.html` | Dashboard web — abrir en el navegador (sin npm) |
| `requirements_firebase.txt` | Dependencias Python para esta carpeta |
| `ufirebase.py` | Librería MicroPython de la maestra — copiar al ESP32 |

---

## Paso 1 — Crear el proyecto en Firebase

Sigue exactamente los pasos del slide de la maestra:

1. Ve a **https://firebase.google.com** e inicia sesión con cuenta Google
2. Clic en **Agregar proyecto** → nombre: `VestaGuard`
3. Deshabilita Google Analytics → **Crear proyecto**
4. En el menú lateral: **Compilación → Autenticación → Comenzar**
5. Método: **Anónimo → Habilitar → Guardar**
6. **Compilación → Realtime Database → Crear base de datos**
7. Ubicación: **Estados Unidos (us-central1)**
8. Reglas: **Iniciar en modo de prueba** (30 días de acceso abierto)
9. **URL de nuestra DB oficial (ya configurada)** (la necesitarás):
   ```
   https://chaleco-vestaguard-default-rtdb.firebaseio.com
   ```
10. En **Reglas**, verifica que quede:
    ```json
    { "rules": { ".read": true, ".write": true } }
    ```

---

## Paso 2 — Obtener el API Key para el dashboard

El slide de la maestra dice: *Configuración del proyecto → General → Clave de API web*

1. En Firebase Console → ícono ️ → **Configuración del proyecto**
2. Pestaña **General**
3. El valor oficial de **Clave de API web** es (`AIzaSyD3rAg3WZkbuF-MGrpuB3x5i67ayYEQtsg`)

---

## Paso 3 — Estructura JSON en Firebase

La maestra indica que la estructura debe ser `sensores/` y `actuadores/`.
Para VestaGuard usamos el nodo raíz `vestaguard/`:

```
vestaguard/
  sensores/           ← última lectura (PUT/sobreescritura)
    distancia_cm
    movimiento_pir
    aceleracion_y
    caida_detectada
    boton_panico
    gps_latitud
    gps_longitud
    timestamp
  alertas_ia/         ← historial con ID automático (POST/addto)
    -Nabc123/
      clasificacion
      confianza
      accion
      timestamp
  actuadores/         ← estado actual (PATCH)
    motores           ← "ON" / "OFF"
    rgb               ← "ROJO" / "VERDE" / "AZUL" / "APAGAR"
    relevador         ← "ON" / "OFF"
  historial_sensores/ ← registros con ID automático
  historial_actuadores/
  sistema/
    estado/           ← online: true/false
    camara/           ← estado ESP32-CAM
```

---

## Paso 4 — Instalar dependencias Python

```bash
pip install -r requirements_firebase.txt
```

Esto instala:
- `requests` → para hacer PUT/POST/PATCH/GET a Firebase REST API (igual que `urequests` en MicroPython)
- `paho-mqtt` → para escuchar los temas MQTT de VestaGuard

---

## Paso 5 — Configurar la URL de Firebase

**Opción A** — Variable de entorno (recomendada):
```bash
# Windows
set FIREBASE_DB_URL=https://chaleco-vestaguard-default-rtdb.firebaseio.com

# Linux/Mac
export FIREBASE_DB_URL=https://chaleco-vestaguard-default-rtdb.firebaseio.com
```

**Opción B** — Editar directamente en `firebase_vestaguard.py`:
```python
FIREBASE_URL = "https://chaleco-vestaguard-default-rtdb.firebaseio.com"
```

---

## Paso 6 — Orden de arranque del sistema VestaGuard

Ejecuta cada componente en una terminal distinta, en este orden:

```
Terminal 1 — Broker MQTT
  mosquitto                            (o mosquitto -v para verbose)

Terminal 2 — Servidor IA
  python servidor_ia.py

Terminal 3 — Firebase Logger (esta carpeta)
  python firebase_vestaguard.py

Terminal 4 — Dashboard (abrir en el navegador)
  Doble clic en dashboard.html
  (o: python -m http.server 8080  →  abrir http://localhost:8080/dashboard.html)

Terminal 5 (opcional) — ESP32 simulado / pruebas MQTT
  python firebase_vestaguard.py --demo
```

---

## Paso 7 — Probar sin hardware (modo demo)

```bash
python firebase_vestaguard.py --demo
```

Genera datos simulados de VestaGuard cada 5 segundos y los guarda en Firebase
(o los imprime en consola si no hay URL configurada).

---

## Paso 8 — Conectar el dashboard a Firebase

1. Abre `dashboard.html` en el navegador
2. Expande el panel **️ Configuración de Firebase**
3. Ingresa:
   - **API Key**: `AIzaSyD3rAg3WZkbuF-MGrpuB3x5i67ayYEQtsg` (del Paso 2)
   - **Auth Domain**: `chaleco-vestaguard.firebaseapp.com`
   - **Database URL**: `https://chaleco-vestaguard-default-rtdb.firebaseio.com`
   - **Project ID**: `vestaguard`
4. Clic en **Conectar a Firebase**
5. El badge cambiará a  **ONLINE** cuando haya datos en tiempo real

---

## Paso 9 — ESP32 con ufirebase.py

El archivo `ufirebase.py` (librería de la maestra) debe copiarse al ESP32 junto
con el resto del firmware del chaleco. Permite que el ESP32 escriba directamente
a Firebase sin pasar por el servidor Python:

```python
import ufirebase as firebase

firebase.setURL("https://chaleco-vestaguard-default-rtdb.firebaseio.com/")

# Escribir telemetria
firebase.put("vestaguard/sensores/distancia_cm", 120)

# Agregar alerta con ID automatico
firebase.addto("vestaguard/alertas_ia", {
    "clasificacion": "amenaza",
    "confianza": 0.84,
    "accion": "VIBRACION_FUERTE"
})

# Leer estado de actuador
firebase.get("vestaguard/actuadores/motores", "estado_motor")
print("Motor:", firebase.estado_motor)  # "ON" o "OFF"
```

---

---

## Referencias

- Firebase Realtime Database: https://firebase.google.com/products/realtime-database
- Tutorial ESP32 + Firebase: https://randomnerdtutorials.com/esp32-firebase-realtime-database/
- Librería ufirebase.py: https://github.com/ckoever/micropython-firebase-realtimedatabase
- Firebase REST API: https://firebase.google.com/docs/reference/rest/database


# Conclusiones Finales del Equipo (Día de Despliegue)

- **Puente Bidireccional:** El script `firebase_vestaguard.py` evolucionó de un simple logger a un puente bidireccional que escucha botones en el Dashboard y los retransmite al broker MQTT local.
- **Deduplicación en Firebase:** Resolvemos el problema de filtrado de eventos idénticos en Firebase añadiendo un timestamp único al payload (ej. CAPTURAR_1739...) y limpiándolo en Python.
- **Interfaz Gráfica Visor:** El Dashboard despliega exitosamente imágenes codificadas en Base64 provenientes de la ESP32-CAM.
