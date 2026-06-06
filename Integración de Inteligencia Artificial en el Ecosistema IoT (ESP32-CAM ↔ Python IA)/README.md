# Avance de IA para ESP32-CAM y Servidor Python

<!-- RESPONSABLE PRINCIPAL: Rangel Hernandez Aldo. Estefania revisa la captura de imagen y Pablo revisa la integracion fisica y documental. -->
<!-- SE CARGA EN: ESP32-CAM con OV3660 para captura, laptop para servidor Python, y ESP32 principal para recibir comandos por MQTT. -->

OBJETIVO: Integrar un servidor Python con IA que reciba imagenes y telemetria desde la ESP32-CAM por MQTT, tome una decision y responda con comandos inmediatos hacia los actuadores del proyecto.
INTEGRANTES: Alvarez Guevara Estefania Guadalupe (23240077), Rangel Hernandez Aldo (23240272), Reyes Gutierrez Pablo Alberto (23240055)
PROYECTO: VestaGuard

Este avance corresponde al entregable E3 de la unidad 4: pipeline de IA con ESP32-CAM, MQTT y servidor Python externo. Firebase e interfaz gráfica no forman parte de esta carpeta; se reservan para el entregable siguiente.

Esta carpeta documenta solo el material oficial de entrega. Las pruebas, duplicados de presentación y archivos de respaldo no se consideran parte de la carga oficial del dispositivo.

## 1. Proposito del avance

Este avance se integra directamente al proyecto del chaleco inteligente. La idea no es crear una actividad aislada, sino agregar una capa de inteligencia al mismo sistema que ya trae la HAL, MQTT y la lógica de sensores. La ESP32-CAM actua como sensor crítico de evidencia visual y el servidor Python funciona como cerebro de decisión.

En términos de arquitectura, este bloque cumple con la consigna de la materia:

Sensor o cámara ESP32 -> MQTT -> Servidor Python con IA -> MQTT -> Actuador ESP32

## 2. Como encaja con el proyecto

El chaleco ya resuelve la detección local con sensores de proximidad, movimiento e inclinación. Esta actividad agrega la parte visual para que el sistema no dependa solo del PIR, ultrasonido o MPU6050.

La forma correcta de integrarlo es esta:

- El ESP32 principal del chaleco sigue siendo la base de sensores y actuadores.
- La ESP32-CAM funciona como un nodo externo de visión, sin compartir pines ni carga eléctrica con la HAL.
- El servidor Python recibe la imagen por MQTT, decide con IA y regresa el comando al chaleco.
- El chaleco recibe el comando y activa vibración, LED o relevador según su lógica local.

Con esto, la práctica queda alineada con el proyecto sin mezclar el control físico con la inferencia visual.

La ESP32-CAM no funciona como simple visualizador. Su rol es funcional y necesario porque aporta el frame que alimenta la decision del servidor. Eso permite justificar la actividad frente a la rúbrica.

## 3. Requisitos tecnicos cubiertos

Este avance cubre los puntos que pide la actividad:

- Validación previa con datos estáticos.
- Pipeline completo en tiempo real.
- Uso de librería profesional de IA y visión por computadora.
- Rol crítico de la ESP32-CAM.
- Código con encabezado obligatorio.
- Documentación de precisión aproximada y tipo de predicción.
- Evidencia lista para subir al repositorio del proyecto.

Además, la ESP32-CAM se trabaja con firmware custom compatible con cámara, porque el firmware oficial de MicroPython no incluye ese soporte. La guía de conexión y flasheo de la maestra se usa como base para montar la placa con FTDI, GPIO0 a GND durante la programación y 5V en la alimentación.

## 5. Flujo de funcionamiento

1. La ESP32-CAM recibe la orden `vestaguard/camara/disparar`.
2. Captura un frame JPEG y lo publica en `vestaguard/camara/frame`.
3. El servidor Python recibe el mensaje y decodifica `imagen_b64`.
4. OpenCV analiza la imagen y, si existe, se carga un modelo desde `modelo/modelo_vestaguard.joblib`.
5. El servidor publica la decision en `vestaguard/ia/resultado`.
6. El comando final se publica en `vestaguard/ia/comando` para que la ESP32 principal active vibracion, LED o relevador.

## 6. Formato del payload de camara

La ESP32-CAM publica un JSON con esta estructura:

```json
{
	"imagen_b64": "...",
	"formato": "jpeg",
	"ancho": 320,
	"alto": 240,
	"evento": "solicitud_remota",
	"origen": "esp32cam"
}
```

Para el servidor, la clave esencial es `imagen_b64`. Los demás campos ayudan a documentar la prueba y a explicar el funcionamiento del sistema.

## 7. Validacion estatica antes de MQTT

Primero se prueba la IA con imagenes locales. Esto permite demostrar que el modelo o la heurística funciona antes de conectar la red.

```bash
python validacion_estatica.py --entrada muestras
```

La salida muestra:

- clasificacion
- confianza
- accion sugerida
- fuente de la decision

## 8. Requisitos del backend

- Python 3.10 o superior.
- `paho-mqtt` para la comunicacion con Mosquitto.
- `opencv-python` para lectura y analisis de imagenes.
- `numpy` para procesamiento matricial.
- `scikit-learn` y `joblib` si se desea entrenar y cargar un modelo local.

## 9. Relacion con el chaleco

- La HAL sigue controlando sensores y actuadores locales del chaleco.
- La ESP32-CAM añade una capa de evidencia visual.
- Python IA decide si la imagen representa normalidad, vigilancia o amenaza.
- MQTT conecta todo sin mover la lógica de hardware al servidor.

Conviene aclarar en clase que esta carpeta resuelve la parte de IA y visión del entregable E3; el almacenamiento histórico en Firebase y el dashboard se abordan después, según la secuencia de la unidad 4.
