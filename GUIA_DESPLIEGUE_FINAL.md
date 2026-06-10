# VestaGuard â€” GuÃ­a de EjecuciÃ³n RÃ¡pida (DÃ­a de la PresentaciÃ³n)
**Chaleco HÃ¡ptico Inteligente para Seguridad Urbana**
Ãlvarez Guevara EstefanÃ­a (23240077) Â· Rangel HernÃ¡ndez Aldo (23240272) Â· Reyes GutiÃ©rrez Pablo Alberto (23240055)

> **PRERREQUISITO:** Se asume que todo el cÃ³digo ya estÃ¡ subido a los ESP32, el hardware soldado, y las librerÃ­as instaladas. Esta guÃ­a es estrictamente para la ejecuciÃ³n durante la presentaciÃ³n.

---

## PASO 1: Verificar la IP de la Laptop
1. Abre un CMD y escribe `ipconfig`.
2. Tu DirecciÃ³n IPv4 oficial es **10.254.179.79**.
3. *(Opcional)* Si la IP cambiÃ³ desde la Ãºltima vez que programaste, debes actualizarla en el archivo `secrets.py` de ambos ESP32.

---

## PASO 2: Levantar los Servidores en la Laptop

Abre **4 ventanas nuevas de CMD** (o 4 terminales divididas en Visual Studio Code) y colÃ³calas donde puedas verlas.

### â–¶ TERMINAL 1 (Mosquitto - TrÃ¡fico de Red)
Esta terminal manejarÃ¡ la comunicaciÃ³n entre el chaleco, la cÃ¡mara y la laptop.
```cmd
mosquitto -c "C:\Users\PR11\OneDrive\Documentos\7MO-SEM\Sistemas Programables\Unidad 4\Proyecto_Final_\DESPLIEGUE\mosquitto_local.conf" -v
```
*(Nota: Si te dice que el puerto ya estÃ¡ en uso, entra a un CMD como Administrador y ejecuta `net stop mosquitto` primero).*

* DÃ©jala abierta. VerÃ¡s texto pasando rÃ¡pido cuando los equipos se conecten.

### â–¶ TERMINAL 2 (Servidor de Inteligencia Artificial)
Esta terminal recibe las fotos de la cÃ¡mara y detecta si hay personas.
```cmd
cd "C:\Users\PR11\OneDrive\Documentos\7MO-SEM\Sistemas Programables\Unidad 4\Proyecto_Final_\DESPLIEGUE\LAPTOP_SERVIDOR"
python servidor_ia.py
```
* Espera a que diga: `[IA] Servidor activo. Esperando imagenes de ESP32-CAM y telemetria...`

### â–¶ TERMINAL 3 (Firebase - Base de Datos en la Nube)
Esta terminal sube todos los registros de los sensores a internet para el Dashboard.
```cmd
cd "C:\Users\PR11\OneDrive\Documentos\7MO-SEM\Sistemas Programables\Unidad 4\Proyecto_Final_\DESPLIEGUE\LAPTOP_SERVIDOR"
python firebase_vestaguard.py
```
* Espera a que diga: `[Firebase] Conectado` y `[Sistema] Puente activo`.

### â–¶ TERMINAL 4 (Servidor Web del Dashboard)
Esta terminal sirve los archivos para que puedas acceder al dashboard desde tu celular en la misma red Wi-Fi.
```cmd
cd "C:\Users\PR11\OneDrive\Documentos\7MO-SEM\Sistemas Programables\Unidad 4\Proyecto_Final_\DESPLIEGUE\LAPTOP_DASHBOARD"
python -m http.server 8080
```
* DÃ©jala corriendo en segundo plano.

---

## PASO 3: Encender el Hardware (BaterÃ­a)

ï¸ **Â¡CRÃTICO ANTES DE ENCENDER!**
* AsegÃºrate de que el pin **GPIO0** de la ESP32-CAM **NO** estÃ© conectado a GND (debe estar libre para que arranque el cÃ³digo y no se quede en modo programaciÃ³n).
* AsegÃºrate de que tu baterÃ­a pueda entregar al menos 1A a 5V para evitar reinicios por *Brownout* al prender el flash.

1. **Enciende el Chaleco (ESP32 Principal):** Conecta la baterÃ­a.
   *  VerÃ¡s en la Terminal 1 (Mosquitto) que se conectÃ³ el ESP32.
2. **Enciende la CÃ¡mara (ESP32-CAM):** Conecta la baterÃ­a.
   *  VerÃ¡s en la Terminal 1 (Mosquitto) que se conectÃ³ la cÃ¡mara.

---

## PASO 4: El Dashboard Visual

1. **Desde tu Laptop:** Abre tu navegador y entra a `http://localhost:8080/dashboard.html`
2. **Desde tu Celular:** AsegÃºrate de estar en la misma red Wi-Fi que la laptop y entra a la direcciÃ³n oficial: **`http://10.254.179.79:8080/dashboard.html`**
3. Dale clic al Ã­cono de engrane (ï¸) y verifica que estÃ©n los datos de conexiÃ³n de tu Firebase.
4. El indicador arriba a la derecha debe decir ** ONLINE**.
5. **Â¡PRUEBA LA CÃMARA!** Presiona el botÃ³n "Capturar" en el celular. DeberÃ­as ver la foto aparecer en el visor en aproximadamente 1 a 2 segundos.

** Â¡SISTEMA LISTO PARA DEMOSTRACIÃ“N!** Ya puedes interactuar con los sensores y el dashboard.

---

## ANEXO 1 â€” TÃ“PICOS MQTT DEL SISTEMA (Para debugear)

| TÃ³pico | Publicado por | Payload ejemplo |
|---|---|---|
| `vestaguard/telemetria/sensores` | ESP32 chaleco | `{"distancia_cm":145.3,"pir":true,...}` |
| `vestaguard/camara/frame` | ESP32-CAM | bytes JPEG en base64 |
| `vestaguard/ia/resultado` | Servidor IA | `{"clasificacion":"amenaza","confianza":0.92}` |
| `vestaguard/ia/comando` | Servidor IA | `ALERTA_TOTAL` / `VIBRACION_FUERTE` / `MANTENER` |
| `vestaguard/control/camara_disparo` | Dashboard/Firebase | `CAPTURAR` |
| `vestaguard/control/rgb` | Dashboard HTML | `ROJO` / `AZUL` / `APAGAR` |
| `vestaguard/alerta/sos` | ESP32 chaleco | `{"evento":"panico","timestamp":"..."}` |

---

## ANEXO 2 â€” COMPORTAMIENTO DE LOS ESTADOS (FSM)

| Estado FSM | CondiciÃ³n de activaciÃ³n | LED RGB | Motores Vibradores |
|---|---|---|---|
| **NORMAL** | Sin amenaza detectada |  Verde (o Azul) | Apagados |
| **VIGILANCIA** | Solo PIR activo (sin distancia crÃ­tica) |  Azul (Cian) | Apagados |
| **ALERTA** | UltrasÃ³nico < 120cm + PIR detecta |  Violeta/Ambar | Hombros alternados |
| **AMENAZA** | UltrasÃ³nico < 80cm + PIR + IA detecta persona |  Rojo | Ambos hombros |
| **EMERGENCIA** | BotÃ³n de pÃ¡nico O caÃ­da detectada |  Rojo rÃ¡pido | Ambos hombros + rÃ¡pido |

