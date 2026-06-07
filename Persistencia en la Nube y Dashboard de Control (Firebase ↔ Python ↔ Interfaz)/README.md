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

## 1. Cumplimiento de Rúbrica de Nube y Dashboard

###  Firebase Operativo (Datos en tiempo real)
Se demuestra la conectividad bidireccional continua. El archivo `firebase_vestaguard.py` escucha los tópicos MQTT del chaleco y actualiza en milisegundos la base de datos en `https://chaleco-vestaguard-default-rtdb.firebaseio.com`, usando actualizaciones `PUT` para los sensores en tiempo real.

###  Eventos con Timestamp (Logs fechados)
La base de datos almacena eventos históricos estructurados con la fecha y hora exacta en formato ISO. Se registran 3 tipos de logs distintos:
1. **Historial de Sensores:** Caídas (acelerómetro) e intrusiones (PIR) guardados bajo `/historial_sensores`.
2. **Historial de Actuadores:** Activación de motores y estrobos guardados bajo `/historial_actuadores`.
3. **Log de Alertas IA:** Resultados de inferencia visual de la cámara guardados en `/alertas_ia` (cada evento con su respectivo `timestamp` e ID generado automáticamente).

###  Dashboard Funcional
El archivo `dashboard.html` es una interfaz construida en HTML5/JS puro que se conecta por WebSockets a Firebase. Refleja en tiempo real el estado actual de los sensores (distancia, movimiento, coordenadas GPS sobre un mapa embebido) y muestra en una tabla dinámica el log histórico de amenazas de la Inteligencia Artificial.

###  Control Remoto (Actuador desde Interfaz)
El Dashboard incluye botones de control. Al presionar "Activar Motores" o "Encender Estrobo", la interfaz web escribe en la rama `/actuadores` de Firebase. El puente Python detecta este cambio (`PATCH`) e inmediatamente publica un mensaje MQTT (`vestaguard/control/...`) que el ESP32 recibe, accionando mecánicamente el componente físico en el chaleco.

###  Garantía de Privacidad (Anonimización visual)
Dado que el chaleco capta imágenes en la vía pública, es imperativo proteger la privacidad. Antes de que el servidor de IA envíe el frame JPEG codificado en Base64 a Firebase, ejecuta una rutina de ofuscación (difuminado facial mediante un filtro gaussiano en la región de interés del rostro) en OpenCV. Esto garantiza que ninguna imagen sensible o identificable se almacene en la base de datos alojada en la nube de Google.

---

## 2. Guía de configuración paso a paso

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

1. En Firebase Console → ícono  → **Configuración del proyecto**
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
2. Expande el panel ** Configuración de Firebase**
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


## 11. Análisis Individual del Equipo

### Rangel Hernandez Aldo (22240272)
- **Responsabilidad principal:** Desarrollo del Dashboard en HTML/JS y configuración de la consola de Firebase Realtime Database.
- **Problemas encontrados:** Durante las primeras pruebas, los registros de alertas de la Inteligencia Artificial se sobrescribían constantemente en la base de datos, dejando solo el último evento en lugar de crear un historial.
- **Soluciones aplicadas:** Modifiqué el uso de la función `put()` (sobreescritura) por llamadas `POST` o `addto()` en la API REST de Firebase. Esto forzó a Firebase a generar claves automáticas (push IDs como `-Nabc123...`) para cada nueva alerta de la IA, creando un log estructurado.
- **Conclusión personal:** "Lograr la sincronización en tiempo real mediante WebSockets de Firebase eliminó la necesidad de hacer peticiones HTTP constantes (polling), lo cual hizo que el Dashboard reaccione de forma instantánea a los estímulos del chaleco. Además, el manejo de comandos con timestamp resolvió de forma elegante las limitaciones de deduplicación de Firebase."

### Álvarez Guevara Estefanía Guadalupe (23240077)
- **Responsabilidad principal:** Enlace de la transmisión de imágenes (Base64) desde OpenCV hacia Firebase, y garantía de privacidad.
- **Problemas encontrados:** Enviar fotografías del rostro de los transeúntes hacia una base de datos en la nube (Google Cloud) implicaba una fuerte violación a la privacidad, y codificar imágenes JPEG completas volvía inestable la conexión JSON.
- **Soluciones aplicadas:** Implementé la anonimización: un algoritmo de *blur* (difuminado) en OpenCV que censura la cara del atacante antes de convertir el frame a Base64. Adicionalmente, reduje la resolución al vuelo a 320x240 para no saturar el payload de Firebase.
- **Conclusión personal:** "Enlazar la salida de la Red Neuronal (Caffe SSD) con Firebase a través del puente Python nos permitió tener un registro histórico visual de las amenazas de forma ética. Comprobar que una fotografía ofuscada puede viajar desde el microcontrolador hasta el navegador web en tiempo real fue uno de los mayores logros de la integración Cloud-IA."

### Reyes Gutierrez Pablo Alberto (23240055)
- **Responsabilidad principal:** Supervisión de la arquitectura, conectividad de telemetría e integración física del actuador controlado por web.
- **Problemas encontrados:** El ESP32 colapsaba por falta de memoria (Out Of Memory) y latencia si intentaba hacer demasiadas peticiones HTTP con la librería `urequests` directamente a la API REST de Firebase, afectando la respuesta de la Máquina de Estados.
- **Soluciones aplicadas:** Adopté la decisión arquitectónica de delegar toda la carga de nube al puente Python (`firebase_vestaguard.py`). El ESP32 solo publica en MQTT local (muy ligero), y Python se encarga de subir los datos a Firebase mediante HTTPS. 
- **Conclusión personal:** "Poder observar en el Dashboard de Firebase el reflejo exacto de los sensores físicos (Ultrasónico, PIR y GPS) y ver los motores accionándose en milisegundos tras hacer clic en una página web, confirmó que la topología elegida (Chaleco -> MQTT -> Servidor -> Firebase) es la correcta para sistemas IoT de baja latencia."
