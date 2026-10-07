import math
import time
from datetime import datetime

from gpiozero import Servo, DistanceSensor
from gpiozero.pins.lgpio import LGPIOFactory

import config


# ============================================================
# RADAR
# ============================================================

class Radar:

    def __init__(self):

        # ----------------------------------------------------
        # GPIO Factory
        # ----------------------------------------------------

        self.factory = LGPIOFactory()


        # ----------------------------------------------------
        # Servo
        # ----------------------------------------------------

        self.servo = Servo(
            config.SERVO_GPIO,
            min_pulse_width=0.0005,
            max_pulse_width=0.0025,
            pin_factory=self.factory
        )


        # ----------------------------------------------------
        # HC-SR04
        # ----------------------------------------------------

        self.sensor = DistanceSensor(
            trigger=config.TRIG_GPIO,
            echo=config.ECHO_GPIO,
            max_distance=config.DETECTION_DISTANCE_CM / 100.0,
            pin_factory=self.factory
        )


        # ----------------------------------------------------
        # Estado da varredura
        # ----------------------------------------------------

        self.ativo = False

        self.angulo = config.ANGLE_MIN

        self.direcao = 1


        # ----------------------------------------------------
        # ID das detecções
        # ----------------------------------------------------

        self.detection_id = 0


        # ----------------------------------------------------
        # Callback
        #
        # Será utilizado posteriormente pelo main.py.
        #
        # Exemplo:
        #
        # radar.on_detection = minha_funcao
        # ----------------------------------------------------

        self.on_detection = None


    # ========================================================
    # START / STOP
    # ========================================================

    def start(self):

        """
        Inicia a varredura.
        """

        self.ativo = True


    def stop(self):

        """
        Para a varredura e desliga o sinal do servo.
        """

        self.ativo = False

        self.servo.detach()


    # ========================================================
    # SERVO
    # ========================================================

    def set_angle(self, angle):

        """
        Converte um ângulo de 0-150 graus para o intervalo
        utilizado pelo gpiozero.Servo.

        gpiozero:
            -1 = mínimo
             0 = centro
            +1 = máximo
        """

        valor = (angle / 90.0) - 1.0

        valor = max(-1.0, min(1.0, valor))

        self.servo.value = valor


    # ========================================================
    # DISTÂNCIA
    # ========================================================

    def measure_distance(self):

        """
        Mede a distância utilizando o HC-SR04.

        Retorna:
            distância em centímetros

        ou:

            None

        caso não seja possível obter uma leitura.
        """

        try:

            distancia_m = self.sensor.distance

            distancia_cm = distancia_m * 100.0

            return distancia_cm

        except Exception:

            return None


    # ========================================================
    # POLAR → CARTESIANA
    # ========================================================

    def polar_to_xy(self, angle, distance):

        """
        Converte coordenadas polares do radar para
        coordenadas cartesianas da interface.

        Retorna:

            x, y
        """

        # Limita a distância ao alcance do radar

        distancia = min(
            distance,
            config.DETECTION_DISTANCE_CM
        )


        # Converte centímetros para pixels

        raio = (
            distancia /
            config.DETECTION_DISTANCE_CM
        ) * config.RADAR_RADIUS


        # Graus → radianos

        angulo_rad = math.radians(angle)


        # Centro da área do radar

        x = config.RADAR_CENTER_X + (
            raio * math.cos(angulo_rad)
        )

        y = config.RADAR_CENTER_Y - (
            raio * math.sin(angulo_rad)
        )


        return round(x), round(y)


    # ========================================================
    # DETECÇÃO
    # ========================================================

    def create_detection(self, angle, distance):

        """
        Cria uma nova detecção.

        A detecção contém:

            ID
            timestamp
            ângulo
            distância
            X
            Y
        """

        self.detection_id += 1


        x, y = self.polar_to_xy(
            angle,
            distance
        )


        detection = {

            "radar_id": config.RADAR_ID,

            "detection_id": self.detection_id,

            "timestamp": datetime.now().astimezone().isoformat(
                timespec="milliseconds"
            ),

            "angle_deg": angle,

            "distance_cm": round(
                distance,
                2
            ),

            "x": x,

            "y": y
        }


        return detection


    # ========================================================
    # PROCESSAMENTO DE UMA POSIÇÃO
    # ========================================================

    def scan_position(self):

        """
        Posiciona o servo, realiza uma medição e,
        caso exista um objeto dentro do alcance,
        gera uma detecção.

        Retorna:

            detection

        ou:

            None
        """

        # Posiciona o servo

        self.set_angle(
            self.angulo
        )


        # Pequena espera para o servo chegar à posição

        time.sleep(0.01)


        # Mede distância

        distancia = self.measure_distance()


        # Não houve leitura válida

        if distancia is None:

            return None


        # Verifica se existe objeto dentro do alcance

        if distancia <= config.DETECTION_DISTANCE_CM:

            detection = self.create_detection(
                self.angulo,
                distancia
            )


            # Notifica o restante da aplicação

            if self.on_detection is not None:

                self.on_detection(
                    detection
                )


            return detection


        return None


    # ========================================================
    # ATUALIZAÇÃO DA VARREDURA
    # ========================================================

    def update(self):

        """
        Executa uma etapa da varredura.

        Deve ser chamada repetidamente pelo main.py.

        Retorna:

            detection

        ou:

            None
        """

        if not self.ativo:

            return None


        # ----------------------------------------------------
        # Realiza medição na posição atual
        # ----------------------------------------------------

        detection = self.scan_position()


        # ----------------------------------------------------
        # Calcula o próximo ângulo
        # ----------------------------------------------------

        self.angulo += (
            config.ANGLE_STEP *
            self.direcao
        )


        # ----------------------------------------------------
        # Chegou ao limite superior
        # ----------------------------------------------------

        if self.angulo >= config.ANGLE_MAX:

            self.angulo = config.ANGLE_MAX

            self.direcao = -1


        # ----------------------------------------------------
        # Chegou ao limite inferior
        # ----------------------------------------------------

        elif self.angulo <= config.ANGLE_MIN:

            self.angulo = config.ANGLE_MIN

            self.direcao = 1


        # ----------------------------------------------------
        # Tempo entre posições
        #
        # Exemplo:
        #
        # 150° / 30 intervalos ≈ 33 ms
        #
        # para completar um trecho em aproximadamente 1 s.
        # ----------------------------------------------------

        numero_intervalos = (
            config.ANGLE_MAX -
            config.ANGLE_MIN
        ) / config.ANGLE_STEP


        intervalo = (
            config.SWEEP_TIME /
            numero_intervalos
        )


        time.sleep(intervalo)


        return detection


    # ========================================================
    # INFORMAÇÕES DO RADAR
    # ========================================================

    def get_angle(self):

        """
        Retorna o ângulo atual.
        """

        return self.angulo


    def is_active(self):

        """
        Retorna True se a varredura estiver ativa.
        """

        return self.ativo


    # ========================================================
    # ENCERRAMENTO
    # ========================================================

    def close(self):

        """
        Libera os recursos do radar.
        """

        self.stop()

        self.sensor.close()
        self.servo.close()

        self.factory.close()