Análisis individual - Estefanía Guadalupe Álvarez Guevara (23240077)
Proyecto: VestaGuard

Integrante: Estefanía Guadalupe Álvarez Guevara

Código: 23240077

Responsabilidad principal: Encargada principal de la Inteligencia Artificial (IA) y del módulo de la cámara (ESP32-CAM). Específicamente, desarrollé el servidor en Python usando OpenCV, programé el código de la cámara (esp32cam_publicador.py) y creé el puente de comunicación (pipeline) entre la IA y la lógica principal del chaleco (la Máquina de Estados o FSM).

Lo que se me dificultó y Problemas encontrados
La transmisión de la cámara: Al principio fue un reto hacer que la ESP32-CAM mandara las imágenes de forma fluida. A veces el video se quedaba pasmado (mucho lag) o la placa se desconectaba si le exigíamos demasiada calidad.

Procesamiento de las imágenes: Trabajar con Python y OpenCV tiene su nivel de complejidad. Lograr que el programa reconociera correctamente lo que queríamos detectar sin confundirse (falsos positivos) tomó bastante prueba y error.

Conectar dos mundos distintos: Lo que más me costó trabajo fue el "pipeline" o puente de comunicación. Tenía que hacer que mi programa de Inteligencia Artificial en la computadora platicara en tiempo real con la tarjeta del chaleco (FSM). Si la IA detectaba algo, tenía que avisarle al chaleco rapidísimo para que reaccionara, y coordinar esos tiempos sin que el sistema se trabara fue muy complicado.

Soluciones que aplicamos
Para la cámara: Logramos evadir las restricciones físicas de la placa (pines DTR/RTS) que impedían subir el código normal. Implementamos MicroPython nativo en la ESP32-CAM, y para programarla desarrollamos un script en Python que inyecta el código en pequeños bloques (chunks) directamente por consola. Además, en el código esp32cam_publicador.py ajusté la configuración para comprimir las imágenes, logrando una transmisión rápida y estable sin sobrecalentar la tarjeta.

Para el servidor Python/OpenCV: Depuré el código para que solo procesara lo estrictamente necesario. Optimicé los algoritmos de visión artificial para que la computadora no se saturara y pudiera analizar las imágenes en tiempo real.

Para conectar la IA con el chaleco: Definimos reglas muy claras de comunicación. Aseguré que el servidor de Python solo le mandara señales específicas y ligeras a la lógica del chaleco (FSM) únicamente cuando había una detección confirmada, evitando bombardear el ESP32 principal con datos innecesarios.

Conclusiones personales
Con este proyecto me di cuenta de que la Inteligencia Artificial no es magia, sino un proceso que requiere mucha sincronización. Por un lado, aprendí muchísimo sobre visión computacional y cómo programar una ESP32-CAM para que funcione como un "ojo" independiente. Pero lo más valioso fue aprender a integrar software avanzado (Python y OpenCV) con hardware (el chaleco).

Entendí que de nada sirve tener un código de IA súper inteligente si no se comunica bien y a tiempo con la Máquina de Estados del dispositivo físico. Mi aportación fue clave para darle "visión y cerebro" al sistema VestaGuard, permitiendo que no sea solo un chaleco que vibra o suena, sino un dispositivo inteligente capaz de reaccionar a su entorno en tiempo real.
