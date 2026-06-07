# VestaGuard — Guía de Ejecución Rápida (Día de la Presentación)
**Chaleco Háptico Inteligente para Seguridad Urbana**
Álvarez Guevara Estefanía (23240077) · Rangel Hernández Aldo (23240272) · Reyes Gutiérrez Pablo Alberto (23240055)

> **PRERREQUISITO:** Se asume que todo el código ya está subido a los ESP32, el hardware soldado, y las librerías instaladas. Esta guía es estrictamente para la ejecución durante la presentación.

---

## PASO 1: Verificar la IP de la Laptop
1. Abre un CMD y escribe `ipconfig`.
2. Tu Dirección IPv4 oficial es **10.254.179.79**.
3. *(Opcional)* Si la IP cambió desde la última vez que programaste, debes actualizarla en el archivo `secrets.py` de ambos ESP32.

---

## PASO 2: Levantar los Servidores en la Laptop

Abre **4 ventanas nuevas de CMD** (o 4 terminales divididas en Visual Studio Code) y colócalas donde puedas verlas.

### ▶ TERMINAL 1 (Mosquitto - Tráfico de Red)
Esta terminal manejará la comunicación entre el chaleco, la cámara y la laptop.
```cmd
mosquitto -c "C:\Users\PR11\OneDrive\Documentos\7MO-SEM\Sistemas Programables\Unidad 4\Proyecto_Final_\DESPLIEGUE\mosquitto_local.conf" -v
```
*(Nota: Si te dice que el puerto ya está en uso, entra a un CMD como Administrador y ejecuta `net stop mosquitto` primero).*

* Déjala abierta. Verás texto pasando rápido cuando los equipos se conecten.

### ▶ TERMINAL 2 (Servidor de Inteligencia Artificial)
Esta terminal recibe las fotos de la cámara y detecta si hay personas.
```cmd
cd "C:\Users\PR11\OneDrive\Documentos\7MO-SEM\Sistemas Programables\Unidad 4\Proyecto_Final_\DESPLIEGUE\LAPTOP_SERVIDOR"
python servidor_ia.py
```
* Espera a que diga: `[IA] Servidor activo. Esperando imagenes de ESP32-CAM y telemetria...`

### ▶ TERMINAL 3 (Firebase - Base de Datos en la Nube)
Esta terminal sube todos los registros de los sensores a internet para el Dashboard.
```cmd
cd "C:\Users\PR11\OneDrive\Documentos\7MO-SEM\Sistemas Programables\Unidad 4\Proyecto_Final_\DESPLIEGUE\LAPTOP_SERVIDOR"
python firebase_vestaguard.py
```
* Espera a que diga: `[Firebase] Conectado` y `[Sistema] Puente activo`.

### ▶ TERMINAL 4 (Servidor Web del Dashboard)
Esta terminal sirve los archivos para que puedas acceder al dashboard desde tu celular en la misma red Wi-Fi.
```cmd
cd "C:\Users\PR11\OneDrive\Documentos\7MO-SEM\Sistemas Programables\Unidad 4\Proyecto_Final_\DESPLIEGUE\LAPTOP_DASHBOARD"
python -m http.server 8080
```
* Déjala corriendo en segundo plano.

---

## PASO 3: Encender el Hardware (Batería)

️ **¡CRÍTICO ANTES DE ENCENDER!**
* Asegúrate de que el pin **GPIO0** de la ESP32-CAM **NO** esté conectado a GND (debe estar libre para que arranque el código y no se quede en modo programación).
* Asegúrate de que tu batería pueda entregar al menos 1A a 5V para evitar reinicios por *Brownout* al prender el flash.

1. **Enciende el Chaleco (ESP32 Principal):** Conecta la batería.
   *  Verás en la Terminal 1 (Mosquitto) que se conectó el ESP32.
2. **Enciende la Cámara (ESP32-CAM):** Conecta la batería.
   *  Verás en la Terminal 1 (Mosquitto) que se conectó la cámara.

---

## PASO 4: El Dashboard Visual

1. **Desde tu Laptop:** Abre tu navegador y entra a `http://localhost:8080/dashboard.html`
2. **Desde tu Celular:** Asegúrate de estar en la misma red Wi-Fi que la laptop y entra a la dirección oficial: **`http://10.254.179.79:8080/dashboard.html`**
3. Dale clic al ícono de engrane (️) y verifica que estén los datos de conexión de tu Firebase.
4. El indicador arriba a la derecha debe decir ** ONLINE**.
5. **¡PRUEBA LA CÁMARA!** Presiona el botón "Capturar" en el celular. Deberías ver la foto aparecer en el visor en aproximadamente 1 a 2 segundos.

** ¡SISTEMA LISTO PARA DEMOSTRACIÓN!** Ya puedes interactuar con los sensores y el dashboard.

---

## ANEXO 1 — TÓPICOS MQTT DEL SISTEMA (Para debugear)

| Tópico | Publicado por | Payload ejemplo |
|---|---|---|
| `vestaguard/telemetria/sensores` | ESP32 chaleco | `{"distancia_cm":145.3,"pir":true,...}` |
| `vestaguard/camara/frame` | ESP32-CAM | bytes JPEG en base64 |
| `vestaguard/ia/resultado` | Servidor IA | `{"clasificacion":"amenaza","confianza":0.92}` |
| `vestaguard/ia/comando` | Servidor IA | `ALERTA_TOTAL` / `VIBRACION_FUERTE` / `MANTENER` |
| `vestaguard/control/camara_disparo` | Dashboard/Firebase | `CAPTURAR` |
| `vestaguard/control/rgb` | Dashboard HTML | `ROJO` / `AZUL` / `APAGAR` |
| `vestaguard/alerta/sos` | ESP32 chaleco | `{"evento":"panico","timestamp":"..."}` |

---

## ANEXO 2 — COMPORTAMIENTO DE LOS ESTADOS (FSM)

| Estado FSM | Condición de activación | LED RGB | Motores Vibradores |
|---|---|---|---|
| **NORMAL** | Sin amenaza detectada |  Verde (o Azul) | Apagados |
| **VIGILANCIA** | Solo PIR activo (sin distancia crítica) |  Azul (Cian) | Apagados |
| **ALERTA** | Ultrasónico < 120cm + PIR detecta |  Violeta/Ambar | Hombros alternados |
| **AMENAZA** | Ultrasónico < 80cm + PIR + IA detecta persona |  Rojo | Ambos hombros |
| **EMERGENCIA** | Botón de pánico O caída detectada |  Rojo rápido | Ambos hombros + rápido |
