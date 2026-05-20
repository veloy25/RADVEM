from machine import Pin, I2C, PWM
import time
import ssd1306

# Botão
botao = Pin(1, Pin.IN, Pin.PULL_DOWN)

# OLED
i2c = I2C(0, scl=Pin(5), sda=Pin(4))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# Servo
servo = PWM(Pin(15))
servo.freq(50)

# Ultrassônico
trig = Pin(2, Pin.OUT)
echo = Pin(3, Pin.IN)

def medir_distancia():
    trig.low()
    time.sleep_us(2)
    trig.high()
    time.sleep_us(10)
    trig.low()

    inicio = 0
    fim = 0
    timeout = time.ticks_us()

    while echo.value() == 0:
        inicio = time.ticks_us()
        if time.ticks_diff(time.ticks_us(), timeout) > 30000:
            return None

    timeout = time.ticks_us()
    while echo.value() == 1:
        fim = time.ticks_us()
        if time.ticks_diff(time.ticks_us(), timeout) > 30000:
            return None

    duracao = time.ticks_diff(fim, inicio)
    return (duracao * 0.0343) / 2


def set_angle(angle):
    min_us = 500
    max_us = 2500
    pulse = min_us + (angle / 180) * (max_us - min_us)
    duty = int(pulse / 20000 * 65535)
    servo.duty_u16(duty)


# Controle
ativo = False
ultimo_estado = 0

# Controle do movimento
angulo = 0
direcao = 1  # 1 = indo, -1 = voltando

# Controle de obstáculo
bloqueado = False

while True:
    # --- BOTÃO ---
    estado = botao.value()

    if estado == 1 and ultimo_estado == 0:
        ativo = not ativo
        time.sleep(0.2)

    ultimo_estado = estado

    # --- SENSOR ---
    distancia = medir_distancia()

    # Histerese (evita tremedeira)
    if distancia is not None:
        if distancia <= 12:
            bloqueado = True
        elif distancia >= 15:
            bloqueado = False

    # --- SERVO ---
    if ativo and not bloqueado:
        set_angle(angulo)

        # Atualiza ângulo (varredura)
        angulo += 5 * direcao

        if angulo >= 90:
            angulo = 90
            direcao = -1
        elif angulo <= 0:
            angulo = 0
            direcao = 1

        time.sleep(0.05)

    else:
        servo.duty_u16(0)

    # --- OLED ---
    oled.fill(0)

    if ativo:
        oled.text("Servo: ON", 0, 0)
    else:
        oled.text("Servo: OFF", 0, 0)
        oled.text("Aperte o botao", 0, 10)

    oled.text("Ang:", 0, 20)
    oled.text(str(angulo), 40, 20)

    oled.text("Dist:", 0, 40)

    if distancia is not None:
        oled.text(str(round(distancia, 1)), 50, 40)
    else:
        oled.text("--", 50, 40)

    if bloqueado:
        oled.text("STOP", 80, 0)

    oled.show()

    time.sleep(0.01)
