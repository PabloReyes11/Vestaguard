# Integración Total MQTT (ESP32 ↔ Python)

Repositorio de entrega para la práctica de Sistemas Programables.

## Contenido de entrega
- `dispositivos.py`: Capa HAL para sensores y actuadores.
- `main.py`: Lógica MQTT en la ESP32.
- `servidor.py`: Servidor Python con telemetría y comandos.
- `conclusion_RG.md`: Conclusión y análisis individual.
- `lib/umqtt/simple.py`: Librería MQTT para MicroPython.

## Arquitectura de Red y Matriz de Tópicos MQTT

El sistema implementa un modelo de publicación/suscripción asincrónico sobre Wi-Fi. El ESP32 actúa como nodo periférico gestionando la capa física (sensores y actuadores) a través de una HAL. La aplicación móvil (MQTT Dash) y el script Python operan como clientes de interfaz y registro de telemetría.

| Componente / Interfaz | Tópico MQTT | Flujo de Datos (QoS 0) | Payload |
|--------|-----------|-----|---------|
| Sensores (PIR, Ultrasónico, MPU6050) | `vestaguard/telemetria/sensores` | ESP32 Publica → Python/App Suscriben | `{"pir":"NO","distancia_cm":154.3,"aceleracion_y":-0.02}` |
| Motor Vibrador | `vestaguard/control/vibrador` | App/Python Publican → ESP32 Suscribe | `ON` / `OFF` |
| LED RGB | `vestaguard/control/rgb` | App/Python Publican → ESP32 Suscribe | `ROJO` / `VERDE` / `APAGAR` |

**Flujo resumido:** El ESP32 publica telemetría JSON cada 2 s hacia el broker Mosquitto. El servidor Python (servidor.py) se suscribe y muestra los datos con marca de tiempo. Los comandos de control viajan en dirección contraria: MQTT Dash o servidor.py publican en los tópicos de control y la ESP32 delega la acción física a la clase HAL (ActuatorBox).

## Resumen de lo que debe verificarse
- El código debe tener encabezado con objetivo, integrantes y proyecto.
- La ESP32 debe publicar telemetría y recibir comandos por MQTT.
- La lógica MQTT debe usar la HAL y no tocar hardware directamente.
- El servidor Python debe mostrar timestamps al recibir telemetría.
- La entrega debe incluir evidencia de funcionamiento real del hardware.

## Análisis individual

### Alvarez Guevara Estefania Guadalupe (23240077)
**Problema:** El ESP32 no se conectaba al broker MQTT porque el identificador único (ID) que enviaba contenía caracteres crudos que corrompían la trama de conexión. Adicionalmente, en la parte física, el motor de vibración no activaba por dos razones: insuficiencia de potencia en la alimentación desde el pin 3.3V, y el transistor 2N2222 estaba conectado en polaridad invertida (pines en orden incorrecto).

**Solución:** Para la capa de red, se importó ubinascii para convertir el ID sucio a formato hexadecimal legible que el servidor MQTT interpretara correctamente. Para la capa física, se reconfiguró la alimentación desde el pin VIN (5V) para proporcionar suficiente corriente al motor, y se corrigió la polaridad del transistor (base, colector, emisor) girándolo 180°. Para optimizar la experiencia de pruebas, se adoptó MQTT Dash en dispositivo móvil como interfaz de control, separando completamente el flujo de telemetría entrante del de comandos salientes.

**Conclusión personal:** La arquitectura de capas (HAL separada de lógica MQTT) fue fundamental para identificar rápidamente que los problemas de conectividad que parecían ser defectos de red eran en realidad problemas de voltaje e inversión de polaridad. Esta separación permitió realizar correcciones precisas sin afectar el código ya funcional, demostrando que en sistemas IoT integrados, la claridad arquitectónica es más importante que la velocidad inicial de implementación.

### Rangel Hernandez Aldo (23240272)
**Problema:** El cliente MQTT y algunos componentes físicos no respondían como se esperaba durante las primeras pruebas. El identificador de cliente con bytes crudos provocaba rechazos silenciosos en el broker Mosquitto y las conexiones físicas mal aseguradas generaban lecturas de sensores inconsistentes que confundían la lógica de control.

**Solución:** Se corrigió el identificador MQTT codificándolo a hexadecimal, se verificó la configuración de red (IP del broker, puerto 1883 y conexión a la misma WLAN) y se revisaron y aseguraron todas las conexiones físicas del protoboard que generaban falsos contactos e interferencias en las lecturas.

**Conclusión personal:** La investigación sistemática de cada capa permitió confirmar que los problemas iniciales de conectividad no eran externos sino resultado de configuraciones internas. Al reintentar después de la investigación exhaustiva, el sistema funcionó correctamente. Un aprendizaje crítico surgió al descubrir que el LED RGB requería señales específicas (ROJO, VERDE, AZUL) en lugar de simples comandos ON/OFF; esto demostró que la especificación exacta del protocolo y los payloads es fundamental. El uso de MQTT con una estructura de tópicos jerárquica y bien definida facilitó localizar errores de software (ID inválido, parámetros de conexión) y de hardware (falsos contactos) de forma independiente. La separación de responsabilidades entre la capa de red y la HAL redujo significativamente el tiempo total de depuración, enseñanza valiosa para prácticas futuras.

### Reyes Gutierrez Pablo Alberto (23240055)
**Problema:** Durante la integración MQTT de la ESP32, se presentaron fallas críticas en múltiples capas del sistema. Primero, el cliente MQTT no podía establecer conexión con el broker debido a que el identificador único del microcontrolador se enviaba como bytes crudos, corrompiendo la trama de conexión de umqtt.simple. Posteriormente, al intentar enviar comandos desde la consola de VS Code, los mensajes no se procesaban correctamente porque la telemetría publicada cada 2 segundos (leer_movimiento, leer_distancia, leer_aceleracion) interrumpía el texto en el terminal, generando asincronía. Finalmente, aun cuando los mensajes MQTT llegaban correctamente a la ESP32, el motor vibrador permanecía inactivo, sugiriendo una falla de hardware que requería diagnóstico diferencial entre red y electrónica.

**Solución:** La solución se implementó por capas de acuerdo a la arquitectura del proyecto. En la capa MQTT, se importó la librería ubinascii para convertir el identificador único (machine.unique_id()) a una cadena hexadecimal legible que respetara la especificación del protocolo. En la capa de interacción usuario, se abandonó el uso de la consola de VS Code y se adoptó la aplicación MQTT Dash en dispositivo móvil como cliente de control remoto, aislando completamente el flujo de telemetría entrante del de comandos salientes. En la capa física, mediante troubleshooting aislado (ejecutando código de prueba directo a los pines sin MQTT), se identificaron dos errores críticos: el transistor 2N2222 estaba instalado invertido (180°) debido a confusión en la variante de pines, y la alimentación de la protoboard provenía del pin de 3.3V del ESP32, insuficiente en corriente para activar un motor de DC. Se corrigió la polaridad del transistor (base, colector, emisor) y se reconfiguró la alimentación al pin de 5V (VIN) del ESP32. Con estos cambios, el sistema de control remoto funcionó sin fallos.

**Conclusión personal:** Esta práctica consolidó mi comprensión de que en sistemas IoT integrados, el software y el hardware no pueden considerarse independientes. La arquitectura de la HAL (Capa de Abstracción de Hardware) fue crucial: permitió ejecutar pruebas de comunicación MQTT completamente desacopladas de la activación física de actuadores, evitando daños por prueba-error. Al aislar fallas por capas (red → lógica → hardware), descubrí que un problema aparentemente de conectividad era en realidad un problema de caída de voltaje y polaridad en el protoboard. Aprendí que la depuración metódica, tanto a nivel de bits en la computadora como de voltajes en los cables, es esencial para integrar sistemas embebidos. Esta experiencia refuerza la importancia de mantener límites claros entre capas arquitectónicas durante el desarrollo.

## Evidencias de Funcionamiento

Las evidencias de funcionamiento del sistema (capturas de pantalla de telemetría en Thonny, logs en servidor.py con timestamps, MQTT Dash con comandos activos) se adjuntan en el documento PDF de entrega.

## Verificación del Repositorio GitHub

### Archivos requeridos en el repositorio
- `main.py` — Lógica MQTT de la ESP32; callback `enrutar_topico()` invoca explícitamente la HAL.
- `dispositivos.py` — Capa HAL (SensorBox / ActuatorBox); sin acceso directo al hardware desde la lógica de red.
- `servidor.py` — Servidor Python con timestamps y consola de comandos interactiva.
- Los tres archivos tienen el bloque docstring con OBJETIVO, INTEGRANTES y PROYECTO en la cabecera.
- El repositorio está configurado como público para evitar error 404 durante la revisión.

## Conclusiones Globales de Despliegue Físico (Hardware Final)
- **Topología USB Dual (PowerBank):** Para simplificar el hardware y garantizar 5V estables sin caídas de tensión por el arranque de los motores, implementamos una PowerBank de doble salida. El Puerto 1 alimenta al ESP32 principal y al riel de potencia de los motores, mientras que el Puerto 2 alimenta de forma aislada a la ESP32-CAM, manteniendo una tierra común (GND).
- **Asincronía Total:** El código dispositivos.py controla todo el ecosistema de hardware físico sin latencias gracias a uasyncio.