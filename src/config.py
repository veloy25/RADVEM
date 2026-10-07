# ============================================================
# RADVEM - CONFIGURAÇÃO
# ============================================================

# ----------------------------
# GPIO - BCM
# ----------------------------

SERVO_GPIO = 18

TRIG_GPIO = 23
ECHO_GPIO = 24


# ----------------------------
# RADAR
# ----------------------------

ANGLE_MIN = 0
ANGLE_MAX = 150
ANGLE_STEP = 5

# Tempo para percorrer 0 -> 150 graus
SWEEP_TIME = 1.0

# Distância máxima considerada uma detecção
DETECTION_DISTANCE_CM = 100.0


# ----------------------------
# INTERFACE
# ----------------------------

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 480

RADAR_CENTER_X = 400
RADAR_CENTER_Y = 390

RADAR_RADIUS = 330

# Tempo que o ponto permanece visível
FADEOUT_TIME = 3.0


# ----------------------------
# API
# ----------------------------

API_URL = "http://SEU_SERVIDOR/detections"

RADAR_ID = "RADVEM-001"