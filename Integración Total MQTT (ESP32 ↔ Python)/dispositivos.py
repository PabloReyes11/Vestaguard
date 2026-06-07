import math
import time
try:
    from micropython import const
except ImportError:

    def const(valor):
        return valor
try:
    import machine
except ImportError:
    machine = None
PIN_TRIGGER_ULTRASONICO_DEF = const(5)
PIN_ECHO_ULTRASONICO_DEF = const(18)
PIN_PIR_DEF = const(19)
PIN_BOTON_PANICO_DEF = const(32)
PIN_SDA_MPU6050_DEF = const(21)
PIN_SCL_MPU6050_DEF = const(22)
PIN_TX_GPS_DEF = const(16)
PIN_RX_GPS_DEF = const(17)
BAUDRATE_GPS_DEF = const(9600)
PIN_VIBRADOR_HOMBRO_IZQ_DEF = const(25)
PIN_VIBRADOR_HOMBRO_DER_DEF = const(27)
PIN_VIBRADOR_DEF = PIN_VIBRADOR_HOMBRO_IZQ_DEF
PIN_BUZZER_DEF = const(26)
PIN_RELEVADOR_DEF = const(23)
PIN_LED_R_DEF = const(13)
PIN_LED_G_DEF = const(14)
PIN_LED_B_DEF = const(33)
PINES_FLASH_SPI = (6, 7, 8, 9, 10, 11)
PINES_REPL_SERIE = (1, 3)
PINES_SOLO_ENTRADA = (34, 35, 36, 37, 38, 39)
PINES_PWM_SEGUROS = (4, 13, 14, 25, 26, 27, 32, 33)
DIRECCION_MPU6050 = const(104)
REGISTRO_PWR_MGMT_1 = const(107)
REGISTRO_ACCEL_XOUT_H = const(59)
LONGITUD_BLOQUE_ACCEL = const(6)
ESCALA_ACELEROMETRO_LSB_G = const(16384)
ESCALA_MILIG = const(1000)
EMA_ESCALA_MIL = const(1000)
EMA_ALPHA_JOYSTICK_MIL_DEF = const(180)
TIMEOUT_ULTRASONICO_US = const(30000)
INTERVALO_REINTENTO_MPU_MS = const(2000)
CALIBRACION_PIR_MS_DEF = const(30000)

def tiempo_ms_actual():
    try:
        return time.ticks_ms()
    except AttributeError:
        return int(time.time() * 1000)

def diferencia_tiempo_ms(actual_ms, anterior_ms):
    try:
        return time.ticks_diff(actual_ms, anterior_ms)
    except AttributeError:
        return actual_ms - anterior_ms

def sumar_tiempo_ms(base_ms, incremento_ms):
    try:
        return time.ticks_add(base_ms, int(incremento_ms))
    except AttributeError:
        return int(base_ms) + int(incremento_ms)

def esperar_ms(duracion_ms):
    try:
        time.sleep_ms(int(duracion_ms))
    except AttributeError:
        time.sleep(float(duracion_ms) / 1000.0)

def validar_pin_entrada(pin, nombre_pin, requiere_pullup=False):
    if pin in PINES_FLASH_SPI:
        raise ValueError(nombre_pin + ' usa GPIO reservado para memoria FLASH SPI')
    if pin in PINES_REPL_SERIE:
        raise ValueError(nombre_pin + ' usa GPIO de consola serie (TX/RX)')
    if requiere_pullup and pin in PINES_SOLO_ENTRADA:
        raise ValueError(nombre_pin + ' no soporta pull-up interno en ese GPIO')

def validar_pin_salida(pin, nombre_pin):
    if pin in PINES_FLASH_SPI:
        raise ValueError(nombre_pin + ' usa GPIO reservado para memoria FLASH SPI')
    if pin in PINES_REPL_SERIE:
        raise ValueError(nombre_pin + ' usa GPIO de consola serie (TX/RX)')
    if pin in PINES_SOLO_ENTRADA:
        raise ValueError(nombre_pin + ' esta en bloque solo-entrada (34-39)')

def validar_pin_pwm_seguro(pin, nombre_pin):
    validar_pin_salida(pin, nombre_pin)
    if pin not in PINES_PWM_SEGUROS:
        raise ValueError(nombre_pin + ' no pertenece al bloque seguro PWM recomendado')

class PinSimulado:

    def __init__(self, valor_inicial=0):
        self._valor = int(valor_inicial)

    def value(self, nuevo_valor=None):
        if nuevo_valor is None:
            return self._valor
        self._valor = int(nuevo_valor)
        return self._valor

class PwmSimulado:

    def __init__(self):
        self.frecuencia_hz = 0
        self.duty_valor = 0

    def freq(self, frecuencia_hz):
        self.frecuencia_hz = int(frecuencia_hz)

    def duty(self, duty_valor):
        self.duty_valor = int(duty_valor)

    def duty_u16(self, duty_valor):
        self.duty_valor = int(duty_valor)

    def deinit(self):
        self.frecuencia_hz = 0
        self.duty_valor = 0

class CajaSensores:

    def __init__(self, configuracion=None):
        configuracion_base = {'pin_trigger_ultrasonico': PIN_TRIGGER_ULTRASONICO_DEF, 'pin_echo_ultrasonico': PIN_ECHO_ULTRASONICO_DEF, 'pin_pir': PIN_PIR_DEF, 'pin_boton_panico': PIN_BOTON_PANICO_DEF, 'pin_sda_mpu6050': PIN_SDA_MPU6050_DEF, 'pin_scl_mpu6050': PIN_SCL_MPU6050_DEF, 'habilitar_gps': True, 'pin_tx_gps': PIN_TX_GPS_DEF, 'pin_rx_gps': PIN_RX_GPS_DEF, 'baudrate_gps': BAUDRATE_GPS_DEF, 'habilitar_joystick_x': False, 'pin_adc_joystick_x': 34, 'alpha_ema_joystick_mil': EMA_ALPHA_JOYSTICK_MIL_DEF, 'calibracion_pir_ms': CALIBRACION_PIR_MS_DEF, 'tamano_promedio_distancia': 5, 'tamano_promedio_inclinacion': 5, 'tamano_filtro_movimiento': 5, 'umbral_caida_g': 2.2, 'umbral_inclinacion_grados': 55.0}
        if configuracion:
            configuracion_base.update(configuracion)
        self.configuracion = configuracion_base
        self.modo_simulacion = machine is None
        self._validar_configuracion_pines()
        self.historial_distancia = []
        self.historial_inclinacion = []
        self.historial_movimiento = []
        self._contador_simulacion = 0
        self._ultima_aceleracion_total_g = 1.0
        self._flag_panico_irq = False
        self._flag_movimiento_irq = False
        self._pir_calibrado = self.modo_simulacion
        self._lectura_ema_joystick_x = None
        self._buffer_mpu6050 = bytearray(LONGITUD_BLOQUE_ACCEL)
        self._ultimo_reintento_mpu_ms = 0
        self._conteo_errores_i2c = 0
        self._uart_gps = None
        self.gps_disponible = False
        self._ultimo_gps_valido = {'latitud': None, 'longitud': None, 'altitud_m': None, 'satelites': None, 'fijado': False}
        self.pin_trigger = None
        self.pin_echo = None
        self.pin_pir = None
        self.pin_boton_panico = None
        self.adc_joystick_x = None
        self.i2c_mpu6050 = None
        self.mpu6050_disponible = False
        if self.modo_simulacion:
            self.pin_trigger = PinSimulado(0)
            self.pin_echo = PinSimulado(0)
            self.pin_pir = PinSimulado(0)
            self.pin_boton_panico = PinSimulado(1)
        else:
            self._inicializar_hardware_real()
            self._inicializar_adc_joystick()

    def _validar_configuracion_pines(self):
        validar_pin_salida(self.configuracion['pin_trigger_ultrasonico'], 'pin_trigger_ultrasonico')
        validar_pin_entrada(self.configuracion['pin_echo_ultrasonico'], 'pin_echo_ultrasonico')
        validar_pin_entrada(self.configuracion['pin_pir'], 'pin_pir')
        validar_pin_entrada(self.configuracion['pin_boton_panico'], 'pin_boton_panico', requiere_pullup=True)
        validar_pin_salida(self.configuracion['pin_sda_mpu6050'], 'pin_sda_mpu6050')
        validar_pin_salida(self.configuracion['pin_scl_mpu6050'], 'pin_scl_mpu6050')
        if bool(self.configuracion.get('habilitar_gps', True)):
            validar_pin_salida(self.configuracion['pin_tx_gps'], 'pin_tx_gps')
            validar_pin_entrada(self.configuracion['pin_rx_gps'], 'pin_rx_gps')
        if bool(self.configuracion.get('habilitar_joystick_x', False)):
            validar_pin_entrada(self.configuracion['pin_adc_joystick_x'], 'pin_adc_joystick_x')
        pines_usados = {}
        for nombre, valor in self.configuracion.items():
            if not nombre.startswith('pin_'):
                continue
            if nombre == 'pin_adc_joystick_x' and (not bool(self.configuracion.get('habilitar_joystick_x', False))):
                continue
            if valor in pines_usados:
                raise ValueError('Conflicto de GPIO: ' + nombre + ' comparte pin con ' + pines_usados[valor])
            pines_usados[valor] = nombre

    def _inicializar_hardware_real(self):
        self.pin_trigger = machine.Pin(self.configuracion['pin_trigger_ultrasonico'], machine.Pin.OUT)
        self.pin_echo = machine.Pin(self.configuracion['pin_echo_ultrasonico'], machine.Pin.IN)
        self.pin_pir = machine.Pin(self.configuracion['pin_pir'], machine.Pin.IN)
        self.pin_boton_panico = machine.Pin(self.configuracion['pin_boton_panico'], machine.Pin.IN, machine.Pin.PULL_UP)
        self.pin_trigger.value(0)
        esperar_ms(2)
        self._configurar_irq_panico()
        self._configurar_irq_pir()
        self._calibrar_pir_bloqueante()
        self._inicializar_mpu6050()
        self._inicializar_gps()

    def _callback_irq_panico(self, _pin):
        self._flag_panico_irq = True

    def _configurar_irq_panico(self):
        try:
            self.pin_boton_panico.irq(trigger=machine.Pin.IRQ_FALLING, handler=self._callback_irq_panico)
        except Exception:
            pass

    def _callback_irq_pir(self, _pin):
        self._flag_movimiento_irq = True

    def _configurar_irq_pir(self):
        try:
            self.pin_pir.irq(trigger=machine.Pin.IRQ_RISING, handler=self._callback_irq_pir)
        except Exception:
            pass

    def _calibrar_pir_bloqueante(self):
        if self.modo_simulacion:
            self._pir_calibrado = True
            return
        tiempo_calibracion_ms = int(self.configuracion.get('calibracion_pir_ms', CALIBRACION_PIR_MS_DEF))
        if tiempo_calibracion_ms > 0:
            esperar_ms(tiempo_calibracion_ms)
        self._pir_calibrado = True

    def _inicializar_adc_joystick(self):
        if not bool(self.configuracion.get('habilitar_joystick_x', False)):
            self.adc_joystick_x = None
            return
        try:
            self.adc_joystick_x = machine.ADC(machine.Pin(self.configuracion['pin_adc_joystick_x']))
            try:
                self.adc_joystick_x.atten(machine.ADC.ATTN_11DB)
            except Exception:
                pass
        except Exception:
            self.adc_joystick_x = None

    def _inicializar_mpu6050(self):
        try:
            self.i2c_mpu6050 = machine.I2C(0, scl=machine.Pin(self.configuracion['pin_scl_mpu6050']), sda=machine.Pin(self.configuracion['pin_sda_mpu6050']), freq=400000)
        except Exception:
            try:
                self.i2c_mpu6050 = machine.SoftI2C(scl=machine.Pin(self.configuracion['pin_scl_mpu6050']), sda=machine.Pin(self.configuracion['pin_sda_mpu6050']), freq=400000)
            except Exception:
                self.i2c_mpu6050 = None
        if self.i2c_mpu6050 is None:
            self.mpu6050_disponible = False
            return
        try:
            self.i2c_mpu6050.writeto_mem(DIRECCION_MPU6050, REGISTRO_PWR_MGMT_1, b'\x00')
            self.mpu6050_disponible = True
            self._conteo_errores_i2c = 0
        except OSError:
            self._conteo_errores_i2c += 1
            self.mpu6050_disponible = False
        except Exception:
            self.mpu6050_disponible = False

    def _inicializar_gps(self):
        if not bool(self.configuracion.get('habilitar_gps', True)):
            self._uart_gps = None
            self.gps_disponible = False
            return
        if self.modo_simulacion:
            self._uart_gps = None
            self.gps_disponible = True
            self._ultimo_gps_valido = {'latitud': 21.123456, 'longitud': -101.678901, 'altitud_m': 1810.0, 'satelites': 8, 'fijado': True}
            return
        try:
            self._uart_gps = machine.UART(2, baudrate=int(self.configuracion.get('baudrate_gps', BAUDRATE_GPS_DEF)), tx=machine.Pin(self.configuracion['pin_tx_gps']), rx=machine.Pin(self.configuracion['pin_rx_gps']), timeout=0, rxbuf=256)
            self.gps_disponible = True
        except Exception:
            self._uart_gps = None
            self.gps_disponible = False

    def _convertir_grados_nmea_a_decimal(self, valor, hemisferio):
        try:
            if not valor:
                return None
            numero = float(valor)
            grados = int(numero // 100)
            minutos = numero - grados * 100
            coordenada = grados + minutos / 60.0
            if hemisferio in ('S', 'W'):
                coordenada = -coordenada
            return round(coordenada, 6)
        except Exception:
            return None

    def _procesar_trama_gps(self, trama):
        if not trama:
            return None
        if isinstance(trama, bytes):
            try:
                trama = trama.decode('utf-8', 'ignore')
            except Exception:
                return None
        trama = trama.strip()
        if not trama.startswith('$'):
            return None
        partes = trama.split(',')
        cabecera = partes[0]
        if cabecera in ('$GPRMC', '$GNRMC') and len(partes) >= 7:
            estado = partes[2] if len(partes) > 2 else 'V'
            if estado != 'A':
                return None
            latitud = self._convertir_grados_nmea_a_decimal(partes[3], partes[4] if len(partes) > 4 else '')
            longitud = self._convertir_grados_nmea_a_decimal(partes[5], partes[6] if len(partes) > 6 else '')
            if latitud is None or longitud is None:
                return None
            return {'latitud': latitud, 'longitud': longitud, 'altitud_m': self._ultimo_gps_valido.get('altitud_m'), 'satelites': self._ultimo_gps_valido.get('satelites'), 'fijado': True}
        if cabecera in ('$GPGGA', '$GNGGA') and len(partes) >= 10:
            calidad_fijado = partes[6] if len(partes) > 6 else '0'
            latitud = self._convertir_grados_nmea_a_decimal(partes[2], partes[3] if len(partes) > 3 else '')
            longitud = self._convertir_grados_nmea_a_decimal(partes[4], partes[5] if len(partes) > 5 else '')
            if latitud is None or longitud is None:
                return None
            satelites = None
            altitud = None
            try:
                satelites = int(partes[7]) if partes[7] else None
            except Exception:
                satelites = None
            try:
                altitud = float(partes[9]) if partes[9] else None
            except Exception:
                altitud = None
            return {'latitud': latitud, 'longitud': longitud, 'altitud_m': altitud, 'satelites': satelites, 'fijado': calidad_fijado not in ('0', '', None)}
        return None

    def obtener_posicion_gps(self):
        if not bool(self.configuracion.get('habilitar_gps', True)):
            return None
        if self.modo_simulacion:
            return dict(self._ultimo_gps_valido)
        if self._uart_gps is None:
            if self._ultimo_gps_valido.get('fijado'):
                return dict(self._ultimo_gps_valido)
            return None
        try:
            if self._uart_gps.any() > 0:
                lectura = self._uart_gps.readline()
                if lectura:
                    posicion = self._procesar_trama_gps(lectura)
                    if posicion is not None:
                        self._ultimo_gps_valido = posicion
                        return dict(posicion)
        except Exception:
            pass
        if self._ultimo_gps_valido.get('fijado'):
            return dict(self._ultimo_gps_valido)
        return None

    def _reintentar_mpu6050(self):
        ahora = tiempo_ms_actual()
        if diferencia_tiempo_ms(ahora, self._ultimo_reintento_mpu_ms) < INTERVALO_REINTENTO_MPU_MS:
            return
        self._ultimo_reintento_mpu_ms = ahora
        self._inicializar_mpu6050()

    def _agregar_historial(self, historial, valor, tamano_maximo):
        historial.append(valor)
        while len(historial) > tamano_maximo:
            historial.pop(0)
        return historial

    def _promedio(self, historial):
        if not historial:
            return None
        return sum(historial) / len(historial)

    def _leer_distancia_cruda_cm(self):
        if self.modo_simulacion:
            self._contador_simulacion += 1
            fase = self._contador_simulacion % 36
            if fase < 10:
                return 170
            if fase < 20:
                return 110
            if fase < 28:
                return 78
            return 150
        try:
            self.pin_trigger.value(0)
            time.sleep_us(2)
            self.pin_trigger.value(1)
            time.sleep_us(10)
            self.pin_trigger.value(0)
            duracion_us = machine.time_pulse_us(self.pin_echo, 1, TIMEOUT_ULTRASONICO_US)
            if duracion_us < 0:
                return None
            return duracion_us // 58
        except OSError:
            return None
        except Exception:
            return None

    def obtener_proximidad_cm(self):
        lectura_cruda = self._leer_distancia_cruda_cm()
        if lectura_cruda is None:
            return self._promedio(self.historial_distancia)
        self._agregar_historial(self.historial_distancia, lectura_cruda, self.configuracion['tamano_promedio_distancia'])
        promedio = self._promedio(self.historial_distancia)
        if promedio is None:
            return None
        return round(promedio, 2)

    def detectar_movimiento_pir(self):
        if not self._pir_calibrado:
            return False
        if self.modo_simulacion:
            fase = self._contador_simulacion % 12
            lectura = 1 if fase >= 4 else 0
        elif self._flag_movimiento_irq:
            self._flag_movimiento_irq = False
            lectura = 1
        else:
            try:
                lectura = int(self.pin_pir.value())
            except Exception:
                lectura = 0
        self._agregar_historial(self.historial_movimiento, lectura, self.configuracion['tamano_filtro_movimiento'])
        activos = sum(self.historial_movimiento)
        return activos >= len(self.historial_movimiento) // 2 + 1

    def _complemento_a_dos(self, valor_16_bits):
        if valor_16_bits & 32768:
            return -(65535 - valor_16_bits + 1)
        return valor_16_bits

    def _leer_aceleracion_g(self):
        if self.modo_simulacion:
            fase = self._contador_simulacion % 20
            ax_mg = fase * 10 // 2
            ay_mg = 200
            az_mg = 1000
            return (ax_mg, ay_mg, az_mg)
        if not self.mpu6050_disponible:
            return None
        try:
            try:
                self.i2c_mpu6050.readfrom_mem_into(DIRECCION_MPU6050, REGISTRO_ACCEL_XOUT_H, self._buffer_mpu6050)
            except AttributeError:
                datos = self.i2c_mpu6050.readfrom_mem(DIRECCION_MPU6050, REGISTRO_ACCEL_XOUT_H, LONGITUD_BLOQUE_ACCEL)
                self._buffer_mpu6050[0:LONGITUD_BLOQUE_ACCEL] = datos
            ax = self._complemento_a_dos(self._buffer_mpu6050[0] << 8 | self._buffer_mpu6050[1])
            ay = self._complemento_a_dos(self._buffer_mpu6050[2] << 8 | self._buffer_mpu6050[3])
            az = self._complemento_a_dos(self._buffer_mpu6050[4] << 8 | self._buffer_mpu6050[5])
            ax_mg = ax * ESCALA_MILIG // ESCALA_ACELEROMETRO_LSB_G
            ay_mg = ay * ESCALA_MILIG // ESCALA_ACELEROMETRO_LSB_G
            az_mg = az * ESCALA_MILIG // ESCALA_ACELEROMETRO_LSB_G
            return (ax_mg, ay_mg, az_mg)
        except OSError:
            self._conteo_errores_i2c += 1
            self._reintentar_mpu6050()
            return None
        except Exception:
            return None

    def obtener_inclinacion_grados(self):
        lectura = self._leer_aceleracion_g()
        if lectura is None:
            return self._promedio(self.historial_inclinacion)
        ax_mg, ay_mg, az_mg = lectura
        magnitud_mg = math.sqrt(ax_mg * ax_mg + ay_mg * ay_mg + az_mg * az_mg)
        self._ultima_aceleracion_total_g = magnitud_mg / float(ESCALA_MILIG)
        denominador = math.sqrt(ay_mg * ay_mg + az_mg * az_mg)
        if denominador == 0:
            denominador = 0.0001
        inclinacion = abs(math.degrees(math.atan(ax_mg / denominador)))
        self._agregar_historial(self.historial_inclinacion, inclinacion, self.configuracion['tamano_promedio_inclinacion'])
        promedio = self._promedio(self.historial_inclinacion)
        if promedio is None:
            return None
        return round(promedio, 2)

    def detectar_caida(self, inclinacion_actual=None):
        if inclinacion_actual is None:
            inclinacion_actual = self.obtener_inclinacion_grados()
        if inclinacion_actual is None:
            return False
        umbral_g = float(self.configuracion['umbral_caida_g'])
        umbral_ang = float(self.configuracion['umbral_inclinacion_grados'])
        return self._ultima_aceleracion_total_g >= umbral_g or inclinacion_actual >= umbral_ang

    def obtener_boton_panico(self):
        if self._flag_panico_irq:
            self._flag_panico_irq = False
            return True
        if self.modo_simulacion:
            return False
        try:
            return self.pin_boton_panico.value() == 0
        except Exception:
            return False

    def obtener_angulo_joystick_x(self):
        if self.modo_simulacion:
            return None
        if self.adc_joystick_x is None:
            return None
        try:
            lectura_adc = int(self.adc_joystick_x.read())
        except OSError:
            return None
        except Exception:
            return None
        if lectura_adc < 0:
            lectura_adc = 0
        if lectura_adc > 4095:
            lectura_adc = 4095
        alpha_mil = int(self.configuracion.get('alpha_ema_joystick_mil', EMA_ALPHA_JOYSTICK_MIL_DEF))
        if alpha_mil < 0:
            alpha_mil = 0
        if alpha_mil > EMA_ESCALA_MIL:
            alpha_mil = EMA_ESCALA_MIL
        if self._lectura_ema_joystick_x is None:
            self._lectura_ema_joystick_x = lectura_adc
        else:
            self._lectura_ema_joystick_x = (alpha_mil * lectura_adc + (EMA_ESCALA_MIL - alpha_mil) * self._lectura_ema_joystick_x) // EMA_ESCALA_MIL
        return self._lectura_ema_joystick_x * 180 // 4095

    def obtener_resumen_sensores(self):
        proximidad_cm = self.obtener_proximidad_cm()
        movimiento_pir = self.detectar_movimiento_pir()
        inclinacion_grados = self.obtener_inclinacion_grados()
        caida_detectada = self.detectar_caida(inclinacion_grados)
        boton_panico = self.obtener_boton_panico()
        angulo_joystick_x = self.obtener_angulo_joystick_x()
        posicion_gps = self.obtener_posicion_gps()
        accel = self._leer_aceleracion_g()
        aceleracion_y = accel[1] / 1000.0 if accel else None
        if posicion_gps is None:
            gps_latitud = None
            gps_longitud = None
            gps_altitud_m = None
            gps_satelites = None
            gps_fijado = False
        else:
            gps_latitud = posicion_gps.get('latitud')
            gps_longitud = posicion_gps.get('longitud')
            gps_altitud_m = posicion_gps.get('altitud_m')
            gps_satelites = posicion_gps.get('satelites')
            gps_fijado = bool(posicion_gps.get('fijado', False))
        return {'proximidad_cm': proximidad_cm, 'movimiento_pir': movimiento_pir, 'inclinacion_grados': inclinacion_grados, 'aceleracion_y': aceleracion_y, 'caida_detectada': caida_detectada, 'boton_panico': boton_panico, 'angulo_joystick_x': angulo_joystick_x, 'gps_latitud': gps_latitud, 'gps_longitud': gps_longitud, 'gps_altitud_m': gps_altitud_m, 'gps_satelites': gps_satelites, 'gps_fijado': gps_fijado, 'errores_i2c': self._conteo_errores_i2c, 'bateria_pct': 100, 'modo_simulacion': self.modo_simulacion}

class CajaActuadores:

    def __init__(self, configuracion=None):
        configuracion_base = {'pin_vibrador': PIN_VIBRADOR_HOMBRO_IZQ_DEF, 'pines_vibradores_secundarios': [PIN_VIBRADOR_HOMBRO_DER_DEF], 'habilitar_buzzer': False, 'pin_buzzer': PIN_BUZZER_DEF, 'pin_relevador': PIN_RELEVADOR_DEF, 'pin_led_r': PIN_LED_R_DEF, 'pin_led_g': PIN_LED_G_DEF, 'pin_led_b': PIN_LED_B_DEF, 'timeout_seguridad_ms': 15000, 'modo_silencioso': True, 'timeout_watchdog_ms': 12000}
        if configuracion:
            configuracion_base.update(configuracion)
        self.configuracion = configuracion_base
        self.habilitar_buzzer = bool(self.configuracion.get('habilitar_buzzer', False))
        self._validar_configuracion_pines()
        self.modo_silencioso = bool(self.configuracion['modo_silencioso'])
        if not self.habilitar_buzzer:
            self.modo_silencioso = True
        self.modo_simulacion = machine is None
        self.pin_vibrador = None
        self.pin_vibradores_matriz = []
        self.pin_led_r = None
        self.pin_led_g = None
        self.pin_led_b = None
        self.pin_relevador = None
        self.pwm_buzzer = None
        self._ultimo_comando_ms = tiempo_ms_actual()
        if self.modo_simulacion:
            self.pin_vibrador = PinSimulado(0)
            self.pin_vibradores_matriz = [self.pin_vibrador]
            for _ in self.configuracion.get('pines_vibradores_secundarios', []):
                self.pin_vibradores_matriz.append(PinSimulado(0))
            self.pin_led_r = PinSimulado(0)
            self.pin_led_g = PinSimulado(0)
            self.pin_led_b = PinSimulado(0)
            self.pin_relevador = PinSimulado(0)
            self.pwm_buzzer = PwmSimulado()
        else:
            self._inicializar_hardware_real()
        self.estado_seguro()

    def _validar_configuracion_pines(self):
        validar_pin_pwm_seguro(self.configuracion['pin_vibrador'], 'pin_vibrador')
        if self.habilitar_buzzer:
            validar_pin_pwm_seguro(self.configuracion['pin_buzzer'], 'pin_buzzer')
        validar_pin_salida(self.configuracion['pin_relevador'], 'pin_relevador')
        validar_pin_salida(self.configuracion['pin_led_r'], 'pin_led_r')
        validar_pin_salida(self.configuracion['pin_led_g'], 'pin_led_g')
        validar_pin_salida(self.configuracion['pin_led_b'], 'pin_led_b')
        secundarios = self.configuracion.get('pines_vibradores_secundarios', [])
        if secundarios is None:
            secundarios = []
        if not isinstance(secundarios, (list, tuple)):
            raise ValueError('pines_vibradores_secundarios debe ser una lista o tupla')
        for indice, pin_secundario in enumerate(secundarios):
            validar_pin_pwm_seguro(pin_secundario, 'pin_vibrador_secundario_' + str(indice + 1))
        pines = [self.configuracion['pin_vibrador'], self.configuracion['pin_relevador'], self.configuracion['pin_led_r'], self.configuracion['pin_led_g'], self.configuracion['pin_led_b']]
        if self.habilitar_buzzer:
            pines.append(self.configuracion['pin_buzzer'])
        pines_totales = pines + list(secundarios)
        if len(set(pines_totales)) != len(pines_totales):
            raise ValueError('Hay conflicto de GPIO entre actuadores')

    def _inicializar_hardware_real(self):
        self.pin_vibrador = machine.Pin(self.configuracion['pin_vibrador'], machine.Pin.OUT)
        self.pin_vibradores_matriz = [self.pin_vibrador]
        for pin_secundario in self.configuracion.get('pines_vibradores_secundarios', []):
            self.pin_vibradores_matriz.append(machine.Pin(pin_secundario, machine.Pin.OUT))
        self.pin_led_r = machine.Pin(self.configuracion['pin_led_r'], machine.Pin.OUT)
        self.pin_led_g = machine.Pin(self.configuracion['pin_led_g'], machine.Pin.OUT)
        self.pin_led_b = machine.Pin(self.configuracion['pin_led_b'], machine.Pin.OUT)
        self.pin_relevador = machine.Pin(self.configuracion['pin_relevador'], machine.Pin.OUT)
        self.pin_relevador.value(1)
        if self.habilitar_buzzer:
            try:
                self.pwm_buzzer = machine.PWM(machine.Pin(self.configuracion['pin_buzzer']))
                self.pwm_buzzer.freq(2000)
                self._ajustar_pwm_buzzer(0)
            except Exception:
                self.pwm_buzzer = PwmSimulado()
        else:
            self.pwm_buzzer = PwmSimulado()

    def _registrar_comando(self):
        self._ultimo_comando_ms = tiempo_ms_actual()

    def _ajustar_pwm_buzzer(self, intensidad):
        try:
            self.pwm_buzzer.duty_u16(int(intensidad))
            return
        except Exception:
            pass
        try:
            self.pwm_buzzer.duty(int(intensidad))
        except Exception:
            pass

    def _encender_vibrador_ms(self, duracion_ms):
        self._encender_patron_vibradores_ms(duracion_ms, [0])

    def _setear_vibradores_matriz(self, indices_activos=None):
        if indices_activos is None:
            indices_activos = list(range(len(self.pin_vibradores_matriz)))
        activos = set((int(indice) for indice in indices_activos))
        for indice, pin_vibrador in enumerate(self.pin_vibradores_matriz):
            pin_vibrador.value(1 if indice in activos else 0)

    def _encender_patron_vibradores_ms(self, duracion_ms, indices_activos=None):
        self._setear_vibradores_matriz(indices_activos)
        esperar_ms(duracion_ms)
        self._setear_vibradores_matriz([])

    def _setear_led(self, rojo, verde, azul):
        self.pin_led_r.value(1 if rojo else 0)
        self.pin_led_g.value(1 if verde else 0)
        self.pin_led_b.value(1 if azul else 0)

    def controlar_led_rgb(self, rojo, verde, azul):
        self._registrar_comando()
        self._setear_led(rojo, verde, azul)

    def controlar_vibradores(self, activo):
        self._registrar_comando()
        if activo:
            self._setear_vibradores_matriz(list(range(len(self.pin_vibradores_matriz))))
        else:
            self._setear_vibradores_matriz([])

    def _tono_buzzer(self, frecuencia_hz, duracion_ms):
        if not self.habilitar_buzzer or self.modo_silencioso:
            return
        try:
            self.pwm_buzzer.freq(int(frecuencia_hz))
        except Exception:
            pass
        self._ajustar_pwm_buzzer(450)
        esperar_ms(duracion_ms)
        self._ajustar_pwm_buzzer(0)

    def activar_relevador_emergencia(self, duracion_ms=600):
        self._registrar_comando()
        self.pin_relevador.value(0)
        esperar_ms(duracion_ms)
        self.pin_relevador.value(1)

    def desactivar_relevador_emergencia(self):
        self._registrar_comando()
        self.pin_relevador.value(1)

    def activar_modo_silencioso(self, activar):
        self._registrar_comando()
        self.modo_silencioso = bool(activar) or not self.habilitar_buzzer

    def mostrar_estado_normal(self):
        self._registrar_comando()
        self._setear_led(0, 0, 1)
        self._setear_vibradores_matriz([])
        self._ajustar_pwm_buzzer(0)

    def activar_alerta_suave(self):
        self._registrar_comando()
        self._setear_led(1, 0, 1)
        self._encender_patron_vibradores_ms(120, [0])
        esperar_ms(80)
        self._encender_patron_vibradores_ms(120, [1])
        self._tono_buzzer(1800, 90)

    def activar_alerta_critica(self):
        self._registrar_comando()
        self._setear_led(1, 0, 0)
        for _ in range(3):
            self._encender_patron_vibradores_ms(220, [0, 1])
            esperar_ms(90)
        self._tono_buzzer(2300, 180)
        esperar_ms(80)
        self._tono_buzzer(1900, 180)
        self.activar_relevador_emergencia(350)

    def activar_panico_total(self):
        self._registrar_comando()
        self._setear_led(1, 0, 0)
        self.pin_relevador.value(0)
        for i in range(4):
            self._encender_patron_vibradores_ms(180, [i % 2])
            self._tono_buzzer(2500, 120)
            esperar_ms(70)
        self.pin_relevador.value(1)

    def estado_seguro(self):
        self._setear_vibradores_matriz([])
        self._setear_led(0, 0, 0)
        self._ajustar_pwm_buzzer(0)
        self.pin_relevador.value(1)

    def aplicar_timeout_seguridad(self):
        ahora = tiempo_ms_actual()
        transcurrido = diferencia_tiempo_ms(ahora, self._ultimo_comando_ms)
        if transcurrido > int(self.configuracion['timeout_seguridad_ms']):
            self.estado_seguro()

class Dispositivos:

    def __init__(self, configuracion_sensores=None, configuracion_actuadores=None):
        self.sensores = CajaSensores(configuracion_sensores)
        self.actuadores = CajaActuadores(configuracion_actuadores)
        self._validar_conflictos_entre_modulos()
        self._watchdog = None
        self._inicializar_watchdog(configuracion_actuadores or {})

    def _validar_conflictos_entre_modulos(self):
        pines_sensor = {}
        for nombre, valor in self.sensores.configuracion.items():
            if nombre.startswith('pin_'):
                if nombre == 'pin_adc_joystick_x' and (not bool(self.sensores.configuracion.get('habilitar_joystick_x', False))):
                    continue
                pines_sensor[valor] = nombre
        for nombre, valor in self.actuadores.configuracion.items():
            if not nombre.startswith('pin_'):
                continue
            if valor in pines_sensor:
                raise ValueError('Conflicto de GPIO entre modulos: ' + nombre + ' y ' + pines_sensor[valor])

    def _inicializar_watchdog(self, configuracion_actuadores):
        if machine is None:
            return
        timeout_ms = int(configuracion_actuadores.get('timeout_watchdog_ms', 12000))
        try:
            self._watchdog = machine.WDT(timeout=timeout_ms)
        except Exception:
            self._watchdog = None

    def obtener_estado_general(self):
        return self.sensores.obtener_resumen_sensores()

    def activar_modo_silencioso(self, activar):
        self.actuadores.activar_modo_silencioso(activar)

    def controlar_led_rgb(self, rojo, verde, azul):
        self.actuadores.controlar_led_rgb(rojo, verde, azul)

    def controlar_vibradores(self, activo):
        self.actuadores.controlar_vibradores(activo)

    def mostrar_estado_normal(self):
        self.actuadores.mostrar_estado_normal()

    def activar_alerta_suave(self):
        self.actuadores.activar_alerta_suave()

    def activar_alerta_critica(self):
        self.actuadores.activar_alerta_critica()

    def activar_panico_total(self):
        self.actuadores.activar_panico_total()

    def activar_estrobo_emergencia(self, duracion_ms=600):
        self.actuadores.activar_relevador_emergencia(duracion_ms)

    def desactivar_estrobo_emergencia(self):
        self.actuadores.desactivar_relevador_emergencia()

    def estado_seguro(self):
        self.actuadores.estado_seguro()

    def aplicar_timeout_seguridad(self):
        self.actuadores.aplicar_timeout_seguridad()

    def alimentar_watchdog(self):
        if self._watchdog is None:
            return
        try:
            self._watchdog.feed()
        except Exception:
            pass

class SensorBox(CajaSensores):
    pass

class ActuatorBox(CajaActuadores):
    pass