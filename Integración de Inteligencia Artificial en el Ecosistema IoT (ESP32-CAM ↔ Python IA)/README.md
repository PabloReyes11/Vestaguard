# Integración de Inteligencia Artificial en el Ecosistema IoT (ESP32-CAM ↔ Python IA)

En términos de arquitectura, este bloque cumple con la consigna de la materia de implementar Inteligencia Artificial como un nodo activo y funcional dentro del sistema IoT.

La arquitectura de visión se resume en el siguiente flujo Extremo a Extremo:
`Sensor o cámara ESP32-CAM -> MQTT / HTTP -> Servidor Python con IA -> MQTT -> Actuador en ESP32`

## 1. Cumplimiento de Rúbrica de Inteligencia Artificial

###  Prueba Estática (Validación sin Red)
Antes de enviar imágenes por MQTT, el modelo fue validado localmente procesando imágenes estáticas para garantizar su precisión. El script `validacion_estatica.py` carga imágenes de prueba y demuestra que la heurística de visión (Caffe SSD) identifica correctamente los rostros y emite comandos de predicción antes de depender de la conectividad de red.

###  Pipeline Extremo a Extremo (IA activa el mundo físico)
El sistema demuestra un pipeline completo bidireccional:
1. La ESP32-CAM captura un frame visual.
2. El servidor Python lo procesa mediante la IA.
3. El servidor Python toma una decisión automática (detectar a una persona).
4. El servidor publica el resultado en `vestaguard/ia/comando`.
5. La Máquina de Estados (FSM) del ESP32 NodeMCU recibe el comando por MQTT y activa los actuadores físicos correspondientes (vibración fuerte y alerta visual en el LED RGB) basados en lo que la IA "vio".

###  IA Funcional (Datos esenciales)
La ESP32-CAM no funciona como un simple circuito cerrado de televisión. Su rol es funcional y crítico para el proyecto: aporta el frame que alimenta la toma de decisiones del chaleco. El chaleco detecta proximidad con el sensor ultrasónico, pero es la IA la que confirma si el obstáculo es una persona, eliminando los falsos positivos y habilitando la **Fusión de Sensores (Sensor Fusion)**.

###  Sustentación Técnica (Arquitectura del Modelo y Precisión)
- **Arquitectura del Modelo:** Se utiliza una Red Neuronal Profunda (DNN) de tipo *Single Shot MultiBox Detector (SSD)* basada en el framework Caffe (Caffe SSD).
- **Procesamiento:** El análisis de los frames se realiza mediante el módulo `dnn` de OpenCV (`cv2.dnn.readNetFromCaffe`).
- **Precisión:** El modelo pre-entrenado ofrece una precisión probada superior al **92%** en detección de rostros humanos, incluso en condiciones de variada iluminación y a diferentes escalas.
- **Flujo de Datos:** Para evitar desbordar la memoria de los microcontroladores, la inferencia visual (el procesamiento matemático matricial) ocurre exclusivamente en el Servidor Python, mientras que las placas actúan como emisores de datos y ejecutores mecánicos.

---

## 2. Análisis Individual del Equipo

### Álvarez Guevara Estefanía Guadalupe (23240077)
**Responsabilidad principal:** Encargada principal de la Inteligencia Artificial (IA) y del módulo de la cámara (ESP32-CAM). Desarrolló el servidor en Python usando OpenCV y programó el código de la cámara.
**Problemas encontrados:** Al principio fue un reto hacer que la ESP32-CAM mandara las imágenes de forma fluida. A veces el video se quedaba pasmado o la placa se desconectaba por sobreexigencia. Procesar las imágenes con Python y OpenCV provocaba que el programa arrojara falsos positivos inicialmente. Además, sincronizar el "pipeline" para que el programa en la computadora platicara en tiempo real con el chaleco fue complicado por la asincronía de los tiempos.
**Soluciones aplicadas:** Para evadir restricciones físicas (pines DTR/RTS) que impedían subir el código normal, inyectamos MicroPython por bloques (chunks). En la cámara ajusté la compresión JPEG para tener transmisión rápida sin sobrecalentar la tarjeta. Optimicé los algoritmos de visión artificial para evitar saturación de la computadora, definiendo reglas claras en MQTT para mandar señales solo cuando había una detección 100% confirmada.
**Conclusión personal:** La IA no es magia, requiere mucha sincronización. Aprendí que de nada sirve tener un código de IA súper inteligente si no se comunica bien y a tiempo con la Máquina de Estados del dispositivo físico. Mi aportación le dio "visión y cerebro" al sistema VestaGuard, demostrando que podemos integrar software avanzado (Python/OpenCV) con hardware en tiempo real.

### Rangel Hernandez Aldo (22240272)
**Responsabilidad principal:** Apoyo en conexiones físicas, cableado de componentes, y desarrollador del puente hacia la base de datos y la nube.
**Problemas encontrados:** Fallo durante el proceso de soldado en algunos cables y componentes debido a soldadura de mala calidad, retrasando el avance. Falsos contactos en cables que estaban incorrectamente soldados, provocando que los actuadores no recibieran el comando que enviaba el servidor de IA por la red. Adicionalmente, componentes averiados demostraron ser un cuello de botella.
**Soluciones aplicadas:** Análisis minucioso del cableado antes de enviar los comandos MQTT del servidor de IA. Se repitió el soldado de forma correcta para garantizar que las vibraciones inducidas por la IA realmente accionaran mecánicamente los actuadores. Comprobación de calidad de voltaje antes de implementación final.
**Conclusión personal:** La parte física del proyecto demostró requerir mucho más trabajo del contemplado. Cuando la IA toma una decisión, el hardware físico debe ser impecable para reaccionar. Fue muy satisfactorio trabajar tanto en la base de datos como en lo físico; me ayudó a entender que un pipeline de datos abarca desde el código en la nube hasta el último milímetro de soldadura en el microcontrolador.

### Reyes Gutierrez Pablo Alberto (23240055)
**Responsabilidad principal:** Conexiones físicas, ensamblaje del chaleco y verificación de la integración electromecánica del sistema y su estabilidad ante la red.
**Problemas encontrados:** La ESP32-CAM consumía demasiada corriente al usar el flash y transmitir por WiFi, causando inestabilidad cuando los motores vibradores funcionaban al mismo tiempo. Además, integrar la placa de la cámara sin aislarla eléctricamente de la placa base amenazaba con dañar el ESP32 principal.
**Soluciones aplicadas:** Se organizó la alimentación aislando a la ESP32-CAM del bus de potencia principal; se diseñó el sistema para que la ESP32-CAM opere como nodo de visión completamente independiente del chaleco, únicamente vinculados lógicamente a través del Servidor de IA en la nube. Se rediseñó la etapa de potencia de los motores con transistores para que los comandos de la IA no sobrecargaran al NodeMCU.
**Conclusión personal:** La parte física del proyecto es la que sostiene toda la abstracción de software. Si la alimentación o la etapa de potencia fallan, la IA y la comunicación MQTT no sirven de nada. Entendí que el proyecto debe mantenerse modular: el ESP32 controla la lógica y los motores, la ESP32-CAM aporta la visión, y la laptop/nube procesa la IA. Mi aporte centrado en la estabilidad física permitió que la IA de este entregable pudiera demostrarse con éxito en el mundo real.

---

## 3. Estructura del repositorio de esta entrega
- `servidor_ia.py`: Backend principal con MQTT, OpenCV y lógica de inferencia de IA.
- `esp32cam_publicador.py`: Firmware de la ESP32-CAM para capturar y publicar imágenes JPEG en Base64.
- `validacion_estatica.py`: Evidencia de validación local del modelo antes de red MQTT (Cumplimiento Prueba Estática).
- `modelo/`: Carpeta que contiene los pesos `.caffemodel` y arquitectura `.prototxt` del modelo OpenCV DNN.
