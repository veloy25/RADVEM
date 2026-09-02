```python
import time
import math
from datetime import datetime

from gpiozero import Button, Servo, DistanceSensor
from gpiozero.pins.lgpio import LGPIOFactory

from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306


# ============================================================
# CONFIGURAÇÃO DOS GPIOs
# ============================================================

# Numeração BCM
BOTAO_GPIO = 17

TRIG_GPIO = 23
ECHO_GPIO = 24

SERVO_GPIO = 18

I2C_PORT = 1
I2C_ADDRESS = 0x3C


# ============================================================
# CONFIGURAÇÃO DO RADAR
# ============================================================

ANGULO_MIN = 0
ANGULO_MAX = 150
PASSO_ANGULO = 5

DISTANCIA_BLOQUEIO = 12.0
DISTANCIA_LIBERACAO = 15.0

TEMPO_ENTRE_MOVIMENTOS = 0.05

# Limite utilizado pelo radar para representação gráfica.
# Exemplo: 100 cm serão representados como o raio máximo.
DISTANCIA_MAXIMA_CM = 100.0

# Tamanho da área gráfica futura
RADAR_CENTRO_X = 400
RADAR_CENTRO_Y = 400
RADAR_RAIO_PX = 350

ARQUIVO_LOG = "radar_deteccoes.txt"


# ============================================================
# GPIO FACTORY
# ============================================================

factory = LGPIOFactory()


# ============================================================
# BOTÃO
# ============================================================

botao = Button(
    BOTAO_GPIO,
    pull_up=False,
    bounce_time=0.2,
    pin_factory=factory
)


# ============================================================
# SERVO
# ============================================================

servo = Servo(
    SERVO_GPIO,
    min_pulse_width=0.0005,
    max_pulse_width=0.0025,
    pin_factory=factory
)


# ============================================================
# SENSOR ULTRASSÔNICO
# ============================================================

sensor = DistanceSensor(
    trigger=TRIG_GPIO,
    echo=ECHO_GPIO,
    max_distance=DISTANCIA_MAXIMA_CM / 100.0,
    pin_factory=factory
)


# ============================================================
# OLED SSD1306
# ============================================================

serial = i2c(
    port=I2C_PORT,
    address=I2C_ADDRESS
)

oled = ssd1306(serial)


# ============================================================
# ESTADO DO RADAR
# ============================================================

ativo = False

angulo = ANGULO_MIN
direcao = 1

bloqueado = False

numero_ciclo = 0


# ============================================================
# CONTROLE DO BOTÃO
# ============================================================

def alternar_radar():
    global ativo

    ativo = not ativo


botao.when_pressed = alternar_radar


# ============================================================
# SERVO
# ============================================================

def set_angle(angle):
    """
    Converte o ângulo do radar para o intervalo
    utilizado pelo gpiozero.Servo.

    gpiozero:
        -1 = posição mínima
         0 = posição central
        +1 = posição máxima
    """

    valor = (angle / 90.0) - 1.0

    valor = max(-1.0, min(1.0, valor))

    servo.value = valor


# ============================================================
# DISTÂNCIA
# ============================================================

def medir_distancia():
    """
    Retorna a distância em centímetros.
    Retorna None em caso de erro.
    """

    try:

        distancia_m = sensor.distance

        distancia_cm = distancia_m * 100.0

        return distancia_cm

    except Exception:

        return None


# ============================================================
# COORDENADAS POLARES → PIXELS
# ============================================================

def polar_para_pixel(angulo_graus, distancia_cm):
    """
    Converte:

        ângulo + distância

    para:

        coordenadas X/Y da interface.

    A distância máxima corresponde ao raio máximo
    da área gráfica.
    """

    # Limita a distância ao alcance representado
    distancia = min(
        distancia_cm,
        DISTANCIA_MAXIMA_CM
    )

    # Converte centímetros para pixels
    raio_px = (
        distancia / DISTANCIA_MAXIMA_CM
    ) * RADAR_RAIO_PX

    # Python utiliza radianos nas funções trigonométricas
    angulo_rad = math.radians(angulo_graus)

    x = RADAR_CENTRO_X + (
        raio_px * math.cos(angulo_rad)
    )

    y = RADAR_CENTRO_Y - (
        raio_px * math.sin(angulo_rad)
    )

    return round(x), round(y)


# ============================================================
# REGISTRO DA DETECÇÃO
# ============================================================

def registrar_deteccao(
    ciclo,
    angulo,
    distancia,
    x,
    y
):

    timestamp = datetime.now().isoformat(
        timespec="milliseconds"
    )

    linha = (
        f"{ciclo};"
        f"{timestamp};"
        f"{angulo};"
        f"{distancia:.2f};"
        f"{x};"
        f"{y}\n"
    )

    with open(ARQUIVO_LOG, "a") as arquivo:

        arquivo.write(linha)


# ============================================================
# CABEÇALHO DO ARQUIVO
# ============================================================

def inicializar_arquivo():

    try:

        with open(ARQUIVO_LOG, "x") as arquivo:

            arquivo.write(
                "ciclo;"
                "timestamp;"
                "angulo;"
                "distancia_cm;"
                "x;"
                "y\n"
            )

    except FileExistsError:

        pass


# ============================================================
# OLED
# ============================================================

def atualizar_oled(distancia):

    oled.clear()

    if ativo:

        oled.text(
            "Radar: ON",
            0,
            0
        )

    else:

        oled.text(
            "Radar: OFF",
            0,
            0
        )

        oled.text(
            "Aperte o botao",
            0,
            10
        )


    oled.text(
        "Ang:",
        0,
        20
    )

    oled.text(
        str(angulo),
        40,
        20
    )


    oled.text(
        "Dist:",
        0,
        40
    )

    if distancia is not None:

        oled.text(
            f"{distancia:.1f}",
            50,
            40
        )

    else:

        oled.text(
            "--",
            50,
            40
        )


    if bloqueado:

        oled.text(
            "STOP",
            80,
            0
        )


    oled.show()


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

inicializar_arquivo()


try:

    while True:

        # ----------------------------------------------------
        # MEDIÇÃO
        # ----------------------------------------------------

        distancia = medir_distancia()


        # ----------------------------------------------------
        # HISTERESE
        # ----------------------------------------------------

        if distancia is not None:

            if distancia <= DISTANCIA_BLOQUEIO:

                bloqueado = True

            elif distancia >= DISTANCIA_LIBERACAO:

                bloqueado = False


        # ----------------------------------------------------
        # VARREDURA
        # ----------------------------------------------------

        if ativo and not bloqueado:

            # Posiciona o servo
            set_angle(angulo)

            # ------------------------------------------------
            # DETECÇÃO
            # ------------------------------------------------

            if distancia is not None:

                # Apenas registra objetos dentro do
                # alcance configurado.
                if distancia <= DISTANCIA_MAXIMA_CM:

                    x, y = polar_para_pixel(
                        angulo,
                        distancia
                    )

                    registrar_deteccao(
                        numero_ciclo,
                        angulo,
                        distancia,
                        x,
                        y
                    )


            # ------------------------------------------------
            # PRÓXIMA POSIÇÃO
            # ------------------------------------------------

            angulo += PASSO_ANGULO * direcao


            if angulo >= ANGULO_MAX:

                angulo = ANGULO_MAX

                direcao = -1

                # Uma ida e volta completa
                # representa um novo ciclo.
                numero_ciclo += 1


            elif angulo <= ANGULO_MIN:

                angulo = ANGULO_MIN

                direcao = 1


            time.sleep(TEMPO_ENTRE_MOVIMENTOS)


        else:

            # Não movimenta o servo
            servo.detach()


        # ----------------------------------------------------
        # OLED
        # ----------------------------------------------------

        atualizar_oled(distancia)


        time.sleep(0.01)


except KeyboardInterrupt:

    print("\nRadar encerrado.")


finally:

    servo.detach()

    oled.clear()
    oled.show()
```
