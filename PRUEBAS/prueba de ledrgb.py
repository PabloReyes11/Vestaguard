from machine import Pin, PWM
import time

# Configuración de pines PWM según tu diagrama
led_r = PWM(Pin(13), freq=1000, duty=0)
led_g = PWM(Pin(14), freq=1000, duty=0)
led_b = PWM(Pin(33), freq=1000, duty=0)

def color(r, g, b):
    # Convierte escala 0-255 a ciclo de trabajo 0-1023
    led_r.duty(int((r / 255) * 1023))
    led_g.duty(int((g / 255) * 1023))
    led_b.duty(int((b / 255) * 1023))

print("Iniciando prueba de LED RGB...")

try:
    while True:
        print("Color: ROJO")
        color(255, 0, 0)
        time.sleep(1)
        
        print("Color: VERDE")
        color(0, 255, 0)
        time.sleep(1)
        
        print("Color: AZUL")
        color(0, 0, 255)
        time.sleep(1)
        
        print("Color: APAGADO")
        color(0, 0, 0)
        time.sleep(1)
        
except KeyboardInterrupt:
    color(0, 0, 0)
    print("Prueba finalizada.")