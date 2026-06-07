# Analisis individual - Reyes Gutierrez Pablo Alberto (23240055)

**Proyecto:** VestaGuard  
**Integrante:** Reyes Gutierrez Pablo Alberto  
**Codigo:** 23240055  
**Responsabilidad principal:** Conexiones fisicas, ensamblaje del chaleco, cableado de sensores y actuadores, y verificacion de la integracion mecanica del sistema.

## Problemas encontrados

1. La alimentacion del sistema podia volverse inestable cuando los motores vibradores y el relevador trabajaban al mismo tiempo.
2. Algunos actuadores no debian conectarse directo a los GPIO del ESP32 porque podian dañar la placa.
3. El boton de panico podia generar falsos disparos por ruido en los cables y por rebote mecanico.
4. El montaje del chaleco necesitaba quedar firme, pero sin volver el sistema imposible de revisar o reparar.
5. La ESP32-CAM no debia mezclarse con el cableado principal del chaleco, porque su funcion es solo como nodo de vision independiente.

## Soluciones aplicadas

1. Se organizó la alimentación usando una PowerBank de doble puerto USB. Un puerto alimenta al ESP32 principal y su etapa de potencia de motores, mientras que el otro puerto alimenta de forma aislada a la ESP32-CAM. Todo se unificó con una tierra común sólida para evitar caídas de voltaje.
2. Los motores vibradores se dejaron con etapa de conmutacion por transistor, resistencia de base y diodo de proteccion, en lugar de conectarlos directo al ESP32.
3. El boton de panico se documento con filtro anti-rebote y pull-up externo para evitar lecturas falsas.
4. Se propuso un montaje mixto: soldar la parte critica de potencia y fijar modulos como ESP32, TP4056, GPS y ESP32-CAM con tornillos, separadores o conectores donde conviene mantenimiento.
5. Se separo la ESP32-CAM como nodo independiente de vision para no cargar la estructura electrica del chaleco.

## Conclusiones personales

La parte fisica del proyecto es tan importante como el codigo, porque si la alimentacion, la tierra comun o la etapa de potencia estan mal hechas, la IA y la comunicacion MQTT no sirven en una demostracion real. En este trabajo entendi que un sistema wearable necesita montaje robusto, cableado ordenado y proteccion electrica para que los sensores y actuadores respondan de forma confiable.

Tambien aprendi que el proyecto debe mantenerse modular: el ESP32 principal controla la logica del chaleco, la ESP32-CAM aporta la evidencia visual y la laptop procesa la IA. Esa separacion hace mas facil revisar, mantener y demostrar el sistema sin mezclar todo en una sola placa.

Mi aporte quedo centrado en asegurar que el chaleco pueda funcionar fisicamente de forma segura, estable y reparable, que es la base para que la parte de IA y MQTT tenga sentido en la entrega final.
