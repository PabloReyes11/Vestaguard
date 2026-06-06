# Plantilla practica MQTT VestaGuard

## Objetivo
Usa esta plantilla como base para documentar la practica MQTT con el hardware actual de VestaGuard. La ESP32 publica datos de sensores y la laptop publica comandos hacia los actuadores.

## Arquitectura
- ESP32 -> publica telemetria
- Laptop/Python -> recibe telemetria y publica comandos
- Mosquitto -> broker central
- HAL -> abstrae el hardware en `dispositivos.py`

## T_topics de la practica
- `vestaguard/telemetria/sensores`
- `vestaguard/telemetria/gps`
- `vestaguard/control/motores`
- `vestaguard/control/rgb`
- `vestaguard/control/relevador`
- `vestaguard/control/estado`

## Telemetria que se reporta
- `pir`
- `distancia_cm`
- `aceleracion_y`
- `boton_panico`
- `gps_latitud`
- `gps_longitud`
- `gps_altitud_m`
- `gps_satelites`
- `gps_fijado`

## Comandos que recibe la ESP32
- `MOTOR_ON`
- `MOTOR_OFF`
- `RGB_ROJO`
- `~~RGB_VERDE~~` (EXCLUIDO: no se usa por hardware)
- `RGB_AZUL`
- `RGB_OFF`
- `RELE_ON`
- `RELE_OFF`
- `TODO_ON`
- `TODO_OFF`

## Resumen de hardware
- PIR en GPIO 19
- HC-SR04 en GPIO 5 y 18
- MPU6050 en GPIO 21 y 22
- GPS NEO-6M en GPIO 16 y 17
- Boton de panico en GPIO 32
- Motores vibradores en GPIO 25, 27, 26 y 4
- LED RGB en GPIO 13, ~~14 (Verde EXCLUIDO)~~ y 33 (solo Rojo y Azul)
- Relevador en GPIO 23

## Estructura minima sugerida
### `dispositivos.py`
- `SensorBox`
- `ActuatorBox`
- metodos para leer sensores y activar salidas

### `main.py`
- conexion WiFi
- conexion MQTT
- suscripcion a topics de control
- publicacion periodica de telemetria

### `servidor.py`
- suscripcion a telemetria
- impresion con timestamp
- publicacion de comandos desde la consola

## Ejemplo de flujo
1. `main.py` publica JSON en `vestaguard/telemetria/sensores`.
2. `servidor.py` lo imprime con timestamp.
3. El usuario escribe `MOTOR_ON` en la consola.
4. `servidor.py` publica `vestaguard/control/motores` con payload `ON`.
5. `main.py` recibe el comando y activa los motores desde la HAL.

## Nota para el reporte
Explica que la practica ya no toca pines directamente desde MQTT. El acceso al hardware queda encapsulado en la HAL para evitar errores y mantener el proyecto ordenado.