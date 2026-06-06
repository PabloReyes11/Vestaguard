# Resumen general de la práctica MQTT

Este resumen está pensado para explicar la práctica de MQTT de manera general, sin depender de un proyecto específico. La idea es que sirva como guía para cualquier compañero que tenga sensores y actuadores diferentes, pero que deba seguir la misma lógica de comunicación, la misma estructura de archivos y el mismo criterio de integración entre hardware, HAL, servidor Python y aplicación móvil.

## Qué se hizo en la práctica

La actividad consistió en construir una comunicación real entre una ESP32, una laptop y una aplicación móvil usando el protocolo MQTT. La práctica no se centró solo en “hacer funcionar” un componente, sino en entender cómo se distribuye la información en un sistema embebido: qué dispositivo publica datos, cuál los recibe, cómo se controlan los actuadores y cómo se organiza todo para que el sistema sea fácil de leer, de mantener y de ampliar.

De forma general, la ESP32 se encarga de leer sensores y activar salidas físicas. La laptop corre un servidor en Python que recibe la telemetría con hora y fecha, y que también puede mandar comandos de regreso. La aplicación móvil funciona como interfaz de control para probar y visualizar el sistema sin depender únicamente de la consola.

## Idea principal de la arquitectura

La práctica se entiende mejor si se divide en tres capas. La primera es el hardware físico, donde están conectados los sensores y actuadores. La segunda es la HAL, que encapsula el acceso a esos componentes para que no se manipulen directamente desde la red. La tercera es la capa MQTT, que se encarga de mover los mensajes entre la ESP32, la laptop y el celular por medio del broker Mosquitto.

Esta organización es importante porque evita mezclar funciones. Si el hardware cambia, solo se ajusta la HAL. Si cambian los canales de comunicación, se modifica la parte MQTT. Si cambia la interfaz de monitoreo, se adapta el servidor o la aplicación. Esa separación hace que la práctica tenga orden y que el trabajo sea más fácil de corregir cuando aparece un fallo.

## Función de la HAL

La HAL es la capa que traduce el hardware físico a funciones simples. En lugar de pensar en pines, registros, PWM o lectura de buses, el resto del programa llama métodos como leer un sensor, activar una salida o apagar un actuador. Con eso se evita que la lógica de red tenga que saber cómo está cableado cada componente.

Para cualquier otro equipo, esta es la parte que más se debe adaptar. Si usan temperatura, humedad, luz, distancia, movimiento o un motor, esos elementos deben definirse ahí. La HAL también es la que permite hacer pruebas aisladas del hardware sin pasar primero por MQTT, lo cual ayuda mucho cuando se busca localizar un error físico.

## Función de la parte MQTT

La capa MQTT es la que hace posible que los mensajes viajen entre dispositivos distintos sin que estos estén conectados de forma directa. La ESP32 puede publicar telemetría, mientras que la laptop o la app móvil pueden enviar comandos a tópicos específicos. Todo eso se organiza mediante un broker, que actúa como intermediario.

La idea de usar MQTT en la práctica es demostrar que un sistema puede ser distribuido y ordenado. Un dispositivo no necesita saber quién recibe el mensaje, solo necesita publicar o suscribirse al tópico correcto. Eso hace que la comunicación sea clara y que cada parte del proyecto tenga un rol definido.

## Qué hace el servidor en Python

El servidor en Python cumple dos tareas. Primero, recibe la información que publica la ESP32 y le agrega un timestamp para registrar exactamente cuándo llegó cada mensaje. Segundo, puede enviar comandos de control para activar o desactivar actuadores. Eso permite ver el sistema desde la computadora y usarla como punto central de monitoreo.

Este script también es útil porque demuestra que MQTT no es solo “mandar datos”, sino coordinar un flujo de información en ambos sentidos. Además, ayuda a comprobar que el broker está funcionando, que la red está bien configurada y que los tópicos se están usando correctamente.

## Qué papel tiene la aplicación móvil

La aplicación móvil se usa como una interfaz práctica para controlar el sistema desde el celular. Sirve para mandar comandos, ver estados y validar que el mensaje llegue al hardware físico. No sustituye al servidor de Python, pero sí complementa la prueba porque deja ver que la comunicación funciona también desde otro dispositivo.

En una práctica como esta, la app es muy útil porque hace más visible el control remoto. En lugar de escribir solo en la terminal, se pueden usar botones o interruptores que manden mensajes MQTT directamente. Eso facilita la demostración en clase y hace más fácil verificar que la red está respondiendo bien.

## Qué se revisó durante la práctica

Durante el desarrollo aparecieron problemas de tres tipos: de software, de red y de hardware. En el software, hubo que corregir la instalación de librerías en la laptop y ajustar el entorno virtual para que el servidor Python funcionara. En la ESP32, se tuvo que revisar el identificador MQTT y la lectura de algunos sensores, porque pequeños detalles de formato o dependencia podían romper la conexión.

En la parte física, el problema más común fue el cableado. Se revisaron conexiones de sensores, actuadores, tierra, alimentación y etapas de potencia. Cuando un componente no respondía, se hicieron pruebas aisladas para confirmar si el error era del código o del montaje. Esa forma de trabajo fue clave para no confundir un fallo de hardware con uno de red.

## Qué se aprende con este tipo de práctica

La práctica enseña que un sistema IoT no se corrige solo con cambiar código. Primero hay que entender el flujo completo: sensor, HAL, MQTT, servidor, aplicación y actuador. Si una capa falla, se debe revisar antes de seguir modificando las demás. Ese criterio ayuda a depurar mejor y a trabajar con más orden.

También se aprende que la documentación importa tanto como la programación. Tener claros los tópicos, los pines, la función de cada archivo y la lógica de los mensajes hace que cualquier compañero pueda tomar el proyecto y adaptarlo a sus propios componentes sin perder la estructura general.

## Cierre

En resumen, la práctica de MQTT sirve para entender cómo se conecta un sistema físico con un servidor y con una app móvil usando una arquitectura organizada. La ESP32 publica y recibe mensajes, la HAL protege el acceso al hardware, la laptop registra y controla la información, y la aplicación móvil sirve como panel de mando. El resultado no es solo que funcione, sino que quede bien estructurado para que otro equipo pueda usar la misma lógica con un proyecto distinto.